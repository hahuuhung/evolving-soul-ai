"""
Công Cụ Tự Động Hóa Đóng Gói & Xuất Bản Lên GitHub
Dự án: Evolving Soul AI
Tác giả sáng lập: HÀ HỮU HƯNG (1985) — KỸ SƯ AI THẾ HỆ 8X
"""

import sys
import subprocess


def push_to_github(repo_url: str):
    """Thực thi chuỗi lệnh git an toàn để đẩy mã nguồn mở lên GitHub."""
    commands = [
        ["git", "add", "."],
        ["git", "commit", "-m", "Release v1.0.0: Evolving Soul AI - Tac gia HA HUU HUNG (1985) Ky su AI the he 8X"],
        ["git", "branch", "-M", "main"],
        ["git", "remote", "remove", "origin"],
        ["git", "remote", "add", "origin", repo_url],
        ["git", "push", "-u", "origin", "main"]
    ]

    print("🚀 Đang tiến hành đóng gói và đẩy dự án lên GitHub...")
    for cmd in commands:
        try:
            res = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.stdout:
                print(res.stdout.strip())
        except subprocess.CalledProcessError as e:
            if "remote remove" in " ".join(cmd) or "nothing to commit" in e.stderr:
                continue
            print(f"⚠️ Thông báo ở lệnh {' '.join(cmd)}: {e.stderr.strip()}")

    print(f"\n🎉 HOÀN TẤT! Dự án của tác giả HÀ HỮU HƯNG (1985) đã sẵn sàng tại:\n👉 {repo_url}")


if __name__ == "__main__":
    print("=== CÔNG CỤ TỰ ĐỘNG XUẤT BẢN MÃ NGUỒN MỞ LÊN GITHUB ===")
    if len(sys.argv) > 1:
        repo_link = sys.argv[1].strip()
    else:
        repo_link = input("Nhập đường dẫn GitHub Repository (VD: https://github.com/username/evolving-soul-ai.git): ").strip()

    if not repo_link.startswith("http") and not repo_link.startswith("git@"):
        print("❌ Đường dẫn không hợp lệ! Vui lòng cung cấp link GitHub hợp lệ.")
    else:
        push_to_github(repo_link)
