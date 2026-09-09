# Cisco Historical Unused Port Scanner — User Guide

## 🖥️ Getting Started

### 1. Launching the Application
- **Executable (Windows Standalone)**:
  Double-click `CiscoHistoricalUnusedPortScanner.exe` in the `release/` or `dist/` directory.
- **Source Code (Python)**:
  ```powershell
  python historical_scanner_main.py
  ```

---

## 📋 Step-by-Step Workflow

### Step 1: Manage Switch Inventory
- You can add switch profiles manually or import from Excel/CSV using the **"📥 Import Switch"** button.
- Excel format accepts headers in Vietnamese or English (`Tên Switch`, `Địa chỉ IP`, `Cổng SSH`, `Username`, `Password`, `Enable Secret`).

### Step 2: Configure Inactivity Threshold
- In the top bar dropdown, select your organization's policy:
  - `30 ngày`
  - `60 ngày (Khuyên dùng)`
  - `90 ngày`
  - `180 ngày`
  - `Tùy chỉnh...` (Enter any custom days value)

### Step 3: Execute Historical Batch Scan
- Click **"🚀 Scan All (Quét Tất Cả)"**.
- The worker pool connects concurrently via Netmiko.
- Telemetry snapshots are appended to `data/port_history.xlsx`.
- Previous history is evaluated, and the `Port_Summary` view is automatically refreshed.

### Step 4: Review Port Analytics & Historical Trend
- Click **"📈 Hiện Biểu Đồ Xu Hướng"** to view the time-series trajectory of Unused vs Active ports.
- Filter by Switch, Classification (`UNUSED`, `ACTIVE`, `MONITOR`, etc.), VLAN, or search keyword.
- **Double-click** any port row to view its full snapshot history across every past scan run.

### Step 5: Protect Critical Ports
- Tick ports in the table and click **"🛡️ Bảo Vệ Cổng Chọn"** to permanently protect them.
- Protected ports will be stored in the `Protected_Ports` sheet and never marked as UNUSED.

### Step 6: Generate Configuration & Export Reports
- Click **"⚠️ Tạo Config Shutdown"** to review the proposed shutdown CLI commands.
- Click **"🔄 Tạo Config Rollback"** for the restoration script.
- Click **"📊 Xuất Excel"** to export a multi-sheet executive report with KPI dashboards.
