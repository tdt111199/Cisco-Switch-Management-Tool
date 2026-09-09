# Changelog

All notable changes to **Cisco Historical Unused Port Scanner** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-09

### Added
- **Persistent Multi-Sheet Excel Storage**:
  - Implemented zero-database persistent storage via `data/port_history.xlsx`.
  - Added 4 persistent sheets: `Port_History`, `Port_Summary`, `Protected_Ports`, and `Scan_Log`.
  - Added pre-write automatic backup to `backups/excel_history/port_history_backup_<timestamp>.xlsx`.
  - Implemented atomic file swap to guard against file corruption during sudden terminations.
- **Multi-Scan Historical Intelligence**:
  - Tracking of `First Seen`, `Last Seen`, `Days Unused`, `Consecutive Unused Scans`, `Last Active Time`, and `Active Transitions`.
  - Implemented strict **Reset Rule**: whenever an inactive port becomes active, `Consecutive Unused Scans` is reset to 0, `Last Active Time` is updated, and `Active Transitions` is incremented.
- **Safe Multi-Criteria Classification & Risk Engine**:
  - Classifications: `ACTIVE`, `UNUSED`, `MONITOR`, `PROTECTED`, `TRUNK/UPLINK`, `PORT-CHANNEL`, and `ERROR`.
  - Strict exclusion of Trunk ports, Uplink ports, Port-Channels/EtherChannels, CDP/LLDP neighbors, and user-protected ports.
- **Cisco IOS/IOS-XE Telemetry Collector**:
  - Comprehensive parsing for `show interfaces status`, `show interfaces description`, `show interfaces switchport`, `show etherchannel summary`, `show mac address-table`, `show cdp neighbors`, `show lldp neighbors`, and `show interfaces`.
  - High-precision Cisco duration parsing (`never`, `14w2d`, `3d05h`, `00:15:30`) into exact inactive days.
- **Executive Reporting & Safe Config Generation**:
  - Multi-sheet Excel dashboard export (`Dashboard Tổng Hợp`, `Tất Cả Cổng`, `Cổng UNUSED Đủ Điều Kiện`) with styled KPI cards and color highlights.
  - UTF-8 with BOM CSV export.
  - Safe Cisco IOS shutdown script generator with audit descriptions.
  - Rollback script generator (`no shutdown`).
  - Strict read-only device interaction (zero automated changes pushed to switches).
- **Modern Desktop GUI**:
  - Hardware-accelerated CustomTkinter interface with Dark/Light theme toggle.
  - Real-time KPI summary banner and per-switch unused rate breakdown.
  - Embedded Tkinter Canvas Historical Trend Chart for multi-series visualization over time.
  - Instant multi-criteria filter and search bar.
  - Detailed historical snapshot modal dialog for inspecting individual port history.
- **Packaging**:
  - Standalone Windows `.exe` bundle via PyInstaller without Python installation requirements.
  - One-click build and package script `build.bat`.
