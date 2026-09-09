"""Data models for Cisco Historical Unused Port Scanner."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set


class PortClassification(str, Enum):
    """Classification of switch port state."""
    ACTIVE = "ACTIVE"
    UNUSED = "UNUSED"
    MONITOR = "MONITOR"
    PROTECTED = "PROTECTED"
    TRUNK_UPLINK = "TRUNK/UPLINK"
    PORT_CHANNEL = "PORT-CHANNEL"
    ERROR = "ERROR"


@dataclass
class ScanSettings:
    """Settings for port scanning and historical classification."""
    threshold_days: int = 60
    check_mac: bool = True
    check_cdp_lldp: bool = True
    check_traffic: bool = True
    check_switchport: bool = True
    protected_keywords: List[str] = field(default_factory=lambda: [
        "uplink", "trunk", "core", "wan", "router", "firewall",
        "fw", "server", "ap", "access-point", "wifi", "camera", "cctv",
        "printer", "transit", "dist", "distribution", "mgmt", "management"
    ])
    auto_backup_storage: bool = True
    storage_file: str = "data/port_history.xlsx"


@dataclass
class PortSnapshot:
    """Snapshot of a single port taken during a single scan run."""
    scan_time: str                  # ISO format: YYYY-MM-DD HH:MM:SS
    switch_name: str
    switch_ip: str
    interface: str                 # e.g., GigabitEthernet0/1 or Gi0/1
    status: str                    # connected, notconnect, disabled, err-disabled
    admin_status: str              # up, administratively down
    vlan: str                      # e.g., 10, trunk, routed
    description: str = ""
    mac_addresses: List[str] = field(default_factory=list)
    in_packets: int = 0
    out_packets: int = 0
    in_octets: int = 0
    out_octets: int = 0
    last_input_str: str = ""       # e.g. "never", "12w3d", "00:02:15"
    last_output_str: str = ""
    last_activity_days: float = -1.0  # Computed days from last input/output or link flapped
    is_trunk: bool = False
    switchport_mode: str = "access"  # access, trunk, dynamic
    is_portchannel: bool = False
    port_channel_id: str = ""      # e.g., Po1, or member of Po1
    has_cdp_neighbor: bool = False
    has_lldp_neighbor: bool = False
    neighbor_info: str = ""        # Summary of neighbor: Device ID, Platform, Remote Port
    speed: str = ""
    duplex: str = ""
    raw_info: str = ""             # Additional raw snippet for troubleshooting


@dataclass
class PortSummaryRecord:
    """Aggregated historical intelligence for a unique switch port."""
    switch_name: str
    switch_ip: str
    interface: str
    current_status: str            # latest status (connected, notconnect, etc.)
    current_vlan: str
    description: str
    current_macs: List[str] = field(default_factory=list)
    speed_duplex: str = ""
    
    # Historical Intelligence Metrics
    classification: PortClassification = PortClassification.MONITOR
    days_unused: int = 0
    consecutive_unused_scans: int = 0
    first_seen: str = ""           # Timestamp of first scan recording this port
    last_seen: str = ""            # Timestamp of latest scan
    last_active_time: str = ""     # Timestamp when port was last seen ACTIVE
    active_transitions: int = 0    # Number of times port transitioned from inactive -> active
    
    # Protection and flags
    is_protected: bool = False
    is_trunk: bool = False
    is_portchannel: bool = False
    has_neighbor: bool = False
    neighbor_info: str = ""
    protection_reason: str = ""
    classification_reason: str = ""
    last_input_str: str = ""
    last_output_str: str = ""


@dataclass
class ProtectedPortRecord:
    """Record of a port marked as protected."""
    switch_name: str
    interface: str
    reason: str = "User Protected"
    added_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    added_by: str = "Administrator"


@dataclass
class ScanLogRecord:
    """Record of an execution scan run."""
    scan_id: str
    timestamp: str
    switches_scanned: int
    total_ports: int
    active_count: int
    unused_count: int
    monitor_count: int
    protected_count: int
    trunk_count: int
    error_count: int
    duration_seconds: float
    status: str                    # SUCCESS, PARTIAL, FAILED
    notes: str = ""


@dataclass
class SwitchScanResult:
    """Result of scanning a single switch."""
    switch_name: str
    switch_ip: str
    success: bool
    snapshots: List[PortSnapshot] = field(default_factory=list)
    error_message: str = ""
    duration_seconds: float = 0.0
