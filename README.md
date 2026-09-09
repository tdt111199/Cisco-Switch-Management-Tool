# Cisco Layer 2 Switch Manager (GUI)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GitHub Release](https://img.shields.io/github/v/release/tdt111199/Cisco-Switch-Management-Tool?color=blue&label=release)](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/latest)
[![Download Windows EXE](https://img.shields.io/badge/download-Windows%20x64%20EXE-brightgreen.svg)](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Code Style](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)

A complete, modern desktop GUI application built in Python (CustomTkinter) for configuring, managing, backing up, and monitoring **Cisco Layer 2 Switches** (Cisco Catalyst / IOS / IOS-XE). The application supports concurrent multi-device batch automation, local credential encryption, automated safety backups before restore, and standalone Windows `.exe` deployment.

---

## 📥 Download & Quick Start (No Python Required)

Pre-compiled standalone Windows executables are available on the [GitHub Releases](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/latest) page. You can run the application directly on Windows 10 / 11 (64-bit) without installing Python or dependencies:

| Asset | Link | Description |
| :--- | :--- | :--- |
| **Complete ZIP Package** | [📦 CiscoL2Manager-v1.0.0-windows-x64.zip](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/download/v1.0.0/CiscoL2Manager-v1.0.0-windows-x64.zip) | Standalone EXE + sample inventory templates + guide |
| **Standalone Executable** | [🚀 CiscoL2Manager.exe](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/download/v1.0.0/CiscoL2Manager.exe) | Single executable file (~25.0 MB) |
| **All Releases** | [🌐 GitHub Releases Page](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/latest) | Full changelogs, assets, and SHA256 checksums |

### Quick Start:
1. Download `CiscoL2Manager-v1.0.0-windows-x64.zip` from the release link above.
2. Unzip the archive to any folder and double-click `CiscoL2Manager.exe`.
3. In the **Quản Lý Thiết Bị** tab, import your switch inventory from the provided sample templates in `examples/` (Excel, CSV, or JSON) or add switches manually.

---

## 📑 Table of Contents

- [Download & Quick Start](#-download--quick-start-no-python-required)
- [Project Overview](#-project-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage Guide](#-usage-guide)
- [Build and Packaging (Standalone Windows EXE)](#-build-and-packaging-standalone-windows-exe)
- [Security Notes and Best Practices](#-security-notes-and-best-practices)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔭 Project Overview

Managing network infrastructure often involves repetitive manual CLI configuration across multiple switches, error-prone manual backups, and security risks when storing plain text passwords.

**Cisco Layer 2 Switch Manager** provides network engineers and administrators with:
1. An intuitive, modern graphical interface (Dark/Light mode) for all routine Layer 2 configuration tasks.
2. A safe, structured workflow with **CLI Command Preview** before pushing commands to switches.
3. High-performance concurrent execution across multiple switches using worker threads.
4. Robust backup and safe restoration with **mandatory automatic pre-restore safety snapshots**.
5. Local hardware-bound cryptographic protection for device credentials.

---

## ✨ Key Features

### 1. SSH Connection & Session Management
- Fast, reliable SSH sessions powered by **Netmiko** (`cisco_ios`, `cisco_xe`).
- Enable mode support with separate privileged exec secret handling.
- Built-in connection testing and timeout protection.

### 2. Switch Inventory & Credential Protection
- Comprehensive switch profile management: Hostname, IP address, Port, Group/Location, Device type, Username, Password, Enable Secret, and Notes.
- **Encrypted Credential Storage**: Passwords and secrets are encrypted with symmetric **Fernet (AES-128-CBC + HMAC)** derived via **PBKDF2-HMAC-SHA256** tied to machine hardware identifiers.
- Import/Export inventory from and to **Excel (`.xlsx`)**, **CSV** (auto-detected encoding and delimiters), and **JSON**.

### 3. Full Layer 2 Feature Configuration
Each configuration module includes a **CLI Preview** modal to review exact Cisco IOS commands prior to execution:
- **VLAN Management**: Create VLANs (ID range 1–4094, name) and remove VLANs.
- **Port Modes (Access & Trunk)**:
  - *Access Mode*: Assign access VLAN and optional VoIP Voice VLAN.
  - *Trunk Mode*: 802.1Q encapsulation, allowed VLAN filtering (`all`, lists, `add`, `remove`), and native VLAN configuration.
- **Spanning Tree Protocol (STP), PortFast & BPDU Guard**:
  - Global STP mode (`rapid-pvst`, `pvst`, `mst`).
  - Per-VLAN STP priority (increments of 4096) or quick Root Primary / Secondary assignment.
  - Global or interface-level PortFast and BPDU Guard configuration.
- **EtherChannel (Link Aggregation)**:
  - Member interface range assignment, Channel-Group ID (1–64).
  - Protocols & modes: LACP (`active`, `passive`), PAgP (`desirable`, `auto`), or Static (`on`).
- **Port Security**:
  - Enable/disable port security on access ports.
  - Maximum MAC address limits (`1–1024`).
  - Violation actions: `shutdown`, `restrict`, or `protect`.
  - Dynamic sticky MAC learning (`mac-address sticky`).
- **DHCP Snooping & Dynamic ARP Inspection (DAI)**:
  - Global and per-VLAN DHCP Snooping, Option 82 toggle.
  - Uplink trusted interface designation (`ip dhcp snooping trust`).
  - Per-VLAN Dynamic ARP Inspection (DAI) and DAI trust.
- **Storm Control & Port Settings**:
  - Broadcast and Multicast traffic suppression thresholds (0.0% – 100.0%).
  - Actions on threshold exceed: `trap` or `shutdown`.
  - Port description, speed, duplex, and administrative shutdown/no shutdown.
- **MAC Address Table Management**:
  - Configure static MAC address bindings.
  - Clear dynamic MAC entries globally or filtered by VLAN.

### 4. Backup & Safe Restore
- **Backup**:
  - Selectable scope: **Running-config**, **Startup-config**, or **Both**.
  - Execute on a single switch or **concurrently across multiple switches**.
  - Structured, timestamped archive directory: `backups/<Hostname>_<IP>/<Type>_<Timestamp>.cfg`.
  - Built-in viewer and direct Windows Explorer folder opening.
- **Restore**:
  - Restore configuration from `.cfg` or `.txt` backup files into Running-config or Startup-config.
  - **Mandatory Pre-Restore Safety Snapshot**: Automatically backs up the switch's current Running-config *before* applying any changes to ensure seamless rollback.

### 5. Multi-Device Automation & Live Monitoring
- Multi-threaded worker pool (`concurrent.futures.ThreadPoolExecutor`) ensuring the UI never freezes during long network calls.
- **Real-Time Batch Progress Monitor**: Per-device status badges (Pending, Connecting, Running, Success, Failed) with elapsed runtime and error diagnostics.
- **Live Event Log**: Color-coded, streaming execution log with log export capability.
- **Quick CLI & Show Monitor**: Integrated dropdown for standard operational checks (`show vlan brief`, `show interfaces status`, `show mac address-table`, `show spanning-tree`, `show etherchannel summary`, etc.) plus custom command execution.

---

## 🏗 Architecture

The project follows a clean, modular architecture separating UI presentation, core networking/security infrastructure, and configuration business logic:

```
├── main.py                     # Application entry point
├── build_exe.py                # Standalone PyInstaller build script
├── requirements.txt            # Project dependencies
├── core/                       # Core system services
│   ├── crypto.py               # Hardware-tied PBKDF2/Fernet encryption for credentials
│   ├── inventory.py            # Device inventory management, validation, import/export
│   ├── ssh_client.py           # Netmiko SSH wrapper with timeout and error handling
│   ├── task_runner.py          # Concurrent ThreadPoolExecutor for batch tasks
│   └── logger.py               # Thread-safe logging engine with real-time GUI listeners
├── services/                   # Business and Cisco IOS services
│   ├── l2_config_builder.py    # Cisco IOS CLI command builder with parameter validation
│   ├── backup_service.py       # Running and Startup config backup workflows
│   ├── restore_service.py      # Restore workflow with mandatory pre-restore safety snapshot
│   └── show_service.py         # Inspection and show command definitions
├── gui/                        # CustomTkinter Graphical User Interface
│   ├── app.py                  # Main window frame, sidebar navigation, view router
│   ├── dialogs/                # Modal dialogs (Device add/edit, Confirmation modals)
│   │   ├── device_dialog.py
│   │   └── confirm_dialog.py
│   └── views/                  # Primary functional views
│       ├── devices_view.py     # Switch inventory table, CRUD, search, test SSH, import/export
│       ├── l2_config_view.py   # Layer 2 feature tabs with CLI preview
│       ├── backup_restore_view.py # Backup & restore control center and file archive
│       ├── cli_monitor_view.py # CLI show commands and custom interactive console
│       └── logs_view.py        # Real-time streaming logs and batch status monitor
├── examples/                   # Sanitized example inventory templates
│   ├── devices.example.json
│   ├── devices.example.csv
│   └── devices.example.xlsx
└── tests/                      # Automated unit test suite
    └── test_core_and_services.py
```

---

## 📋 Requirements

- **Operating System**: Windows 10 / 11 (64-bit)
- **Python**: 3.10, 3.11, 3.12, 3.13, or 3.14
- **Network Access**: IP reachability and SSH (port 22 or custom port) enabled on target Cisco switches.

### Dependencies
- `customtkinter` (Modern UI toolkit based on Tkinter)
- `netmiko` (Multi-vendor network automation SSH library)
- `cryptography` (Cryptographic recipes and primitives)
- `openpyxl` (Native Excel `.xlsx` workbook parser and generator)
- `pyinstaller` (Windows executable compiler)

---

## 💻 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/tdt111199/Cisco-Switch-Management-Tool.git
cd Cisco-Switch-Management-Tool
```

### 2. Set Up a Virtual Environment (Recommended)
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Windows Command Prompt:
.venv\Scripts\activate.bat
```

### 3. Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration

### Inventory Setup
You can populate your switch inventory directly through the GUI or by importing an inventory file:
- **Import Templates**: Sample files are provided in the [`examples/`](examples/) directory:
  - `examples/devices.example.json`
  - `examples/devices.example.csv`
  - `examples/devices.example.xlsx`
- **Supported File Formats**:
  - Excel (`.xlsx`, `.xls`)
  - CSV (comma, semicolon, or tab-delimited with UTF-8 or Windows-1252/1258 encodings)
  - JSON

### Expected Column Headers
The application supports both English and Vietnamese header naming:
| Field | English Headers | Vietnamese Headers |
| :--- | :--- | :--- |
| **Hostname** | `name`, `hostname`, `device`, `switch` | `Tên Switch`, `Tên`, `Thiết bị` |
| **IP Address** | `ip`, `ip address`, `host`, `address` | `Địa chỉ IP`, `Địa chỉ` |
| **SSH Port** | `port`, `ssh port` | `Cổng`, `Cổng SSH` |
| **Device Type** | `device_type`, `type` | `Loại thiết bị`, `Loại` |
| **Group** | `group`, `location` | `Nhóm`, `Phòng ban`, `Khu vực` |
| **Username** | `username`, `user` | `Tài khoản` |
| **Password** | `password`, `pass`, `pwd` | `Mật khẩu` |
| **Enable Secret** | `secret`, `enable secret`, `enable_secret` | `Enable Secret`, `Mật khẩu enable` |
| **Notes** | `notes`, `note`, `description` | `Ghi chú`, `Mô tả` |

---

## 🚀 Usage Guide

### Running the Application from Source
```bash
python main.py
```

### Workflow Steps
1. **Device Management (`Quản Lý Thiết Bị`)**:
   - Add new switches or click **📥 Nhập DS** to load an Excel/CSV list.
   - Click **⚡ Test SSH** to verify reachability and credentials.
   - Select one, multiple, or all switches using checkboxes.
2. **Layer 2 Configuration (`Cấu Hình Layer 2`)**:
   - Navigate to the desired module (VLAN, Access/Trunk, STP, EtherChannel, Port Security, DHCP Snooping, Storm Control, or MAC Table).
   - Enter your target parameters.
   - Click **👁 Xem Trước Lệnh CLI** to verify generated commands.
   - Click **🚀 Áp Dụng Lệnh Cấu Hình** to dispatch commands concurrently.
3. **Backup & Restore (`Sao Lưu & Restore`)**:
   - **Backup**: Choose Running, Startup, or Both, then click **🚀 Bắt Đầu Sao Lưu**.
   - **Restore**: Select a target switch and a configuration file. The app automatically creates a pre-restore backup before applying the new configuration.
4. **Monitoring & Logs (`Nhật Ký & Tiến Độ`)**:
   - View per-switch status updates, execution duration, and full CLI output logs in real time.

### Running Unit Tests
Execute the automated test suite with:
```bash
python -m unittest discover tests
```

---

## 📦 Build and Packaging (Standalone Windows EXE)

### Pre-Built Binary
For convenience, pre-built standalone binaries are published under [GitHub Releases](https://github.com/tdt111199/Cisco-Switch-Management-Tool/releases/latest) and tracked via the [`release/`](release/) directory in this repository.

### Compiling from Source
You can also compile the application into your own standalone `.exe` using PyInstaller:

```bash
python build_exe.py
```

- The build script uses PyInstaller with `--onefile`, `--noconsole`, and bundles all required assets from `customtkinter`, `netmiko`, `cryptography`, and `openpyxl`.
- The compiled executable will be output to:
  ```
  dist/CiscoL2Manager.exe
  ```

---

## 🔒 Security Notes and Best Practices

1. **Credential Storage**:
   - Device passwords and enable secrets are never stored in plain text.
   - When saved locally in `data/devices.json`, secrets are encrypted using Fernet (AES-128-CBC + HMAC) with keys derived from the host system's hardware identifier via PBKDF2-HMAC-SHA256.
2. **Repository Hygiene**:
   - The `.gitignore` file strictly excludes runtime databases (`data/`), configuration files, credentials, network backups (`backups/`, `*.cfg`), and runtime logs (`*.log`).
   - Never commit production switch configurations or real credentials to public or private version control.
3. **Transport Security**:
   - All network management is performed over encrypted SSH (v2) sessions. Insecure Telnet is intentionally omitted.
4. **Safety Rollback Protocol**:
   - Configuration restores always trigger an automatic retrieval and storage of the current running configuration before writing new commands.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/amazing-feature`.
3. Commit your changes: `git commit -m "Add amazing feature"`.
4. Push to the branch: `git push origin feature/amazing-feature`.
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
