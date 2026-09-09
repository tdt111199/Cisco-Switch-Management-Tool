# Cisco Layer 2 Switch Manager - Release Binaries

Pre-compiled standalone Windows executables are distributed directly via **GitHub Releases** to maintain optimal repository performance and avoid Git history bloat from large binary files.

## 📥 Download Pre-Compiled Application

You can download the latest official release directly from GitHub:

* 📦 **Complete Release Package (.zip)**: [CiscoL2Manager-v1.0.0-windows-x64.zip](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/download/v1.0.0/CiscoL2Manager-v1.0.0-windows-x64.zip) *(Includes executable, examples, and user guide)*
* 🚀 **Standalone Executable (.exe)**: [CiscoL2Manager.exe](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/download/v1.0.0/CiscoL2Manager.exe)
* 🌐 **All Releases**: [GitHub Releases Page](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/latest)

---

## 🔒 Verification & Checksums

| Asset File | Size | SHA-256 Checksum |
| :--- | :--- | :--- |
| `CiscoL2Manager.exe` | ~25.0 MB (25,037,245 bytes) | `C8929EE20050EA542F54D05693D7CA224DEA7303E55ADADC198F44B2A7267854` |
| `CiscoL2Manager-v1.0.0-windows-x64.zip` | ~24.7 MB (24,682,413 bytes) | `108088B42C278F06748F8D92B27A6C11D25F872A610E3E5EF662F9089FE53994` |

---

## 🚀 Running the Executable

1. Download `CiscoL2Manager-v1.0.0-windows-x64.zip` and extract to any folder, or download `CiscoL2Manager.exe`.
2. Double-click `CiscoL2Manager.exe` to start the GUI. No Python environment, Git, or external dependencies are required.
3. Supported operating systems: Windows 10 / Windows 11 (64-bit).

---

## 🛠️ Building from Source

If you prefer to compile your own standalone executable from source code:

```bash
git clone https://github.com/tdt111199/Cisco-Switch-Management-Tool.git
cd Cisco-Switch-Management-Tool
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
python build_exe.py
```
The compiled binary will be placed in `dist/CiscoL2Manager.exe`.
