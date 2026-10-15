"""Local FastAPI control plane. The vault remains usable without a coordinator."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from .auth import BootstrapManager, PairingTokenManager
from .crypto import b64, random_key, unb64
from .errors import AuthenticationRequired, SoulError
from .extractors import RuleBasedExtractor
from .types import Provenance
from .vault import SoulVault
from .webauthn_auth import WebAuthnManager


class StepUpSessions:
    def __init__(self) -> None:
        self._sessions: dict[str, tuple[str, datetime]] = {}

    def issue(self, credential_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self._sessions[token] = (credential_id, datetime.now(UTC) + timedelta(minutes=5))
        return token

    def consume(self, token: str) -> str:
        try:
            credential_id, expiry = self._sessions.pop(token)
        except KeyError as exc:
            raise AuthenticationRequired("A fresh passkey step-up is required") from exc
        if datetime.now(UTC) >= expiry:
            raise AuthenticationRequired("Passkey step-up session expired")
        return credential_id


def create_app(
    vault: SoulVault,
    *,
    rp_id: str = "localhost",
    origin: str = "http://localhost:8765",
) -> Any:
    try:
        from fastapi import FastAPI, Header, HTTPException
        from fastapi.responses import HTMLResponse
    except ImportError as exc:
        raise SoulError("Local server requires evolving-soul-ai[server]") from exc
    store = vault._store
    if store is None:  # The server must never silently unlock a vault.
        raise SoulError("Vault must be unlocked before starting the sidecar")

    app = FastAPI(title="Evolving Soul local sidecar", version="3.0.0a1")
    bootstrap = BootstrapManager()
    bootstrap_code = bootstrap.issue()
    passkeys = WebAuthnManager(store, rp_id=rp_id, origin=origin)
    pairing_row = next(store.iter_objects("pairing-state"), None)
    if pairing_row is None:
        pairing_opaque_id = secrets.token_bytes(24)
        pairing_value: dict[str, Any] = {"secret": b64(random_key()), "revoked": []}
        store.put(pairing_opaque_id, "pairing-state", pairing_value)
    else:
        pairing_opaque_id, pairing_value = pairing_row

    def persist_revocations(revoked: set[str]) -> None:
        pairing_value["revoked"] = sorted(revoked)
        store.put(pairing_opaque_id, "pairing-state", pairing_value)

    pairing = PairingTokenManager(
        unb64(pairing_value["secret"]),
        revoked=pairing_value["revoked"],
        on_revoke=persist_revocations,
    )
    sessions = StepUpSessions()
    extractor = RuleBasedExtractor()
    review_secret = secrets.token_bytes(32)
    app.state.bootstrap_code = bootstrap_code

    def problem(exc: Exception, status: int = 401) -> HTTPException:
        return HTTPException(status_code=status, detail=str(exc))

    @app.get("/v1/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "vault": "unlocked", "capsule_id": vault.capsule_id}

    @app.get("/", response_class=HTMLResponse)
    def local_review() -> str:
        return _CONTROL_PLANE_HTML

    @app.post("/v1/bootstrap/register/options")
    def bootstrap_options(body: dict[str, Any]) -> dict[str, Any]:
        try:
            bootstrap.consume(str(body.get("code", "")))
            return passkeys.registration_options(str(body.get("owner_name", "Owner")))
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/bootstrap/register/complete")
    def bootstrap_complete(body: dict[str, Any]) -> dict[str, str]:
        try:
            credential_id = passkeys.complete_registration(
                str(body["ceremony_id"]), body["credential"]
            )
            return {"credential_id": credential_id}
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/auth/options")
    def auth_options() -> dict[str, Any]:
        try:
            return passkeys.authentication_options()
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/auth/complete")
    def auth_complete(body: dict[str, Any]) -> dict[str, str]:
        try:
            credential_id = passkeys.complete_authentication(
                str(body["ceremony_id"]), body["credential"]
            )
            return {"step_up_token": sessions.issue(credential_id), "expires_in": "300"}
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/passkeys/register/options")
    def add_passkey_options(
        body: dict[str, Any], authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        try:
            consume_step_up(authorization)
            return passkeys.registration_options(str(body.get("owner_name", "Owner")))
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/passkeys/register/complete")
    def add_passkey_complete(body: dict[str, Any]) -> dict[str, str]:
        try:
            credential_id = passkeys.complete_registration(
                str(body["ceremony_id"]), body["credential"]
            )
            return {"credential_id": credential_id}
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/passkeys/{credential_id}/revoke", status_code=204)
    def revoke_passkey(
        credential_id: str, authorization: str | None = Header(default=None)
    ) -> None:
        try:
            consume_step_up(authorization)
            passkeys.revoke_credential(credential_id)
        except Exception as exc:
            raise problem(exc) from exc

    def consume_step_up(authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationRequired("Bearer step-up token required")
        return sessions.consume(authorization[7:])

    @app.post("/v1/pair/open-webui")
    def pair_open_webui(
        body: dict[str, Any], authorization: str | None = Header(default=None)
    ) -> dict[str, Any]:
        try:
            consume_step_up(authorization)
            user_id = str(body["user_id"])
            return {
                "token": pairing.issue(user_id),
                "scopes": sorted(PairingTokenManager.allowed_scopes),
            }
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/pair/revoke", status_code=204)
    def revoke_pairing(
        body: dict[str, Any], authorization: str | None = Header(default=None)
    ) -> None:
        try:
            consume_step_up(authorization)
            pairing.revoke(str(body["token"]))
        except Exception as exc:
            raise problem(exc) from exc

    def plugin_auth(authorization: str | None, user_id: str | None, scope: str) -> None:
        if not authorization or not authorization.startswith("Bearer ") or not user_id:
            raise AuthenticationRequired("Bound pairing token required")
        pairing.verify(authorization[7:], user_id, scope)

    @app.post("/v1/context/search")
    def context_search(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        x_open_webui_user_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            plugin_auth(authorization, x_open_webui_user_id, "context:read")
            records = vault.search_context(
                str(body.get("query", "")),
                token_budget=min(int(body.get("token_budget", 1024)), 4096),
            )
            return {
                "context": [
                    {
                        "memory_id": record.memory_id,
                        "content": record.content,
                        "provenance": asdict(record.provenance),
                        "trust": "untrusted-memory-data",
                    }
                    for record in records
                ]
            }
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/proposals")
    def create_proposal(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        x_open_webui_user_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            plugin_auth(authorization, x_open_webui_user_id, "proposal:create")
            candidates = extractor.extract(str(body.get("conversation", ""))[:16_000])
            proposals = [
                vault.propose_memory(
                    candidate.content,
                    provenance=Provenance(
                        source=f"open-webui:{x_open_webui_user_id}",
                        extractor="rule-based-local",
                    ),
                )
                for candidate in candidates
            ]
            return {"proposals": [asdict(proposal) for proposal in proposals]}
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/review-link")
    def review_link(
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
        x_open_webui_user_id: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            plugin_auth(authorization, x_open_webui_user_id, "context:read")
            expires = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
            proposal_id = str(body.get("proposal_id", "queue"))
            signed = f"{proposal_id}:{expires}"
            signature = hmac.new(review_secret, signed.encode(), hashlib.sha256).hexdigest()
            return {
                "url": f"{origin}/?review={proposal_id}&expires={expires}&sig={signature}",
                "expires_at": datetime.fromtimestamp(expires, UTC).isoformat(),
            }
        except Exception as exc:
            raise problem(exc) from exc

    @app.get("/v1/proposals")
    def list_proposals(authorization: str | None = Header(default=None)) -> list[dict[str, Any]]:
        try:
            consume_step_up(authorization)
            return [asdict(item) for item in vault.list_proposals()]
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/proposals/{proposal_id}/approve")
    def approve(
        proposal_id: str,
        body: dict[str, Any],
        authorization: str | None = Header(default=None),
    ) -> dict[str, Any]:
        try:
            credential_id = consume_step_up(authorization)
            return asdict(
                vault.approve_memory(
                    proposal_id,
                    actor_credential_id=credential_id,
                    edited_content=body.get("content"),
                    owner_asserted=True,
                )
            )
        except Exception as exc:
            raise problem(exc) from exc

    @app.post("/v1/proposals/{proposal_id}/reject", status_code=204)
    def reject(proposal_id: str, authorization: str | None = Header(default=None)) -> None:
        try:
            consume_step_up(authorization)
            vault.reject_memory(proposal_id, owner_asserted=True)
        except Exception as exc:
            raise problem(exc) from exc

    return app


_CONTROL_PLANE_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evolving Soul AI — Local Review & Control Plane</title>
<style>
:root {
  --bg-primary: #F8FAFC;
  --bg-card: #FFFFFF;
  --border-color: #E2E8F0;
  --border-focus: #2563EB;
  --text-main: #0F172A;
  --text-muted: #64748B;
  --color-primary: #2563EB;
  --color-primary-hover: #1D4ED8;
  --color-success: #059669;
  --color-success-hover: #047857;
  --color-danger: #DC2626;
  --color-danger-hover: #B91C1C;
  --badge-bg: #EFF6FF;
  --badge-border: #BFDBFE;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-main);
  line-height: 1.5;
  padding: 2rem 1rem;
}
.container {
  max-width: 860px;
  margin: 0 auto;
}
header {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem 1.75rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
}
h1 {
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--text-main);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.author-badge {
  display: inline-block;
  background: var(--badge-bg);
  border: 1px solid var(--badge-border);
  border-left: 4px solid var(--color-primary);
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  font-size: 0.82rem;
  font-weight: 600;
  color: #1E40AF;
  margin-top: 0.5rem;
}
.platform-bar {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}
.pill {
  font-size: 0.75rem;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  background: #F1F5F9;
  border: 1px solid #CBD5E1;
  color: #334155;
  font-weight: 500;
}
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
}
.card-header {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.form-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}
input, textarea {
  font-family: inherit;
  font-size: 0.95rem;
  padding: 0.65rem 0.85rem;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #FFFFFF;
  color: var(--text-main);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}
input:focus, textarea:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}
input { flex: 1; min-width: 200px; }
textarea { width: 100%; resize: vertical; margin-bottom: 0.75rem; }
button {
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 0.65rem 1.25rem;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s, transform 0.05s;
  background: var(--color-primary);
  color: #FFFFFF;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}
button:hover { background: var(--color-primary-hover); }
button:active { transform: translateY(1px); }
button.success { background: var(--color-success); }
button.success:hover { background: var(--color-success-hover); }
button.danger { background: var(--color-danger); }
button.danger:hover { background: var(--color-danger-hover); }
.status-box {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  font-size: 0.85rem;
  color: var(--text-muted);
  white-space: pre-wrap;
  margin-top: 1rem;
}
.proposal-item {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  background: #FAFAFA;
}
.proposal-actions {
  display: flex;
  gap: 0.5rem;
}
.code-box {
  background: #0F172A;
  color: #F8FAFC;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-family: ui-monospace, Menlo, Monaco, Consolas, monospace;
  font-size: 0.82rem;
  overflow-x: auto;
  margin-top: 0.5rem;
}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>🛡️ Evolving Soul AI</h1>
    <p style="color: var(--text-muted); font-size: 0.95rem; margin-top: 0.25rem;">
      Local Control Plane & Memory Review Sidecar — Local-First AI Continuity
    </p>
    <div class="author-badge">
      ⚡ Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
    </div>
    <div class="platform-bar" id="platform-bar">
      <span class="pill" id="os-pill">💻 Detecting OS...</span>
      <span class="pill" id="webauthn-pill">🔑 WebAuthn / Passkeys</span>
      <span class="pill">🌐 Localhost Safe</span>
      <span class="pill">🔒 Zero-Knowledge Memory</span>
    </div>
  </header>

  <section class="card" id="bootstrap">
    <div class="card-header">🔑 Register Primary Passkey</div>
    <p style="color: var(--text-muted); font-size: 0.9rem;">
      Enter the one-time bootstrap code generated in your terminal to pair your hardware passkey (Touch ID, Windows Hello, or Security Key).
    </p>
    <div class="form-row">
      <input id="code" placeholder="Terminal bootstrap code" aria-label="Bootstrap code">
      <input id="name" value="Owner" aria-label="Owner label">
      <button onclick="register()"><span>🔐</span> Register Passkey</button>
    </div>
  </section>

  <section class="card">
    <div class="card-header">📥 Pending AI Memory Proposals</div>
    <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem;">
      Memories proposed by Open WebUI or external agents require verified passkey step-up to approve into the vault.
    </p>
    <button onclick="loadQueue()"><span>🔄</span> Authenticate & Load Proposals</button>
    <div id="queue" style="margin-top: 1rem;"></div>
    <pre class="status-box" id="status">Ready. Click above to authenticate with your passkey.</pre>
  </section>

  <section class="card">
    <div class="card-header">🚀 Cross-Platform CLI Quickstart</div>
    <p style="color: var(--text-muted); font-size: 0.9rem;">
      Run the command-line interface on Linux, macOS, or Windows:
    </p>
    <div class="code-box">
# Linux & macOS:
./soul.sh doctor            # Run cross-platform diagnostics
./soul.sh serve             # Start local control plane and sidecar

# Windows (PowerShell / Command Prompt):
soul.bat doctor             # Run cross-platform diagnostics
soul.bat serve              # Start local control plane and sidecar
    </div>
  </section>
</div>

<script>
const status = document.querySelector('#status');
const osPill = document.querySelector('#os-pill');
const webauthnPill = document.querySelector('#webauthn-pill');

// OS Detection
const ua = navigator.userAgent;
let osName = "Linux / POSIX";
if (ua.indexOf("Win") !== -1) osName = "🪟 Windows (NT)";
else if (ua.indexOf("Mac") !== -1) osName = "🍎 macOS (Darwin)";
else if (ua.indexOf("Linux") !== -1) osName = "🐧 Linux";
osPill.textContent = osName;

// WebAuthn Detection
if (window.PublicKeyCredential) {
  webauthnPill.textContent = "🔑 Passkeys Supported";
  webauthnPill.style.background = "#ECFDF5";
  webauthnPill.style.color = "#047857";
  webauthnPill.style.borderColor = "#A7F3D0";
} else {
  webauthnPill.textContent = "⚠️ Passkeys Not Supported";
  webauthnPill.style.color = "#DC2626";
}

const b64d=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/')+'==='.slice((s.length+3)%4)),c=>c.charCodeAt(0));
const b64e=b=>btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');

function creation(o){o.challenge=b64d(o.challenge);o.user.id=b64d(o.user.id);(o.excludeCredentials||[]).forEach(x=>x.id=b64d(x.id));return o}
function request(o){o.challenge=b64d(o.challenge);(o.allowCredentials||[]).forEach(x=>x.id=b64d(x.id));return o}
function credential(c){
  const r=c.response, out={clientDataJSON:b64e(r.clientDataJSON)};
  for(const key of ['attestationObject','authenticatorData','signature','userHandle']){
    if(r[key]) out[key]=b64e(r[key]);
  }
  if(r.getTransports) out.transports=r.getTransports();
  return {id:c.id,rawId:b64e(c.rawId),type:c.type,
    authenticatorAttachment:c.authenticatorAttachment,
    clientExtensionResults:c.getClientExtensionResults(),response:out};
}

async function api(path,body,token){
  let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(body)});
  if(!r.ok) throw Error(await r.text());
  return r.status===204?{}:r.json();
}

async function register(){
  try{
    status.textContent='Requesting passkey registration options...';
    let x=await api('/v1/bootstrap/register/options',{code:code.value,owner_name:name.value});
    status.textContent='Touch your hardware key, fingerprint sensor, or Windows Hello to register...';
    let c=await navigator.credentials.create({publicKey:creation(x.options)});
    await api('/v1/bootstrap/register/complete',{ceremony_id:x.ceremony_id,credential:credential(c)});
    status.textContent='✅ Passkey successfully registered and bound to vault.';
    bootstrap.hidden=true;
  }catch(e){
    status.textContent='❌ Registration error: ' + e.message;
  }
}

async function stepup(){
  let x=await api('/v1/auth/options',{});
  status.textContent='Touch your passkey to authenticate...';
  let c=await navigator.credentials.get({publicKey:request(x.options)});
  return (await api('/v1/auth/complete',{ceremony_id:x.ceremony_id,credential:credential(c)})).step_up_token;
}

async function loadQueue(){
  try{
    let token=await stepup();
    status.textContent='Authenticated. Fetching pending proposals...';
    let r=await fetch('/v1/proposals',{headers:{Authorization:'Bearer '+token}});
    if(!r.ok) throw Error(await r.text());
    let rows=await r.json();
    queue.replaceChildren(...rows.map(card));
    status.textContent=rows.length ? `Found ${rows.length} pending memory proposal(s).` : 'No pending proposals in the vault.';
  }catch(e){
    status.textContent='❌ ' + e.message;
  }
}

function card(p){
  let d=document.createElement('div');
  d.className='proposal-item';
  let meta=document.createElement('div');
  meta.style.fontSize='0.78rem';
  meta.style.color='#64748B';
  meta.style.marginBottom='0.5rem';
  meta.textContent=`ID: ${p.proposal_id} • Source: ${p.provenance?.source || 'unknown'} • Extractor: ${p.provenance?.extractor || 'rule-based'}`;
  let t=document.createElement('textarea');
  t.value=p.content;
  t.rows=3;
  let actions=document.createElement('div');
  actions.className='proposal-actions';
  let a=document.createElement('button');
  a.className='success';
  a.innerHTML='<span>✓</span> Approve Memory';
  a.onclick=()=>decide(p.proposal_id,'approve',t.value);
  let r=document.createElement('button');
  r.className='danger';
  r.innerHTML='<span>✕</span> Reject & Erase';
  r.onclick=()=>decide(p.proposal_id,'reject');
  actions.append(a, r);
  d.append(meta, t, actions);
  return d;
}

async function decide(id,action,content){
  try{
    status.textContent=`Performing ${action} with passkey step-up...`;
    let token=await stepup();
    await api('/v1/proposals/'+encodeURIComponent(id)+'/'+action,{content},token);
    status.textContent=`Proposal ${action}d successfully.`;
    await loadQueue();
  }catch(e){
    status.textContent='❌ Error: ' + e.message;
  }
}
</script>
</body>
</html>
"""
