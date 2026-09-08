"""Build script to bundle Cisco Layer 2 Switch Manager into a standalone Windows .exe using PyInstaller."""

import os
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def build():
    print("=" * 70)
    print("STARTING PYINSTALLER BUILD - STANDALONE WINDOWS EXE")
    print("=" * 70)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=CiscoL2Manager",
        "--onefile",
        "--noconsole",
        "--clean",
        "--collect-all=customtkinter",
        "--collect-all=netmiko",
        "--collect-all=cryptography",
        "--collect-all=openpyxl",
        "--hidden-import=tkinter",
        "--hidden-import=PIL",
        "main.py",
    ]

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = os.path.abspath(os.path.join("dist", "CiscoL2Manager.exe"))
        print("=" * 70)
        print("BUILD SUCCESSFUL!")
        print(f"Standalone executable created at:\n{exe_path}")
        print("=" * 70)
        return True
    else:
        print("=" * 70)
        print(f"Build failed with exit code: {result.returncode}")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
