"""
Giao Diện Ứng Dụng Trực Quan — Evolving Soul AI V3 (White Theme Chủ Đạo)
Hiện thực hóa theo mockup docs/mockups/v3_ui.html.

Chạy:  streamlit run app_ui.py      (chế độ demo: đặt EVOLVING_SOUL_DEMO=1)

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)
"""

from __future__ import annotations

import datetime
import hashlib
import html
import inspect
import os
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from evolving_soul import EvolvingSoulEngine, EvolvingSoulError, LockedOutError, Settings, __version__
from evolving_soul.biometrics import BiometricError
from evolving_soul.config import ENV_PASSPHRASE
from evolving_soul.legacy import MIN_FAMILY_SECRET_LENGTH
from evolving_soul.logging_setup import configure_logging
from evolving_soul.scoring import PILLAR_LABELS, PILLARS

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ALL_TRAITS = [
    "Hướng nội", "Hướng ngoại", "Logic & Lý trí", "Giàu cảm xúc",
    "Thích công nghệ", "Yêu nghệ thuật", "Cầu toàn", "Phóng khoáng",
    "Thức khuya", "Dậy sớm", "Thích sự yên tĩnh", "Ưa mạo hiểm",
]
MIN_DATE = datetime.date(1900, 1, 1)
EVENT_LABELS = {
    "vault_created": "Tạo két sắt", "vault_unlock": "Mở két sắt", "owner_registered": "Khởi tạo hồ sơ",
    "owner_reinitialized": "Khởi tạo lại hồ sơ", "owner_verification": "Xác minh Chủ nhân",
    "legacy_sealed": "Niêm phong di sản", "legacy_revoked": "Hủy niêm phong", "legacy_claim": "Yêu cầu tiếp quản",
    "legacy_claim_revoked": "Thu hồi tiếp quản", "passphrase_changed": "Đổi passphrase",
    "migration_started": "Bắt đầu nâng cấp V2", "migration_completed": "Hoàn tất nâng cấp V2",
}

# =========================================================================
# CẤU HÌNH TRANG & WHITE THEME CHỦ ĐẠO
# =========================================================================
st.set_page_config(
    page_title="Evolving Soul AI — Nhận Diện Chủ Nhân & Thừa Kế Di Sản Số",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(f"<style>{(ASSETS_DIR / 'theme.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
configure_logging()


# =========================================================================
# TIỆN ÍCH
# =========================================================================

def esc(value) -> str:
    """Escape dữ liệu người dùng trước khi chèn vào HTML (chống chèn mã)."""
    return html.escape(str(value if value is not None else ""))


def mask_profile(data):
    """Bản xem đã che của hồ sơ: chỉ lộ cấu trúc, độ dài và vài ký tự đầu của digest."""
    if isinstance(data, dict):
        return {k: mask_profile(v) for k, v in data.items()}
    if isinstance(data, list):
        return f"<list: {len(data)} phần tử>"
    if isinstance(data, (int, float, bool)) or data is None:
        return data
    digest = hashlib.sha256(str(data).encode("utf-8")).hexdigest()[:8]
    return f"<str: {len(str(data))} ký tự, sha256 {digest}…>"


def flash(kind: str, message: str) -> None:
    """Thông báo hiển thị sau st.rerun()."""
    st.session_state["flash"] = (kind, message)


def show_flash() -> None:
    kind, message = st.session_state.pop("flash", (None, None))
    if kind:
        getattr(st, kind)(message)


def run_action(action, success: str | None = None) -> bool:
    """Thực thi thao tác của engine, hiển thị lỗi thân thiện thay vì traceback."""
    try:
        action()
    except LockedOutError as exc:
        st.error(f"⏳ {exc}")
        return False
    except (EvolvingSoulError, BiometricError, ValueError, PermissionError) as exc:
        st.error(f"⚠️ {exc}")
        return False
    if success:
        flash("success", success)
    return True


# Streamlit ≥ 1.51 dùng width="stretch"; bản 1.50 (bản cuối hỗ trợ Python 3.9) chỉ có use_container_width
_PLOTLY_HAS_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters


def show_chart(fig: go.Figure) -> None:
    if _PLOTLY_HAS_WIDTH:
        st.plotly_chart(fig, width="stretch")
    else:
        st.plotly_chart(fig, use_container_width=True)


def date_text(value: datetime.date | None) -> str:
    return value.isoformat() if value else ""


def format_ts(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")


def get_engine() -> EvolvingSoulEngine:
    """Mỗi phiên trình duyệt giữ một engine riêng — trạng thái 'đã xác minh' không chia sẻ giữa các phiên."""
    if "engine" not in st.session_state:
        engine = EvolvingSoulEngine(Settings.from_env())
        passphrase = os.environ.get(ENV_PASSPHRASE)
        if passphrase and engine.is_initialized:
            try:
                engine.unlock(passphrase)
            except EvolvingSoulError:
                pass
        st.session_state["engine"] = engine
        st.session_state["view"] = "lock"
    return st.session_state["engine"]


engine = get_engine()
if engine.demo_mode:
    engine.set_demo_offset_days(st.session_state.get("demo_days", 0))


def demo_slider(key: str) -> None:
    if not engine.demo_mode:
        return
    days = st.slider("🧪 [DEMO] Số ngày Chủ nhân đã không online:", 0, 1000,
                     st.session_state.get("demo_days", 0), step=5, key=key)
    if days != st.session_state.get("demo_days", 0):
        st.session_state["demo_days"] = days
        st.rerun()


# =========================================================================
# BIỂU ĐỒ (WHITE THEME)
# =========================================================================

def plot_soul_radar(baseline: dict, current: dict | None = None) -> go.Figure:
    categories = [PILLAR_LABELS[p] for p in PILLARS]
    fig = go.Figure()
    traces = [(baseline, "Chữ ký gốc (EMA)", "#059669", "rgba(5, 150, 105, 0.2)")]
    if current:
        traces.append((current, "Phiên hiện tại", "#2563EB", "rgba(37, 99, 235, 0.25)"))
    for values, name, line, fill in traces:
        r = [float(values.get(c, 0.0)) for c in categories]
        fig.add_trace(go.Scatterpolar(r=r + r[:1], theta=categories + categories[:1], fill="toself",
                                      name=name, line_color=line, fillcolor=fill))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1], gridcolor="#E2E8F0", linecolor="#CBD5E1"),
                   angularaxis=dict(gridcolor="#E2E8F0", linecolor="#CBD5E1"), bgcolor="#F8FAFC"),
        paper_bgcolor="#FFFFFF", showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=30, r=30, t=30, b=40), height=360,
    )
    return fig


