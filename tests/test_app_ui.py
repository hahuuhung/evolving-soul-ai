"""
Kiểm thử giao diện Streamlit V3 bằng AppTest (chạy headless, không cần trình duyệt).

Hai giới hạn của AppTest được xử lý tại đây (không phải lỗi của ứng dụng):
  * date_input khởi tạo value=None không đặt được giá trị -> chạy trên bản sao app_ui.py có ngày mặc định.
  * Streamlit 1.50 (bản cuối hỗ trợ Python 3.9) không chạy tiếp được sau st.rerun() -> tạo phiên AppTest mới
    và mang theo session_state của ứng dụng.

Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
APP_KEYS = ("engine", "view", "last_verify", "claim_result", "demo_days", "flash", "reinit")
PASSPHRASE = "Passphrase-Chu-Nhan-8X"
SECRET = "Kỷ niệm phố cổ Hà Nội 1985"


@pytest.fixture
def app_file(tmp_path, monkeypatch) -> Path:
    source = (ROOT / "app_ui.py").read_text(encoding="utf-8")
    patched = source.replace("value=None, min_value=MIN_DATE", "value=datetime.date(1985, 5, 15), min_value=MIN_DATE")
    assert patched != source
    target = tmp_path / "app_ui.py"
    target.write_text(patched, encoding="utf-8")
    shutil.copytree(ROOT / "assets", tmp_path / "assets")
    monkeypatch.setenv("EVOLVING_SOUL_DEMO", "1")
    monkeypatch.setenv("EVOLVING_SOUL_VAULT_DIR", str(tmp_path / "vault"))
    monkeypatch.setenv("EVOLVING_SOUL_MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.delenv("EVOLVING_SOUL_PASSPHRASE", raising=False)
    return target


def find(widgets, prefix: str):
    for widget in widgets:
        if str(widget.label).startswith(prefix):
            return widget
    raise AssertionError(f"Không thấy '{prefix}' trong {[w.label for w in widgets]}")


def fresh(app_file: Path, old: AppTest | None = None) -> AppTest:
    new = AppTest.from_file(str(app_file), default_timeout=120)
    if old is not None:
        for key in APP_KEYS:
            if key in old.session_state:
                new.session_state[key] = old.session_state[key]
    new.run()
    assert not new.exception, [e.value for e in new.exception]
    return new


def act(app_file: Path, at: AppTest, widget) -> AppTest:
    """Bấm nút rồi chuyển sang phiên mới (tương đương trình duyệt sau st.rerun)."""
    widget.click().run()
    assert not at.exception, [e.value for e in at.exception]
    return fresh(app_file, at)


def test_full_owner_and_heir_journey(app_file):
    at = fresh(app_file)
    assert find(at.button, "Vào cổng tiếp quản").disabled  # chưa niêm phong di sản

    # Màn hình khóa -> tạo két sắt
    find(at.text_input, "Passphrase (").input(PASSPHRASE)
    find(at.text_input, "Nhập lại passphrase").input(PASSPHRASE)
    at = act(app_file, at, find(at.button, "Tạo két sắt"))

    # Khởi tạo hồ sơ Gen #1
    find(at.text_area, "Gia đình").input("Bố Hà Văn A, Vợ Trần Thị C, Con trai Hà Minh Khôi")
    find(at.text_input, "Một mật khẩu bạn hay dùng").input("HungAI@1985#Secret")
    find(at.text_area, "Kỷ niệm").input("Tôi thấy bình yên khi viết code AI ban đêm và uống trà nóng.")
    at = act(app_file, at, find(at.button, "🚀"))
    assert [t.label for t in at.tabs][:5] == ["1️⃣ Xác minh & Tiến hóa", "2️⃣ Hộ chiếu Số", "3️⃣ Di sản Số", "4️⃣ Nhật ký", "5️⃣ Cài đặt"]
    assert find(at.button, "🔒 Niêm phong").disabled
    assert find(at.button, "Đổi passphrase").disabled

    # Xác minh Chủ nhân (đã già đi, đổi mật khẩu theo thói quen)
    find(at.text_input, "Kể tên vài người thân").input("Vợ Trần Thị C, Con trai Ha Minh Khoi")
    find(at.text_input, "Một mật khẩu theo thói quen").input("HungAI@2031#NewPass")
    find(at.text_area, "Điều gì làm bạn").input("Viết code AI ban đêm và uống trà cùng gia đình.")
    at = act(app_file, at, find(at.button, "🔍"))
    assert any("XÁC NHẬN CHỦ NHÂN" in s.value and "Gen #2" in s.value for s in at.success)
    assert not find(at.button, "🔒 Niêm phong").disabled

    # Hộ chiếu số + dữ liệu đã che
    assert any("CHỨNG NHẬN DANH TÍNH SỐ" in m.value and "SOUL-" in m.value for m in at.markdown)
    assert "HungAI" not in str(at.json[0].value)

    # Niêm phong di sản
    find(at.text_input, "Họ tên người thừa kế").input("Hà Minh Khôi")
    find(at.text_input, "Email người thừa kế").input("khoi.ha@gmail.com")
    find(at.text_input, "Mật ước gia đình").input(SECRET)
    find(at.text_input, "Nhập lại mật ước").input(SECRET)
    find(at.text_area, "Danh mục").input("MASTER-KEY-8X-2026\nKho sáng tác")
    find(at.text_area, "Lời nhắn").input("Giữ vững đạo đức nghề nghiệp.")
    at = act(app_file, at, find(at.button, "🔒 Niêm phong"))
    assert len(at.dataframe[0].value) >= 4  # nhật ký kiểm toán
    assert at.slider  # thanh trượt chỉ có ở chế độ demo

    # Khóa két -> cổng người thừa kế (không cần passphrase)
    at = act(app_file, at, find(at.button, "🔒 Khóa két sắt"))
    at = act(app_file, at, find(at.button, "Vào cổng tiếp quản"))
    find(at.slider, "🧪").set_value(800).run()
    at = fresh(app_file, at)
    find(at.radio, "Phương thức").set_value("⬆️ Tải ảnh").run()
    at = fresh(app_file, at)
    find(at.text_input, "Họ tên của bạn").input("Ha Minh Khoi")
    find(at.text_input, "Email").input("khoi.ha@gmail.com")
    find(at.text_input, "Các thành viên").input("Bố Hà Văn A, Vợ Trần Thị C")
    find(at.text_input, "Mật ước gia đình").input(SECRET.lower())
    at = act(app_file, at, find(at.button, "🗝️"))
    assert any("CHỨNG THƯ CHUYỂN GIAO" in m.value and "MASTER-KEY-8X-2026" in m.value for m in at.markdown)


def test_wrong_passphrase_shows_error_not_traceback(app_file, tmp_path):
    at = fresh(app_file)
    find(at.text_input, "Passphrase (").input(PASSPHRASE)
    find(at.text_input, "Nhập lại passphrase").input(PASSPHRASE)
    at = act(app_file, at, find(at.button, "Tạo két sắt"))
    at = act(app_file, at, find(at.button, "🔒 Khóa két sắt"))

    find(at.text_input, "Passphrase của Chủ nhân").input("sai-passphrase")
    find(at.button, "Mở khóa").click().run()
    assert not at.exception
    assert any("Sai passphrase" in e.value for e in at.error)


def test_no_demo_slider_outside_demo_mode(app_file, monkeypatch):
    monkeypatch.setenv("EVOLVING_SOUL_DEMO", "0")
    at = fresh(app_file)
    assert not any("CHẾ ĐỘ DEMO" in m.value for m in at.markdown)
    assert not at.slider
