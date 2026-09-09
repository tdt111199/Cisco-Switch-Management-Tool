"""Historical Analyzer for Cisco Historical Unused Port Scanner.

Calculates multi-scan historical metrics:
- First Seen
- Last Seen
- Days Unused
- Consecutive Unused Scans
- Last Active Time
- Active Transitions (increments when port goes from inactive to active)
- Reset logic: resets Consecutive Unused Scans to 0 when port becomes active.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from core.logger import logger
from core.scanner_models import (
    PortClassification,
    PortSnapshot,
    PortSummaryRecord,
    ScanSettings,
)


class HistoricalAnalyzer:
    """Computes historical intelligence across multiple scan snapshots."""

    def __init__(self, settings: Optional[ScanSettings] = None):
        self.settings = settings or ScanSettings()

    def analyze(
        self,
        current_snapshots: List[PortSnapshot],
        previous_summaries: List[PortSummaryRecord],
        protected_ports_set: Set[Tuple[str, str]],
    ) -> List[PortSummaryRecord]:
        """Merges current snapshots with previous historical summaries and returns updated summaries."""
        # Index previous summaries by (switch_name, interface)
        prev_map: Dict[Tuple[str, str], PortSummaryRecord] = {}
        for rec in previous_summaries:
            prev_map[(rec.switch_name, rec.interface)] = rec

        updated_records: List[PortSummaryRecord] = []
        now_dt = datetime.now()
        now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

        for snap in current_snapshots:
            key = (snap.switch_name, snap.interface)
            prev = prev_map.get(key)

            # Determine if this port is currently active in this snapshot
            is_currently_active = self._is_snapshot_active(snap)

            # 1. First Seen
            if prev and prev.first_seen:
                first_seen = prev.first_seen
            else:
                first_seen = snap.scan_time or now_str

            # 2. Last Seen
            last_seen = snap.scan_time or now_str

            # 3. Active Transitions & Consecutive Scans & Last Active Time
            if is_currently_active:
                # Port is active now -> RESET consecutive unused scans
                consecutive_unused_scans = 0
                last_active_time = last_seen
                days_unused = 0

                # Check if this is a transition from inactive -> active
                active_transitions = prev.active_transitions if prev else 0
                if prev and prev.current_status not in ("connected", "up"):
                    active_transitions += 1
                elif not prev:
                    active_transitions = 1
            else:
                # Port is inactive now
                prev_consec = prev.consecutive_unused_scans if prev else 0
                consecutive_unused_scans = prev_consec + 1
                active_transitions = prev.active_transitions if prev else 0

                # Last active time
                if prev and prev.last_active_time:
                    last_active_time = prev.last_active_time
                else:
                    last_active_time = ""

                # Days unused calculation
                days_unused = self._calculate_days_unused(
                    snap=snap,
                    prev=prev,
                    now_dt=now_dt,
                    first_seen=first_seen,
                    last_active_time=last_active_time
                )

            # Build initial summary record
            speed_duplex = f"{snap.speed}/{snap.duplex}".strip("/")
            rec = PortSummaryRecord(
                switch_name=snap.switch_name,
                switch_ip=snap.switch_ip,
                interface=snap.interface,
                current_status=snap.status,
                current_vlan=snap.vlan,
                description=snap.description,
                current_macs=snap.mac_addresses,
                speed_duplex=speed_duplex,
                classification=PortClassification.MONITOR,  # Assigned next by RiskProtectionEngine
                days_unused=days_unused,
                consecutive_unused_scans=consecutive_unused_scans,
                first_seen=first_seen,
                last_seen=last_seen,
                last_active_time=last_active_time,
                active_transitions=active_transitions,
                is_protected=False,
                is_trunk=snap.is_trunk,
                is_portchannel=snap.is_portchannel,
                has_neighbor=snap.has_cdp_neighbor or snap.has_lldp_neighbor,
                neighbor_info=snap.neighbor_info,
                last_input_str=snap.last_input_str,
                last_output_str=snap.last_output_str,
            )
            updated_records.append(rec)

        # Include ports from previous summary that were not scanned in this run (e.g. from other switches)
        current_keys = {(s.switch_name, s.interface) for s in current_snapshots}
        for (sw, iface), prev_rec in prev_map.items():
            if (sw, iface) not in current_keys:
                updated_records.append(prev_rec)

        return updated_records

    def _is_snapshot_active(self, snap: PortSnapshot) -> bool:
        """Determines if a port is actively transmitting/connected in this snapshot."""
        st = snap.status.lower()
        if st in ("connected", "up"):
            return True
        if snap.mac_addresses and len(snap.mac_addresses) > 0:
            return True
        # If last activity days is 0 or less than 1 day
        if 0 <= snap.last_activity_days < 1.0:
            return True
        return False

    def _calculate_days_unused(
        self,
        snap: PortSnapshot,
        prev: Optional[PortSummaryRecord],
        now_dt: datetime,
        first_seen: str,
        last_active_time: str
    ) -> int:
        """Calculates days of continuous inactivity combining switch hardware timers and scan history."""
        candidates = []

        # 1. Hardware duration from switch (e.g. 'Last input 14w2d' -> 100 days)
        if snap.last_activity_days > 0:
            if snap.last_activity_days >= 9999.0:
                # "never" -> at least time since first seen or 999
                candidates.append(999)
            else:
                candidates.append(int(snap.last_activity_days))

        # 2. History duration: elapsed days since last_active_time
        if last_active_time:
            try:
                dt_last_act = datetime.strptime(last_active_time, "%Y-%m-%d %H:%M:%S")
                diff_days = (now_dt - dt_last_act).days
                if diff_days >= 0:
                    candidates.append(diff_days)
            except Exception:
                pass

        # 3. History duration: elapsed days since first_seen (if never active)
        if not last_active_time and first_seen:
            try:
                dt_first = datetime.strptime(first_seen, "%Y-%m-%d %H:%M:%S")
                diff_days = (now_dt - dt_first).days
                if diff_days >= 0:
                    candidates.append(diff_days)
            except Exception:
                pass

        # 4. Previous days_unused + increment
        if prev and prev.days_unused > 0:
            candidates.append(prev.days_unused)

        if candidates:
            return max(candidates)

        return 0
