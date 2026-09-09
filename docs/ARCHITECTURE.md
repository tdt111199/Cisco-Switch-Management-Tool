# Architecture & Design Specifications

## 🏛️ System Overview

**Cisco Historical Unused Port Scanner** is engineered as a zero-database, modular desktop application for enterprise network auditing. It leverages Netmiko for SSH communication, openpyxl for multi-sheet Excel persistent storage, and CustomTkinter for a hardware-accelerated desktop UI.

```
+-------------------------------------------------------------------------------+
|                       Presentation Layer (CustomTkinter)                      |
|  - HistoricalScannerView (Dashboard, Table, Filters, Action Bar)              |
|  - HistoricalTrendChart (Canvas Multi-Series Trend Visualizer)                |
|  - Dialogs (HistoricalPortDetailDialog, ConfigPreviewDialog, DeviceDialog)    |
+---------------------------------------+---------------------------------------+
                                        |
+---------------------------------------v---------------------------------------+
|                    Coordination & Business Logic Layer                        |
|  - HistoricalScannerService (ThreadPoolExecutor Multi-Switch Batch Engine)     |
|  - HistoricalAnalyzer (Multi-Scan Intelligence, Inactivity & Reset Rules)     |
|  - RiskProtectionEngine (Safety Matrix & Strict Exclusion Classifier)         |
|  - ConfigGenerator (Safe Shutdown & Rollback CLI Generation)                  |
|  - ReportGenerator (Executive Excel Dashboards & CSV Exporter)                |
+-------------------+-----------------------------------+-----------------------+
                    |                                   |
+-------------------v-------------------+       +-------v-----------------------+
|        Network & Collection Layer     |       |       Persistence Layer       |
|  - CiscoSSHClient (Netmiko Session)   |       |  - ExcelStorageManager        |
|  - CiscoDataCollector (CLI Parser)    |       |    * Port_History             |
|    * show interfaces status           |       |    * Port_Summary             |
|    * show interfaces switchport       |       |    * Protected_Ports          |
|    * show etherchannel summary        |       |    * Scan_Log                 |
|    * show mac address-table           |       |    * Auto-Backup Engine       |
|    * show cdp/lldp neighbors          |       |    * Atomic File Swapper      |
|    * show interfaces (timers/counters)|       +-------------------------------+
+---------------------------------------+
```

---

## 🧩 Component Breakdown

### 1. Presentation Layer (`src/gui/`)
- **`HistoricalScannerView`**: The central operational view providing:
  - Real-time KPI summary badges.
  - Multi-criteria filter engine (instant regex search across switch, interface, description, MACs, classification).
  - Checkbox selection model with context menus.
  - Per-switch unused rate indicator.
- **`HistoricalTrendChart`**: Pure Tkinter Canvas component plotting historical time-series lines (`UNUSED`, `ACTIVE`, `MONITOR`) without heavy external plotting dependencies.
- **`ConfigPreviewDialog`**: Read-only CLI script viewer preventing accidental direct execution while enabling quick clipboard copying and `.cfg` file export.

### 2. Service & Analytics Layer (`src/services/scanner/`)
- **`HistoricalScannerService`**: Uses Python's `concurrent.futures.ThreadPoolExecutor` to query multiple devices concurrently while keeping the UI responsive via event callbacks.
- **`HistoricalAnalyzer`**: Implements state-machine logic comparing the current snapshot against all prior historical scans to compute cumulative inactive duration and reset consecutive counters upon device reconnection.
- **`RiskProtectionEngine`**: Enforces strict safety rules ensuring no uplink, trunk, etherchannel, or protected port is ever marked `UNUSED`.

### 3. Network Collection Layer (`src/core/` and `src/services/scanner/`)
- **`CiscoDataCollector`**:
  - Connects to Cisco IOS/IOS-XE devices.
  - Executes standardized operational commands.
  - Normalizes Cisco interface identifiers (`Gi0/1`, `Gig 0/1`, `GigabitEthernet0/1`).
  - Converts human-readable uptime/hang strings (`never`, `14w2d`, `3d05h`, `00:15:30`) into exact floating-point days.

### 4. Excel Persistent Storage Layer (`src/services/scanner/excel_storage.py`)
- Zero-database dependency: relies purely on `data/port_history.xlsx`.
- **Pre-write Backup**: Every write operation triggers an automatic timestamped snapshot to `backups/excel_history/port_history_backup_YYYYMMDD_HHMMSS.xlsx`.
- **Atomic Replacement**: Writes to a temporary `.tmp` file and performs an atomic filesystem replace to eliminate corruption risks during unexpected terminations.
