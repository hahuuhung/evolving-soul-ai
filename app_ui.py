"""
Giao Diện Ứng Dụng Trực Quan — Evolving Soul AI (White Theme Chủ Đạo)
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
Bản quyền: Giấy phép Mã nguồn Mở bắt buộc ghi nhận nguồn gốc (Attribution Required)
"""

import os
import json
import hashlib
import streamlit as st
import plotly.graph_objects as go
from core_engine import EvolvingOwnerAI_V2

# =========================================================================
# CẤU HÌNH TRANG & WHITE THEME CHỦ ĐẠO
# =========================================================================
st.set_page_config(
    page_title="Evolving Soul AI — Nhận Diện Chủ Nhân & Thừa Kế Di Sản Số",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS ép White Theme chuẩn quốc tế, sang trọng, tinh tế và chuyên nghiệp
st.markdown("""
<style>
    /* Nền tổng thể White Theme */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Container Card trắng sang trọng */
    .white-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }

    .badge-author {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-left: 4px solid #2563EB;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 15px;
    }

    .passport-box {
        background: linear-gradient(135deg, #FFFFFF 0%, #F0FDF4 100%);
        border: 2px solid #059669;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(5, 150, 105, 0.08);
    }

    .legacy-box {
        background: linear-gradient(135deg, #FFFFFF 0%, #FEF3C7 100%);
        border: 2px solid #D97706;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 15px -3px rgba(217, 119, 6, 0.08);
    }

    /* Tinh chỉnh typography */
    h1, h2, h3, h4 {
        color: #0F172A;
        font-weight: 700;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F1F5F9;
        padding: 6px;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 18px;
        font-weight: 600;
        color: #475569;
        background-color: transparent;
    }

    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #2563EB !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    /* Button Primary chuẩn White Theme */
    div.stButton > button[kind="primary"] {
        background-color: #2563EB;
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1D4ED8;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo Lõi AI
ai = EvolvingOwnerAI_V2()
profile = ai.load_profile()

ALL_TRAITS = [
    "Hướng nội", "Hướng ngoại", "Logic & Lý trí", "Giàu cảm xúc",
    "Thích công nghệ", "Yêu nghệ thuật", "Cầu toàn", "Phóng khoáng",
    "Thức khuya", "Dậy sớm", "Thích sự yên tĩnh", "Ưa mạo hiểm"
]

# =========================================================================
# SIDEBAR: THÔNG TIN HỆ THỐNG & BẢN QUYỀN TÁC GIẢ
# =========================================================================
with st.sidebar:
    st.markdown("### 🛡️ Evolving Soul AI")
    st.caption("Mô hình AI Nhỏ Gọn Nhận Diện Chủ Nhân Phi Sinh Trắc Học & Thừa Kế Di Sản Số")
    st.divider()

    if profile:
        st.success(f"🟢 **Chủ nhân**: {profile.get('owner_name', 'Chủ Nhân')}")
        st.metric(label="Thế hệ Tiến hóa (Generation)", value=f"Gen #{profile.get('generation', 1)}")
        st.caption(f"🕒 Cập nhật: `{profile.get('last_updated', 'N/A')}`")
    else:
        st.warning("🟡 Chưa có hồ sơ Chủ nhân. Vui lòng thiết lập ở Tab 1.")

    st.divider()
    st.markdown("#### 🔗 Liên kết Định danh (SSO / OAuth)")
    st.caption("Cung cấp token/email các nền tảng để tăng độ tin cậy:")
    oauth_google = st.text_input("🌐 Google Account", placeholder="user@gmail.com", key="sb_google")
    oauth_apple = st.text_input("🍎 Apple ID", placeholder="user@icloud.com", key="sb_apple")
    oauth_fb = st.text_input("📘 Facebook UID", placeholder="fb.com/username", key="sb_fb")

    # Dấu ấn Bản quyền Tác giả (Attribution Requirement)
    st.divider()
    st.markdown("""
    <div class="badge-author">
        <div style="font-size: 11px; color: #64748B; font-weight: 600; text-transform: uppercase;">Mã Nguồn Mở Có Bản Quyền</div>
        <div style="font-size: 14px; font-weight: 700; color: #1E3A8A; margin-top: 2px;">Tác giả: HÀ HỮU HƯNG (1985)</div>
        <div style="font-size: 12px; color: #2563EB; font-weight: 600;">⚡ KỸ SƯ AI THẾ HỆ 8X</div>
        <div style="font-size: 11px; color: #64748B; margin-top: 4px;">Kiến trúc: Evolving Digital Soul & Dead Man's Switch 730 ngày</div>
    </div>
    """, unsafe_allow_html=True)


# =========================================================================
# HÀM TRỢ GIÚP VẼ RADAR CHART (WHITE THEME POLAR)
# =========================================================================
def plot_soul_radar(baseline_dict: dict, current_dict: dict | None = None):
    categories = list(baseline_dict.keys())
    base_values = list(baseline_dict.values())
    base_values += base_values[:1]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=base_values,
        theta=categories + [categories[0]],
        fill='toself',
        name='Chữ ký Gốc (Đã lưu)',
        line_color='#059669',
        fillcolor='rgba(5, 150, 105, 0.2)'
    ))

    if current_dict:
        curr_values = list(current_dict.values())
        curr_values += curr_values[:1]
        fig.add_trace(go.Scatterpolar(
            r=curr_values,
            theta=categories + [categories[0]],
            fill='toself',
            name='Phiên kiểm tra hiện tại',
            line_color='#2563EB',
            fillcolor='rgba(37, 99, 235, 0.25)'
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor='#E2E8F0', linecolor='#CBD5E1'),
            angularaxis=dict(gridcolor='#E2E8F0', linecolor='#CBD5E1'),
            bgcolor='#F8FAFC'
        ),
        paper_bgcolor='#FFFFFF',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=30, r=30, t=30, b=40),
        height=380
    )
    return fig


# =========================================================================
# HEADER GIAO DIỆN CHÍNH
# =========================================================================
st.markdown("## 🧬 Hệ Thống AI Ghi Nhớ & Nhận Diện Chủ Nhân Tiến Hóa")
st.markdown(
    "<span style='color: #64748B; font-size: 15px;'>Mã nguồn mở bảo vệ quyền riêng tư tuyệt đối — Không phụ thuộc sinh trắc học vật lý khi hoạt động, tự học khi chủ nhân già đi, tích hợp chuyển giao di sản số 2 năm.</span>",
    unsafe_allow_html=True
)
st.write("")

tab1, tab2, tab3, tab4 = st.tabs([
    "1️⃣ Khởi Tạo Hồ Sơ (Training)",
    "2️⃣ Xác Minh & Tiến Hóa (Verification)",
    "3️⃣ Hộ Chiếu Danh Tính Số (Data Vault)",
    "4️⃣ Di Sản Số & Thừa Kế 2 Năm (Legacy)"
])

# =========================================================================
# TAB 1: KHỞI TẠO HỒ SƠ CHỦ NHÂN GỐC
# =========================================================================
with tab1:
    st.markdown("### Thiết lập 'Hạt giống Số' Ban đầu của Chủ Nhân")
    st.info("💡 Mọi thông tin nhạy cảm (mật khẩu, tên người thân, ngày sinh) đều được băm một chiều SHA-256 và mã hóa Fernet. Hệ thống chỉ học cấu trúc và đặc trưng của bạn.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### 👨‍👩‍👧‍👦 1. Thông tin Cốt lõi & Đồ thị Gia đình")
        owner_name = st.text_input("Họ và tên / Biệt danh Chủ nhân:", value="HÀ HỮU HƯNG (1985)")
        dob = st.date_input("Ngày tháng năm sinh của bạn:", value=None, key="t1_dob")
        family_str = st.text_area(
            "Gia đình bạn gồm những ai và tên gì?",
            placeholder="Ví dụ: Bố Hà Văn A, Mẹ Nguyễn Thị B, Vợ Trần Thị C, Con trai Hà Minh Khôi...",
            help="AI sẽ trích xuất mạng lưới từ khóa gia đình độc lập thứ tự.",
            key="t1_family"
        )
        traits = st.multiselect(
            "Chọn các nét cá tính đặc trưng của bạn:",
            ALL_TRAITS,
            default=["Thích công nghệ", "Logic & Lý trí", "Hướng nội"],
            key="t1_traits"
        )

    with col2:
        st.markdown("##### ⌨️ 2. Hành vi & Tư duy Ngữ nghĩa (Zero-Knowledge)")
        pw_sample = st.text_input(
            "Nhập 1 mật khẩu bạn hay dùng (Chỉ học cấu trúc, không lưu mật khẩu):",
            type="password",
            key="t1_pw"
        )
        sec_answer = st.text_area(
            "Câu hỏi mở: 'Kỷ niệm hoặc thói quen nào khiến bạn thấy bình yên nhất?'",
            placeholder="Hãy viết tự nhiên theo văn phong của bạn (1-2 câu)...",
            key="t1_ans"
        )

    if st.button("🚀 Mã hóa & Lưu Hồ Sơ Chủ Nhân Gốc", type="primary", use_container_width=True):
        if not dob or not family_str or not pw_sample or not sec_answer:
            st.error("⚠️ Vui lòng điền đầy đủ Ngày sinh, Thông tin gia đình, Mật khẩu mẫu và Câu trả lời!")
        else:
            data_pkg = {
                "owner_name": owner_name,
                "google": oauth_google,
                "apple": oauth_apple,
                "facebook": oauth_fb,
                "dob": str(dob),
                "family": family_str,
                "traits": traits,
                "password": pw_sample,
                "answer": sec_answer
            }
            new_prof = ai.register_owner(data_pkg)
            st.success("✅ Đã tạo và mã hóa thành công 'Hạt giống Số' của Chủ nhân! Chuyển sang Tab 2 để trải nghiệm.")
            st.rerun()

# =========================================================================
# TAB 2: XÁC MINH CHỦ NHÂN & TIẾN HÓA TRƯỢT THỜI GIAN
# =========================================================================
with tab2:
    st.markdown("### Kiểm Tra Nhận Diện & Tự Động Tiến Hóa (Co-Evolution)")
    if not profile:
        st.warning("⚠️ Chưa có hồ sơ Chủ nhân. Vui lòng tạo hồ sơ ở Tab 1 trước!")
    else:
        v_col1, v_col2 = st.columns([1.2, 1])
        with v_col1:
            st.markdown("##### Nhập dữ liệu để AI đối chiếu & nhận ra bạn:")
            v_dob = st.date_input("Xác nhận Ngày sinh:", value=None, key="v_dob")
            v_family = st.text_input(
                "Kể tên một vài người thân trong gia đình bạn:",
                placeholder="Ví dụ: Vợ Trần Thị C, Con trai Hà Minh Khôi...",
                key="v_family"
            )
            v_traits = st.multiselect(
                "Cá tính hiện tại của bạn (có thể thay đổi nhẹ theo năm tháng):",
                ALL_TRAITS,
                default=profile.get("traits_saved", ["Thích công nghệ"]),
                key="v_traits"
            )
            v_pw = st.text_input("Nhập một mật khẩu theo thói quen của bạn:", type="password", key="v_pw")
            v_ans = st.text_area("Trả lời ngắn: 'Điều gì làm bạn thấy bình yên nhất?'", key="v_ans")

            verify_btn = st.button("🔍 Phân Tích & Xác Minh Chủ Nhân", type="primary", use_container_width=True)

        with v_col2:
            st.markdown("##### 📊 Đối chiếu Chữ Ký Số (Radar Chart)")
            if verify_btn:
                v_pkg = {
                    "google": oauth_google,
                    "apple": oauth_apple,
                    "facebook": oauth_fb,
                    "dob": str(v_dob),
                    "family": v_family,
                    "traits": v_traits,
                    "password": v_pw,
                    "answer": v_ans
                }
                res = ai.verify_and_evolve(v_pkg)

                if res:
                    st.plotly_chart(plot_soul_radar(res["saved_radar"], res["curr_radar"]), use_container_width=True)
                    score_pct = res["trust_score"] * 100

                    if res["is_owner"]:
                        st.success(f"🎉 **XÁC NHẬN CHỦ NHÂN ({res['owner_name']})!** — Độ khớp: **{score_pct:.1f}%**")
                        st.caption(f"🧬 *Hồ sơ đã học thêm thói quen mới và tự tiến hóa lên **Gen #{res['generation']}**.*")
                    else:
                        st.error(f"🚨 **CẢNH BÁO NGƯỜI LẠ!** — Độ khớp: **{score_pct:.1f}%** (Yêu cầu >= 72%)")

                    c1, c2, c3 = st.columns(3)
                    c1.metric("Vector Hành vi", f"{res['vec_sim']*100:.0f}%")
                    c2.metric("Trí nhớ Gia đình", f"{res['fam_sim']*100:.0f}%")
                    c3.metric("Văn phong Ngữ nghĩa", f"{res['word_sim']*100:.0f}%")
            else:
                st.plotly_chart(plot_soul_radar(profile.get("radar_baseline", {})), use_container_width=True)

# =========================================================================
# TAB 3: HỘ CHIẾU DANH TÍNH SỐ & DATA VAULT
# =========================================================================
with tab3:
    st.markdown("### Hộ Chiếu Danh Tính Số & Cam Kết Trách Nhiệm Xã Hội")
    if not profile:
        st.info("Chưa có dữ liệu Chủ nhân.")
    else:
        soul_hash = hashlib.sha256(json.dumps(profile["evolving_vector"]).encode()).hexdigest()[:16].upper()
        traits_display = ", ".join(profile.get("traits_saved", ["Chưa cập nhật"]))

        st.markdown(f"""
        <div class="passport-box">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #059669; padding-bottom: 12px; margin-bottom: 16px;">
                <div>
                    <h3 style="margin: 0; color: #065F46;">🏛️ CHỨNG NHẬN DANH TÍNH SỐ & AI ĐỒNG HÀNH</h3>
                    <div style="font-size: 13px; color: #047857; font-weight: 600;">Evolving Digital Soul Passport & Accountable Identity</div>
                </div>
                <div style="text-align: right;">
                    <span style="background: #D1FAE5; color: #065F46; padding: 4px 10px; border-radius: 6px; font-weight: 700; font-size: 13px;">GEN #{profile.get('generation', 1)}</span>
                </div>
            </div>
            <div style="font-size: 15px; line-height: 1.8; color: #1E293B;">
                <p><b>Chủ nhân hợp pháp:</b> <span style="color: #0F172A; font-weight: 700;">{profile.get('owner_name')}</span></p>
                <p><b>Mã định danh Linh hồn Số (Public Soul ID):</b> <code style="font-size: 15px; color: #059669; background: #FFFFFF; padding: 2px 8px; border: 1px solid #A7F3D0; border-radius: 4px;">SOUL-{soul_hash}</code></p>
                <p><b>Bản sắc & Cá tính cốt lõi:</b> <i>{traits_display}</i></p>
                <p><b>Thời gian tạo lập:</b> {profile.get('created_at', '2026-10-15')}</p>
                <hr style="border: 0; border-top: 1px dashed #CBD5E1; margin: 15px 0;">
                <div style="font-size: 13px; color: #475569; background: #FFFFFF; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0;">
                    <b>Tuyên ngôn Trách nhiệm Xã hội Số:</b> Bản sao AI mang mã định danh <code>SOUL-{soul_hash}</code> này đại diện cho ý chí, danh dự và đạo đức của chủ nhân <b>{profile.get('owner_name')}</b> trên không gian mạng, cam kết hoạt động vì cộng đồng và thượng tôn pháp luật.<br>
                    <span style="color: #2563EB; font-weight: 600; font-size: 12px;">Kiến trúc lõi sáng lập bởi: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X.</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")
        with st.expander("🔐 Xem Cấu Trúc Dữ Liệu Đã Mã Hóa (Zero-Knowledge Disk Inspection)"):
            st.json(profile)

# =========================================================================
# TAB 4: DI SẢN SỐ & THỪA KẾ 2 NĂM (DEAD MAN'S SWITCH)
# =========================================================================
with tab4:
    st.markdown("### 🏛️ Giao Thức Di Sản Số & Thừa Kế Bản Quyền (Dead Man's Switch)")
    st.caption("Nguyên tắc: Khi Chủ nhân còn online (< 2 năm): bảo mật độc quyền, người thân được nhận diện như bạn đồng hành. Khi Chủ nhân không online đủ 2 năm (730 ngày): Mở khóa xác thực Sinh trắc học khẩn cấp để chuyển giao tài sản số.")

    if not profile:
        st.warning("⚠️ Vui lòng khởi tạo Hồ sơ Chủ nhân ở Tab 1 trước!")
    else:
        col_setup, col_claim = st.columns(2)

        with col_setup:
            st.markdown("##### ✍️ 1. Niêm phong Di Sản & Người Kế Thừa (Dành cho Chủ nhân)")
            heir_name = st.text_input("Họ tên Người thân kế thừa:", value="Hà Minh Khôi", key="t4_heir_name")
            heir_email = st.text_input("Email Người thân:", value="khoi.ha@gmail.com", key="t4_heir_email")
            family_secret = st.text_input("Câu mật ước gia đình (Chỉ người nhà biết):", type="password", key="t4_secret")
            
            st.markdown("**📸 Đăng ký Mẫu Sinh Trắc Học Người Thừa Kế (Ảnh rõ mặt):**")
            bio_enroll_file = st.file_uploader(
                "Tải lên ảnh người thừa kế (AI trích xuất Vector 64 chiều, không lưu ảnh thô):",
                type=["jpg", "jpeg", "png"],
                key="t4_bio_enroll"
            )

            assets_input = st.text_area(
                "Danh mục Bản quyền, Tác phẩm & Tài sản Online cần bảo vệ (Mỗi mục 1 dòng):",
                value="- Bản quyền Mã nguồn Evolving Soul AI - Tác giả HÀ HỮU HƯNG (1985)\n- Kho lưu trữ Sáng tác & Bản thảo cá nhân: https://github.com/hahuuhung1985/evolving-soul-ai\n- Khóa giải mã Kho tài sản số trí tuệ: MASTER-KEY-8X-2026",
                key="t4_assets"
            )
            legacy_msg = st.text_area(
                "Lời nhắn gửi lại cho Người thân:",
                value="Con hãy tiếp tục phát triển dự án AI này và giữ vững đạo đức nghề nghiệp.",
                key="t4_msg"
            )

            if st.button("🔒 Niêm Phong Di Sản Số (Hẹn giờ 2 Năm = 730 Ngày)", type="primary", use_container_width=True):
                if not heir_name or not heir_email or not family_secret or not assets_input:
                    st.error("⚠️ Vui lòng điền đầy đủ Người kế thừa, Mật ước và Danh mục tài sản!")
                else:
                    bio_bytes = bio_enroll_file.read() if bio_enroll_file else None
                    assets_list = [line.strip() for line in assets_input.split("\n") if line.strip()]
                    ai.setup_digital_legacy(
                        heir_name=heir_name,
                        heir_email=heir_email,
                        family_secret=family_secret,
                        assets_list=assets_list,
                        message_to_kin=legacy_msg,
                        heir_bio_bytes=bio_bytes,
                        inactivity_days=730
                    )
                    st.success(f"✅ Đã niêm phong Di sản Số cho **{heir_name}** (Khóa bảo vệ 730 ngày offline)!")
                    st.rerun()

        with col_claim:
            st.markdown("##### 🕊️ 2. Cổng Tiếp Quản Di Sản (Sau 2 Năm Chủ Nhân Không Online)")
            if "legacy_config" not in profile:
                st.info("Chủ nhân chưa thiết lập Di sản Số.")
            else:
                sim_days = st.slider("⏳ [Mô phỏng Thử nghiệm] Số ngày Chủ nhân đã không online:", 0, 1000, 0, step=10)
                status = ai.check_inactivity_status(sim_days)

                if status["is_unlockable"]:
                    st.error(f"🚨 Chủ nhân đã vắng mặt **{status['elapsed_days']} ngày** (Vượt ngưỡng 730 ngày / 2 năm). **LỚP SINH TRẮC HỌC ĐÃ ĐƯỢC MỞ KHÓA!**")
                else:
                    remaining = max(0, round(730 - status['elapsed_days'], 1))
                    st.info(f"🛡️ Chủ nhân vẫn trong chu kỳ hoạt động (Còn **{remaining} ngày** nữa). Chế độ bảo vệ độc quyền đang bật.")

                k_name = st.text_input("Họ tên Người thân xác thực:", key="k_name")
                k_email = st.text_input("Email Người thân:", key="k_email")
                k_dob = st.date_input("Ngày sinh của Chủ nhân:", value=None, key="k_dob")
                k_fam = st.text_input("Kể tên các thành viên khác trong gia đình:", key="k_fam")
                k_secret = st.text_input("Nhập Câu mật ước gia đình:", type="password", key="k_secret")

                live_bio_bytes = None
                if status["is_unlockable"]:
                    st.markdown("---")
                    st.markdown("##### 📷 Bước Bắt Buộc Sau 2 Năm: Quét Sinh Trắc Học Người Thừa Kế")
                    bio_method = st.radio("Chọn phương thức quét sinh trắc:", ["Camera trực tiếp", "Tải ảnh xác thực"], horizontal=True)
                    if bio_method == "Camera trực tiếp":
                        cam_img = st.camera_input("Quét khuôn mặt xác thực qua Camera:")
                        if cam_img:
                            live_bio_bytes = cam_img.getvalue()
                    else:
                        up_img = st.file_uploader("Tải ảnh xác thực:", type=["jpg", "jpeg", "png"], key="k_bio_up")
                        if up_img:
                            live_bio_bytes = up_img.read()

                if st.button("🗝️ Xác Thực & Mở Khóa Tài Sản Di Sản Số", type="primary", use_container_width=True):
                    res = ai.verify_kin_with_biometrics(
                        kin_name=k_name,
                        kin_email=k_email,
                        owner_dob=str(k_dob),
                        other_family_members=k_fam,
                        family_secret_input=k_secret,
                        live_bio_bytes=live_bio_bytes,
                        simulated_days_offline=sim_days
                    )

                    c_k1, c_k2 = st.columns(2)
                    c_k1.metric("Điểm Tri thức Gia đình", f"{res['knowledge_score']*100:.1f}%", "Yêu cầu >= 70%")
                    c_k2.metric("Điểm Khớp Sinh trắc học", f"{res['bio_score']*100:.1f}%", "Yêu cầu >= 75%")

                    if not res["is_unlockable"]:
                        st.warning("⏳ Chưa đủ điều kiện 2 năm (730 ngày) Chủ nhân không online. Hãy kéo thanh trượt mô phỏng lên >= 730 ngày để thử nghiệm!")
                    elif res["is_unlocked"]:
                        st.balloons()
                        st.success(f"🎉 **XÁC NHẬN NGƯỜI THÂN TIẾP QUẢN HỢP PHÁP: {k_name.upper()}!**")
                        
                        assets_html = "".join([f"<li style='margin-bottom: 6px;'><code>{item}</code></li>" for item in res['assets']])
                        st.markdown(f"""
                        <div class="legacy-box">
                            <h4 style="color: #92400E; margin-top: 0;">📜 CHỨNG THƯ CHUYỂN GIAO BẢN QUYỀN & DI SẢN SỐ</h4>
                            <p><b>Chủ nhân sáng lập:</b> {res['owner_name']} <i>(Kiến trúc sư: HÀ HỮU HƯNG 1985 — KỸ SƯ AI THẾ HỆ 8X)</i></p>
                            <p><b>Người thừa kế hợp pháp:</b> {k_name} ({k_email})</p>
                            <p><b>Di thư của Chủ nhân:</b> <i>"{res['message']}"</i></p>
                            <hr style="border: 0; border-top: 1px solid #FDE68A; margin: 15px 0;">
                            <p style="color: #B45309; font-weight: 700;">🔓 Danh mục Bản quyền & Thành quả Sáng tạo Mở Khóa:</p>
                            <ul>{assets_html}</ul>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error("🚨 Xác thực thất bại! Dữ liệu Tri thức Gia đình hoặc Sinh trắc học không khớp với hồ sơ niêm phong.")
