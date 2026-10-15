# Why not Mem0, Supermemory, Bitwarden, or Keycloak?

These are adjacent systems, not inferior substitutes.

- **Mem0 and Supermemory** focus on extracting, storing, and retrieving AI memory. Evolving Soul
  focuses on owner approval, a portable encrypted format, continuity proof, and selective
  succession. They may become extractor or retrieval adapters.
- **Open WebUI** distributes a chat interface and extensibility runtime. Evolving Soul ships thin
  Functions that call a local sidecar; it does not replace Open WebUI.
- **Keycloak** is a mature IAM/SSO platform. Evolving Soul uses passkeys for vault authority and
  treats OIDC as optional account linking; it is not an IAM replacement.
- **Bitwarden/Vaultwarden emergency access** inspires delayed recovery. Evolving Soul applies a
  coordinator-plus-guardian threshold to selected encrypted AI-memory compartments rather than
  transferring a password vault or making a legal ownership claim.

The intended gap is a model-independent continuity layer between memory engines, local AI UIs,
identity providers, and emergency-recovery systems.