def plot_trust_history(history: list[dict], threshold: float) -> go.Figure:
    xs = list(range(1, len(history) + 1))
    fig = go.Figure()
    fig.add_hline(y=threshold, line_dash="dash", line_color="#CBD5E1",
                  annotation_text=f"ngưỡng {threshold:.0%}", annotation_font_color="#64748B")
    fig.add_trace(go.Scatter(
        x=xs, y=[h["trust"] for h in history], mode="lines+markers", line=dict(color="#2563EB", width=2),
        marker=dict(size=7, color=["#059669" if h["is_owner"] else "#DC2626" for h in history]),
        hovertext=[format_ts(h["ts"]) for h in history], name="Điểm tin cậy",
    ))
    fig.update_layout(height=180, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                      yaxis=dict(range=[0, 1], gridcolor="#E2E8F0", tickformat=".0%"), xaxis=dict(visible=False),
                      showlegend=False)
    return fig


# =========================================================================
# SIDEBAR: TRẠNG THÁI & BẢN QUYỀN TÁC GIẢ
# =========================================================================

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("### 🛡️ Evolving Soul AI")
        st.caption(f"V{__version__} · AI ghi nhớ & nhận diện Chủ nhân · Thừa kế Di sản Số")
        if engine.demo_mode:
            st.markdown('<div class="es-demo">🧪 <b>CHẾ ĐỘ DEMO</b> — mô phỏng thời gian đang bật</div>',
                        unsafe_allow_html=True)
        st.divider()

        profile = engine.profile if engine.is_unlocked else None
        if profile:
            st.success(f"🟢 **Chủ nhân**: {profile.get('owner_name')}")
            st.metric("Thế hệ tiến hóa (Generation)", f"Gen #{profile.get('generation', 1)}")
            if engine.owner_verified:
                minutes = int(engine.owner_session_remaining_seconds // 60) + 1
                st.markdown(f'<span class="es-pill green">● Đã xác minh · còn {minutes} phút</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="es-pill gray">○ Chưa xác minh trong phiên này</span>', unsafe_allow_html=True)

            status = engine.legacy_status()
            if status:
                st.caption("Di sản Số")
                st.progress(min(1.0, status["elapsed_days"] / status["threshold_days"]),
                            text=f"Còn {status['remaining_days']:.0f} / {status['threshold_days']} ngày")
        elif engine.is_unlocked:
            st.warning("🟡 Chưa có hồ sơ Chủ nhân.")
        else:
            st.info("🔒 Két sắt đang khóa.")

        if engine.is_unlocked and st.button("🔒 Khóa két sắt", width="stretch"):
            engine.lock()
            st.session_state.pop("last_verify", None)
            st.session_state.pop("reinit", None)
            st.rerun()

        st.divider()
        st.markdown("""
        <div class="badge-author">
            <small>Mã Nguồn Mở Có Bản Quyền</small>
            <strong>Tác giả: HÀ HỮU HƯNG (1985)</strong>
            <span>⚡ KỸ SƯ AI THẾ HỆ 8X</span>
            <small style="text-transform:none;font-weight:400;margin-top:4px">Kiến trúc: Evolving Digital Soul & Dead Man's Switch 730 ngày</small>
        </div>
        """, unsafe_allow_html=True)


# =========================================================================
# MÀN HÌNH A — KHÓA KÉT SẮT
# =========================================================================

def render_lock_screen() -> None:
    st.markdown("""
    <div class="es-brand">
        <h2>🛡️ Evolving Soul AI</h2>
        <div class="es-muted">AI ghi nhớ & nhận diện Chủ nhân · Thừa kế Di sản Số 730 ngày</div>
    </div>
    """, unsafe_allow_html=True)
    show_flash()
    if engine.needs_migration:
        st.warning("⬆️ **Phát hiện két sắt V2.** Đặt passphrase mới để nâng cấp lên V3. Lần xác minh đầu tiên sẽ dùng "
                   "thuật toán V2 để chứng minh bạn là Chủ nhân, sau đó file V2 bị xóa.")

    col_owner, col_setup, col_heir = st.columns(3)
    with col_owner, st.container(border=True):
        st.markdown("#### 🔑 Mở két sắt")
        if engine.is_initialized:
            with st.form("unlock_form"):
                passphrase = st.text_input("Passphrase của Chủ nhân", type="password")
                if st.form_submit_button("Mở khóa", type="primary", width="stretch"):
                    if run_action(lambda: engine.unlock(passphrase)):
                        st.rerun()
        else:
            st.caption("Chưa có két sắt trên máy này.")

    with col_setup, st.container(border=True):
        if engine.needs_migration:
            st.markdown("#### ⬆️ Nâng cấp từ V2")
            with st.form("migrate_form"):
                p1 = st.text_input("Passphrase V3 mới (≥ 8 ký tự)", type="password")
                p2 = st.text_input("Nhập lại passphrase", type="password")
                v2_phrase = st.text_input("Cụm từ bí mật V2 (để trống nếu dùng mặc định)", type="password")
                if st.form_submit_button("Nâng cấp két sắt", type="primary", width="stretch"):
                    if p1 != p2:
                        st.error("Hai lần nhập passphrase không khớp.")
                    elif run_action(lambda: engine.migrate_from_v2(p1, v2_phrase or "chu_nhan_bi_mat_v2_2026"),
                                    "✅ Đã nâng cấp két sắt. Hãy xác minh Chủ nhân ở Tab 1 để hoàn tất."):
                        st.rerun()
        elif not engine.is_initialized:
            st.markdown("#### ✨ Tạo két sắt mới")
            with st.form("create_form"):
                p1 = st.text_input("Passphrase (≥ 8 ký tự)", type="password")
                p2 = st.text_input("Nhập lại passphrase", type="password")
                st.caption("Passphrase không được lưu ở đâu cả — quên là mất két sắt.")
                if st.form_submit_button("Tạo két sắt", type="primary", width="stretch"):
                    if p1 != p2:
                        st.error("Hai lần nhập passphrase không khớp.")
                    elif run_action(lambda: engine.create_vault(p1)):
                        st.rerun()
        else:
            st.markdown("#### 🔐 Bảo mật")
            st.caption("Két sắt được mã hóa bằng khóa chủ ngẫu nhiên, bọc bởi passphrase qua Scrypt. "
                       "Sai 5 lần liên tiếp sẽ bị khóa tạm 15 phút.")

    with col_heir, st.container(border=True):
        st.markdown("#### 🕊️ Cổng Người thừa kế")
        st.caption("Dành cho người thân được Chủ nhân niêm phong Di sản Số. Không cần passphrase của Chủ nhân.")
        if st.button("Vào cổng tiếp quản →", width="stretch", disabled=not engine.legacy_sealed):
            st.session_state["view"] = "heir"
            st.rerun()
        if not engine.legacy_sealed:
            st.caption("Chưa có Di sản Số được niêm phong.")


# =========================================================================
# KHỞI TẠO HỒ SƠ CHỦ NHÂN (GEN #1)
# =========================================================================

def render_registration(force: bool = False) -> None:
    st.markdown("### Thiết lập 'Hạt giống Số' ban đầu của Chủ nhân")
    st.info("💡 Ngày sinh, tên người thân, tài khoản và thói quen mật khẩu đều được băm một chiều HMAC-SHA256 "
            "rồi mã hóa trong két sắt. Hệ thống chỉ học cấu trúc và đặc trưng của bạn.")
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 👨‍👩‍👧‍👦 1. Thông tin cốt lõi & Đồ thị gia đình")
            owner_name = st.text_input("Họ và tên / Biệt danh Chủ nhân", value="HÀ HỮU HƯNG (1985)")
            dob = st.date_input("Ngày tháng năm sinh", value=None, min_value=MIN_DATE, format="YYYY-MM-DD")
            family = st.text_area("Gia đình bạn gồm những ai?",
                                  placeholder="Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi...",
                                  help="Mỗi người cách nhau bằng dấu phẩy. Có thể ghi kèm quan hệ (Bố, Mẹ, Con trai...).")
            traits = st.multiselect("Nét cá tính đặc trưng", ALL_TRAITS, default=["Thích công nghệ", "Logic & Lý trí", "Hướng nội"])
        with col2:
            st.markdown("##### ⌨️ 2. Hành vi, tư duy & tài khoản")
            password = st.text_input("Một mật khẩu bạn hay dùng (chỉ học cấu trúc, không lưu)", type="password")
            answer = st.text_area("Kỷ niệm hoặc thói quen nào khiến bạn thấy bình yên nhất?",
                                  placeholder="Viết tự nhiên theo văn phong của bạn (1-2 câu)...")
            google = st.text_input("🌐 Google (tùy chọn)", placeholder="user@gmail.com")
            apple = st.text_input("🍎 Apple ID (tùy chọn)", placeholder="user@icloud.com")
            facebook = st.text_input("📘 Facebook (tùy chọn)", placeholder="fb.com/username")
        submitted = st.form_submit_button("🚀 Mã hóa & Lưu hồ sơ Chủ nhân gốc", type="primary", width="stretch")

    if submitted:
        if not dob or not family.strip() or not password or not answer.strip():
            st.error("⚠️ Vui lòng điền đầy đủ ngày sinh, gia đình, mật khẩu mẫu và câu trả lời!")
            return
        data = {"owner_name": owner_name, "dob": date_text(dob), "family": family, "traits": traits,
                "password": password, "answer": answer, "google": google, "apple": apple, "facebook": facebook}
        if run_action(lambda: engine.register_owner(data, force=force),
                      "✅ Đã tạo 'Hạt giống Số' của Chủ nhân. Hãy xác minh ở Tab 1 để mở các thao tác nhạy cảm."):
            st.session_state.pop("reinit", None)
            st.session_state.pop("last_verify", None)
            st.rerun()


# =========================================================================
# TAB 1 — XÁC MINH & TIẾN HÓA
# =========================================================================

def render_verify_tab(profile: dict) -> None:
    if engine.migration_pending:
        st.info("⬆️ **Xác minh lần đầu để hoàn tất nâng cấp V2 → V3.** Lần này hệ thống chấm bằng thuật toán V2 "
                "(ngưỡng 72%); sau đó mô hình V3 được dựng từ chính dữ liệu bạn nhập.")
    col_form, col_result = st.columns([1.15, 1])
    with col_form, st.container(border=True):
        st.markdown("##### Nhập dữ liệu để AI nhận ra bạn")
        with st.form("verify_form"):
            dob = st.date_input("Ngày sinh", value=None, min_value=MIN_DATE, format="YYYY-MM-DD")
            family = st.text_input("Kể tên vài người thân", placeholder="Vợ Trần Thị C, Con trai Hà Minh Khôi...")
            traits = st.multiselect("Cá tính hiện tại (có thể thay đổi theo năm tháng)", ALL_TRAITS,
                                    default=[t for t in profile.get("traits_saved", []) if t in ALL_TRAITS])
            password = st.text_input("Một mật khẩu theo thói quen của bạn", type="password")
            answer = st.text_area("Điều gì làm bạn thấy bình yên nhất?")
            with st.expander("🔗 Tài khoản liên kết (Google / Apple / Facebook)"):
                google = st.text_input("🌐 Google", key="v_google")
                apple = st.text_input("🍎 Apple ID", key="v_apple")
                facebook = st.text_input("📘 Facebook", key="v_fb")
            submitted = st.form_submit_button("🔍 Phân tích & Xác minh Chủ nhân", type="primary", width="stretch")
        if submitted:
            data = {"dob": date_text(dob), "family": family, "traits": traits, "password": password, "answer": answer,
                    "google": google, "apple": apple, "facebook": facebook}
            result = {}
            if run_action(lambda: result.update(engine.verify_owner(data))):
                st.session_state["last_verify"] = result
                st.rerun()

    with col_result, st.container(border=True):
        res = st.session_state.get("last_verify")
        if not res:
            st.markdown("##### 📊 Chữ ký số của Chủ nhân")
            show_chart(plot_soul_radar(profile.get("radar_baseline", {})))
        else:
            if res["is_owner"]:
                note = "hoàn tất nâng cấp V2 → V3 và " if res.get("migrated") else ""
                st.success(f"🎉 **XÁC NHẬN CHỦ NHÂN ({res['owner_name']})** — {note}tiến hóa lên **Gen #{res['generation']}**")
            else:
                st.error("🚨 **CẢNH BÁO NGƯỜI LẠ!** Không nhận ra Chủ nhân.")
            st.metric("Điểm tin cậy", f"{res['trust_score'] * 100:.1f}%", f"ngưỡng {res['threshold'] * 100:.0f}%",
                      delta_color="off")
            st.progress(min(1.0, res["trust_score"]))
            if not res["gate_passed"]:
                st.caption("⛔ Cổng tri thức chưa đạt: cần đúng ngày sinh hoặc ít nhất một nửa số người thân.")
            show_chart(plot_soul_radar(res["saved_radar"], res["curr_radar"]))
            for pillar in PILLARS:
                value = res["pillars"].get(pillar)
                label = PILLAR_LABELS[pillar]
                if value is None:
                    st.caption(f"{label}: — (chưa liên kết)")
                else:
                    st.progress(min(1.0, value), text=f"{label}: {value * 100:.0f}%")
        history = profile.get("trust_history", [])
        if history:
            st.caption("Lịch sử điểm tin cậy (xanh: Chủ nhân · đỏ: bị từ chối)")
            threshold = res["threshold"] if res else engine.settings.owner_threshold
            show_chart(plot_trust_history(history, threshold))


# =========================================================================
# TAB 2 — HỘ CHIẾU DANH TÍNH SỐ
# =========================================================================

def render_passport_tab(profile: dict) -> None:
    traits = esc(", ".join(profile.get("traits_saved", [])) or "Chưa cập nhật")
    owner = esc(profile.get("owner_name"))
    soul_id = esc(engine.soul_id or "Đang chờ hoàn tất nâng cấp")
    st.markdown(f"""
    <div class="passport-box">
        <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #059669;padding-bottom:12px;margin-bottom:16px;">
            <div>
                <h3 style="margin:0;color:#065F46;">🏛️ CHỨNG NHẬN DANH TÍNH SỐ & AI ĐỒNG HÀNH</h3>
                <div style="font-size:13px;color:#047857;font-weight:600;">Evolving Digital Soul Passport & Accountable Identity</div>
            </div>
            <span style="background:#D1FAE5;color:#065F46;padding:4px 10px;border-radius:6px;font-weight:700;font-size:13px;">GEN #{int(profile.get('generation', 1))}</span>
        </div>
        <div style="font-size:15px;line-height:1.8;color:#1E293B;">
            <p><b>Chủ nhân hợp pháp:</b> <span style="color:#0F172A;font-weight:700;">{owner}</span></p>
            <p><b>Mã định danh Linh hồn Số (Public Soul ID):</b> <code style="font-size:15px;color:#059669;background:#FFFFFF;padding:2px 8px;border:1px solid #A7F3D0;border-radius:4px;">{soul_id}</code></p>
            <p><b>Bản sắc & Cá tính cốt lõi:</b> <i>{traits}</i></p>
            <p><b>Thời gian tạo lập:</b> {esc(profile.get('created_at', 'N/A'))}</p>
            <hr style="border:0;border-top:1px dashed #CBD5E1;margin:15px 0;">
            <div style="font-size:13px;color:#475569;background:#FFFFFF;padding:12px;border-radius:8px;border:1px solid #E2E8F0;">
                <b>Tuyên ngôn Trách nhiệm Xã hội Số:</b> Bản sao AI mang mã định danh <code>{soul_id}</code> này đại diện cho ý chí, danh dự và đạo đức của chủ nhân <b>{owner}</b> trên không gian mạng, cam kết hoạt động vì cộng đồng và thượng tôn pháp luật.<br>
                <span style="color:#2563EB;font-weight:600;font-size:12px;">Kiến trúc lõi sáng lập bởi: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X.</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    with st.expander("🔐 Cấu trúc dữ liệu đã che (Zero-Knowledge Disk Inspection)"):
        st.caption("Chỉ hiển thị cấu trúc, độ dài và digest rút gọn — không lộ nội dung gốc.")
        st.json(mask_profile(profile))


# =========================================================================
# TAB 3 — DI SẢN SỐ (PHÍA CHỦ NHÂN)
# =========================================================================

def render_legacy_tab(profile: dict) -> None:
    status = engine.legacy_status()
    pending_v2 = profile.get("legacy_v2_pending")
    if pending_v2 and not status:
        st.warning("📦 **Di sản từ V2 cần niêm phong lại** — danh mục tài sản và lời nhắn đã được điền sẵn. "
                   "Cho tới khi niêm phong lại, người thừa kế chưa thể tiếp quản.")
    st.caption("Nguyên tắc: Chủ nhân còn hoạt động (< ngưỡng) → tài sản khóa, người thân là bạn đồng hành. "
               "Vắng mặt đủ ngưỡng (mặc định 730 ngày) → mở cổng tiếp quản với xác thực kép tri thức + sinh trắc.")

    col_status, col_seal = st.columns(2)
    with col_status, st.container(border=True):
        st.markdown("##### ⏳ Đồng hồ Dead Man's Switch")
        demo_slider("demo_owner")
        if not status:
            st.info("Chưa niêm phong Di sản Số.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Vắng mặt", f"{status['elapsed_days']:.0f} ngày")
            c2.metric("Ngưỡng", f"{status['threshold_days']} ngày")
            c3.metric("Còn lại", f"{status['remaining_days']:.0f} ngày")
            st.progress(min(1.0, status["elapsed_days"] / status["threshold_days"]))
            if status["claimed"]:
                state = '<span class="es-pill red">Đã được tiếp quản — xác minh để thu hồi</span>'
            elif status["is_unlockable"]:
                state = '<span class="es-pill red">Cổng tiếp quản đang mở</span>'
            elif status["warning"]:
                state = '<span class="es-pill amber">Cảnh báo: sắp chạm ngưỡng — hãy xác minh</span>'
            else:
                state = '<span class="es-pill blue">Chủ nhân đang hoạt động</span>'
            method = {"sface": '<span class="es-pill green">SFace · bảo đảm cao</span>',
                      "histogram": '<span class="es-pill amber">Histogram · bảo đảm thấp</span>'}.get(
                status["biometric_method"], '<span class="es-pill gray">Không có</span>')
            st.markdown(f"""
            | | |
            |---|---|
            | **Người thừa kế** | {esc(status['heir_name_display'])} |
            | **Tài sản niêm phong** | {status['asset_count']} mục (mã hóa bằng mật ước) |
            | **Lớp sinh trắc** | {method} |
            | **Trạng thái** | {state} |
            """, unsafe_allow_html=True)
            if st.button("Hủy niêm phong Di sản", disabled=not engine.owner_verified, width="stretch"):
                if run_action(engine.revoke_legacy, "Đã hủy niêm phong Di sản Số."):
                    st.rerun()

    with col_seal, st.container(border=True):
        st.markdown("##### ✍️ Niêm phong / cập nhật Di sản")
        verified = engine.owner_verified
        if not verified:
            st.info("🔒 Xác minh Chủ nhân ở Tab 1 (trong 15 phút gần nhất) để niêm phong.")
        defaults = pending_v2 or {}
        with st.form("seal_form"):
            c1, c2 = st.columns(2)
            heir_name = c1.text_input("Họ tên người thừa kế", value=defaults.get("heir_name_display", ""))
            heir_email = c2.text_input("Email người thừa kế")
            secret = st.text_input(f"Mật ước gia đình (≥ {MIN_FAMILY_SECRET_LENGTH} ký tự, chỉ người nhà biết)", type="password")
            secret2 = st.text_input("Nhập lại mật ước", type="password")
            images = st.file_uploader("Ảnh người thừa kế (1–3 ảnh, mỗi ảnh đúng 1 khuôn mặt · không lưu ảnh)",
                                      type=["jpg", "jpeg", "png"], accept_multiple_files=True)
            assets = st.text_area("Danh mục bản quyền, tác phẩm & tài sản số (mỗi dòng 1 mục)",
                                  value="\n".join(defaults.get("assets", [])))
            message = st.text_area("Lời nhắn gửi người thân", value=defaults.get("message", ""))
            days = st.number_input("Ngưỡng vắng mặt (ngày)", min_value=1 if engine.demo_mode else 30, max_value=3650,
                                   value=int(defaults.get("inactivity_threshold_days", engine.settings.inactivity_days)))
            submitted = st.form_submit_button("🔒 Niêm phong Di sản Số", type="primary", width="stretch", disabled=not verified)
        if submitted:
            if secret != secret2:
                st.error("Hai lần nhập mật ước không khớp.")
                return
            asset_list = [line.strip() for line in assets.splitlines() if line.strip()]
            heir_images = [f.getvalue() for f in images[:3]] if images else None
            with st.spinner("Đang niêm phong (lần đầu dùng sinh trắc sẽ tải model YuNet/SFace ~39 MB)..."):
                ok = run_action(lambda: engine.seal_legacy(
                    heir_name=heir_name, heir_email=heir_email, family_secret=secret, assets=asset_list,
                    message=message, heir_images=heir_images, inactivity_days=int(days),
                ), f"✅ Đã niêm phong Di sản Số cho {heir_name} (ngưỡng {int(days)} ngày).")
            if ok:
                st.rerun()


# =========================================================================
# TAB 4 — NHẬT KÝ KIỂM TOÁN
# =========================================================================

def render_audit_tab() -> None:
    integrity = engine.audit_integrity()
    if integrity["ok"]:
        st.markdown(f'<span class="es-pill green">✓ Chuỗi băm toàn vẹn · {integrity["entries"]} sự kiện</span>',
                    unsafe_allow_html=True)
    elif integrity.get("reason") == "anchor_missing":
        st.error("⚠️ Nhật ký kiểm toán đã bị viết lại hoặc xóa (không còn khớp neo trong hồ sơ).")
    else:
        st.error(f"⚠️ Chuỗi băm đứt tại dòng {integrity['broken_at'] + 1} — nhật ký đã bị chỉnh sửa.")

    rows = []
    for event in reversed(engine.audit_events(50)):
        extra = {k: v for k, v in event.items() if k not in {"ts", "event", "result", "prev", "hash"} and v is not None}
        rows.append({
            "Thời gian": format_ts(event.get("ts", 0)),
            "Sự kiện": EVENT_LABELS.get(event.get("event"), event.get("event")),
            "Kết quả": event.get("result"),
            "Chi tiết": ", ".join(f"{k}={v}" for k, v in extra.items()),
        })
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Chưa có sự kiện nào.")


# =========================================================================
# TAB 5 — CÀI ĐẶT
# =========================================================================

def render_settings_tab() -> None:
    verified = engine.owner_verified
    if not verified:
        st.info("🔒 Các thao tác dưới đây yêu cầu xác minh Chủ nhân ở Tab 1.")
    col_pass, col_danger = st.columns(2)
    with col_pass, st.container(border=True):
        st.markdown("##### 🔑 Đổi passphrase")
        with st.form("passphrase_form"):
            p1 = st.text_input("Passphrase mới (≥ 8 ký tự)", type="password")
            p2 = st.text_input("Nhập lại", type="password")
            if st.form_submit_button("Đổi passphrase", type="primary", width="stretch", disabled=not verified):
                if p1 != p2:
                    st.error("Hai lần nhập passphrase không khớp.")
                elif run_action(lambda: engine.change_passphrase(p1), "✅ Đã đổi passphrase."):
                    st.rerun()
    with col_danger, st.container(border=True):
        st.markdown("##### ⚠️ Vùng nguy hiểm")
        st.write("Khởi tạo lại hồ sơ Chủ nhân sẽ xóa lịch sử tiến hóa và **hủy Di sản Số** đã niêm phong.")
        confirm = st.checkbox("Tôi là Chủ nhân và hiểu hậu quả", disabled=not verified)
        if st.button("Khởi tạo lại hồ sơ", disabled=not (verified and confirm), width="stretch"):
            st.session_state["reinit"] = True
            st.rerun()


# =========================================================================
# MÀN HÌNH CHÍNH (KÉT ĐÃ MỞ)
# =========================================================================

def render_app() -> None:
    st.markdown("## 🧬 Hệ thống AI Ghi nhớ & Nhận diện Chủ nhân Tiến hóa")
    st.markdown("<span class='es-muted'>Bảo vệ quyền riêng tư tuyệt đối — không phụ thuộc sinh trắc học khi hoạt động, "
                "tự học khi Chủ nhân già đi, tích hợp chuyển giao Di sản Số.</span>", unsafe_allow_html=True)
    show_flash()

    profile = engine.profile
    if profile is None:
        render_registration()
        return
    if st.session_state.get("reinit") and engine.owner_verified:
        if st.button("← Hủy khởi tạo lại"):
            st.session_state.pop("reinit")
            st.rerun()
        render_registration(force=True)
        return

    tabs = st.tabs(["1️⃣ Xác minh & Tiến hóa", "2️⃣ Hộ chiếu Số", "3️⃣ Di sản Số", "4️⃣ Nhật ký", "5️⃣ Cài đặt"])
    with tabs[0]:
        render_verify_tab(profile)
    with tabs[1]:
        render_passport_tab(profile)
    with tabs[2]:
        render_legacy_tab(profile)
    with tabs[3]:
        render_audit_tab()
    with tabs[4]:
        render_settings_tab()


# =========================================================================
# MÀN HÌNH E — CỔNG NGƯỜI THỪA KẾ
# =========================================================================

def render_heir_portal() -> None:
    if st.button("← Quay lại màn hình khóa"):
        st.session_state["view"] = "lock"
        st.session_state.pop("claim_result", None)
        st.rerun()
    st.markdown("### 🕊️ Cổng tiếp quản Di sản Số")
    st.caption("Xác thực kép: tri thức gia đình + sinh trắc học. Tài sản chỉ được bàn giao khi Chủ nhân đã vắng mặt đủ ngưỡng.")

    col_form, col_result = st.columns(2)
    with col_form, st.container(border=True):
        demo_slider("demo_heir")
        method = st.radio("Phương thức quét sinh trắc", ["📷 Camera trực tiếp", "⬆️ Tải ảnh"], horizontal=True)
        with st.form("claim_form"):
            c1, c2 = st.columns(2)
            kin_name = c1.text_input("Họ tên của bạn")
            kin_email = c2.text_input("Email")
            owner_dob = st.date_input("Ngày sinh của Chủ nhân", value=None, min_value=MIN_DATE, format="YYYY-MM-DD")
            family = st.text_input("Các thành viên khác trong gia đình")
            secret = st.text_input("Mật ước gia đình", type="password")
            if method.startswith("📷"):
                shot = st.camera_input("Quét khuôn mặt")
            else:
                shot = st.file_uploader("Ảnh xác thực", type=["jpg", "jpeg", "png"])
            submitted = st.form_submit_button("🗝️ Xác thực & Mở khóa Di sản", type="primary", width="stretch")
        if submitted:
            result = {}
            with st.spinner("Đang xác thực..."):
                ok = run_action(lambda: result.update(engine.claim_legacy(
                    kin_name=kin_name, kin_email=kin_email, owner_dob=date_text(owner_dob), family_members=family,
                    family_secret=secret, live_image=shot.getvalue() if shot else None,
                )))
            if ok:
                result["kin_name"], result["kin_email"] = kin_name, kin_email
                st.session_state["claim_result"] = result

    with col_result:
        res = st.session_state.get("claim_result")
        if not res:
            st.info("Điền thông tin và quét khuôn mặt để xác thực.")
            return
        c1, c2 = st.columns(2)
        c1.metric("Tri thức gia đình", f"{res['knowledge_score'] * 100:.0f}%")
        bio = res.get("bio")
        if bio:
            c2.metric(f"Sinh trắc ({'SFace' if bio['method'] == 'sface' else 'Histogram'})", f"{bio['cosine']:.2f}",
                      f"ngưỡng {bio['threshold']:.3f}", delta_color="off")
        else:
            c2.metric("Sinh trắc", "—")

        if res["is_unlocked"]:
            st.balloons()
            assets_html = "".join(f"<li style='margin-bottom:6px;'><code>{esc(item)}</code></li>" for item in res["assets"])
            st.markdown(f"""
            <div class="legacy-box">
                <h4 style="color:#92400E;margin-top:0;">📜 CHỨNG THƯ CHUYỂN GIAO BẢN QUYỀN & DI SẢN SỐ</h4>
                <p><b>Chủ nhân sáng lập:</b> {esc(res['owner_name'])} <i>(Kiến trúc: HÀ HỮU HƯNG 1985 — KỸ SƯ AI THẾ HỆ 8X)</i></p>
                <p><b>Người thừa kế hợp pháp:</b> {esc(res['kin_name'])} ({esc(res['kin_email'])})</p>
                <p><b>Di thư của Chủ nhân:</b> <i>"{esc(res['message'])}"</i></p>
                <hr style="border:0;border-top:1px solid #FDE68A;margin:15px 0;">
                <p style="color:#B45309;font-weight:700;">🔓 Danh mục bản quyền & tài sản số:</p>
                <ul>{assets_html}</ul>
                <p style="font-size:12px;color:#64748B;">Nếu Chủ nhân quay lại và xác minh thành công, quyền tiếp quản tự động bị thu hồi.</p>
            </div>
            """, unsafe_allow_html=True)
        elif res["is_verified"]:
            st.info(f"🛡️ Xác thực đúng, nhưng Chủ nhân vẫn trong chu kỳ hoạt động (vắng mặt {res['elapsed_days']:.0f}/"
                    f"{res['threshold_days']} ngày). Tài sản tiếp tục được khóa — bạn ở chế độ bạn đồng hành.")
        else:
            st.error(f"🚨 Xác thực thất bại. {res.get('reason', '')}")


# =========================================================================
# ĐIỀU HƯỚNG
# =========================================================================

render_sidebar()
if st.session_state.get("view") == "heir":
    render_heir_portal()
elif engine.is_unlocked:
    render_app()
else:
    render_lock_screen()
