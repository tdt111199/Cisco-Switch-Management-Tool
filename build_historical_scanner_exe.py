"""Build script to bundle Cisco Historical Unused Port Scanner into a standalone Windows .exe."""

import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def build():
    print("=" * 75)
    print("BẮT ĐẦU ĐÓNG GÓI CISCO HISTORICAL UNUSED PORT SCANNER -> STANDALONE EXE")
    print("=" * 75)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=CiscoHistoricalUnusedPortScanner",
        "--onefile",
        "--noconsole",
        "--clean",
        "--paths=src",
        "--collect-all=customtkinter",
        "--collect-all=netmiko",
        "--collect-all=cryptography",
        "--collect-all=openpyxl",
        "--hidden-import=tkinter",
        "--hidden-import=PIL",
        "historical_scanner_main.py",
    ]

    print(f"Lệnh thực thi: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "CiscoHistoricalUnusedPortScanner.exe"))
        print("=" * 75)
        print("ĐÓNG GÓI THÀNH CÔNG!")
        print(f"Tệp thực thi độc lập Windows .exe sẵn sàng tại:\n{exe_path}")
        print("=" * 75)
        return True
    else:
        print("=" * 75)
        print(f"Đóng gói thất bại với mã lỗi: {result.returncode}")
        print("=" * 75)
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
