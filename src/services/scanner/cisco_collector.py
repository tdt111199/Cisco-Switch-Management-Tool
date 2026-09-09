"""Cisco Switch Data Collector using Netmiko.

Collects comprehensive port information: status, description, switchport mode,
EtherChannel membership, MAC table, CDP/LLDP neighbors, and interface counters/timers.
"""

import re
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set, Tuple

from core.inventory import SwitchDevice
from core.logger import logger
from core.scanner_models import PortSnapshot, ScanSettings, SwitchScanResult
from core.ssh_client import CiscoSSHClient, SSHConnectionError


def normalize_interface_name(name: str) -> str:
    """Normalize Cisco interface name (e.g., Gi0/1, Gig 0/1 -> GigabitEthernet0/1)."""
    if not name:
        return ""
    name = re.sub(r"\s+", "", name.strip())
    replacements = [
        (r"^(?:GigabitEthernet|Gig|Gi)(\d.*)$", r"GigabitEthernet\1"),
        (r"^(?:FastEthernet|Fas|Fa)(\d.*)$", r"FastEthernet\1"),
        (r"^(?:TenGigabitEthernet|TenGigE|Ten|Te)(\d.*)$", r"TenGigabitEthernet\1"),
        (r"^(?:FortyGigabitEthernet|FortyGigE|Fo)(\d.*)$", r"FortyGigabitEthernet\1"),
        (r"^(?:HundredGigabitEthernet|HundredGigE|Hu)(\d.*)$", r"HundredGigE\1"),
        (r"^(?:Ethernet|Eth|Et)(\d.*)$", r"Ethernet\1"),
        (r"^(?:Port-channel|Port-Channel|Po)(\d.*)$", r"Port-channel\1"),
        (r"^(?:Vlan|Vl)(\d.*)$", r"Vlan\1"),
    ]
    for pattern, repl in replacements:
        if re.match(pattern, name, re.IGNORECASE):
            return re.sub(pattern, repl, name, flags=re.IGNORECASE)
    return name


def canonical_short_name(name: str) -> str:
    """Short interface name for compact matching (e.g. Gi0/1)."""
    if not name:
        return ""
    name = re.sub(r"\s+", "", name.strip())
    replacements = [
        (r"^(?:GigabitEthernet|Gig|Gi)(\d.*)$", r"Gi\1"),
        (r"^(?:FastEthernet|Fas|Fa)(\d.*)$", r"Fa\1"),
        (r"^(?:TenGigabitEthernet|TenGigE|Ten|Te)(\d.*)$", r"Te\1"),
        (r"^(?:FortyGigabitEthernet|FortyGigE|Fo)(\d.*)$", r"Fo\1"),
        (r"^(?:HundredGigabitEthernet|HundredGigE|Hu)(\d.*)$", r"Hu\1"),
        (r"^(?:Port-channel|Port-Channel|Po)(\d.*)$", r"Po\1"),
        (r"^(?:Ethernet|Eth|Et)(\d.*)$", r"Eth\1"),
        (r"^(?:Vlan|Vl)(\d.*)$", r"Vl\1"),
    ]
    for pattern, repl in replacements:
        if re.match(pattern, name, re.IGNORECASE):
            return re.sub(pattern, repl, name, flags=re.IGNORECASE)
    return name


def parse_cisco_duration(duration_str: str) -> float:
    """Parse Cisco IOS duration string (e.g., '12w3d', '4d02h', 'never', '00:15:30') into days.

    Returns:
        float: Estimated number of days, or -1.0 if not parsable.
    """
    if not duration_str:
        return -1.0
    text = duration_str.strip().lower()

    if "never" in text:
        return 9999.0

    # Pattern like '1y12w' or '2y'
    years = 0
    match_y = re.search(r"(\d+)\s*y(?:ears?)?", text)
    if match_y:
        years = int(match_y.group(1))

    # Pattern like '12w' or '12w3d'
    weeks = 0
    match_w = re.search(r"(\d+)\s*w(?:eeks?)?", text)
    if match_w:
        weeks = int(match_w.group(1))

    # Pattern like '3d' or '3d05h'
    days = 0
    match_d = re.search(r"(\d+)\s*d(?:ays?)?", text)
    if match_d:
        days = int(match_d.group(1))

    # Pattern like '05h'
    hours = 0
    match_h = re.search(r"(\d+)\s*h(?:ours?)?", text)
    if match_h:
        hours = int(match_h.group(1))

    # Pattern like HH:MM:SS or MM:SS
    match_time = re.search(r"(\d+):(\d+):(\d+)", text)
    if match_time:
        h, m, s = int(match_time.group(1)), int(match_time.group(2)), int(match_time.group(3))
        hours += h + (m / 60.0) + (s / 3600.0)

    total_days = (years * 365.0) + (weeks * 7.0) + days + (hours / 24.0)
    if total_days > 0 or "00:00:00" in text:
        return round(total_days, 2)

    return -1.0


class CiscoDataCollector:
    """Collects port snapshots from a Cisco IOS/IOS-XE switch."""

    def __init__(self, device: SwitchDevice, settings: Optional[ScanSettings] = None):
        self.device = device
        self.settings = settings or ScanSettings()

    def collect(self, log_callback: Optional[Callable[[str], None]] = None) -> SwitchScanResult:
        """Connects to switch, executes diagnostic commands, and builds PortSnapshots."""
        start_time = time.time()
        scan_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def _log(msg: str):
            logger.info(msg, self.device.name)
            if log_callback:
                try:
                    log_callback(f"[{self.device.name}] {msg}")
                except Exception:
                    pass

        _log(f"Bắt đầu thu thập dữ liệu port từ {self.device.name} ({self.device.ip})...")

        try:
            with CiscoSSHClient(self.device, timeout=20) as client:
                _log("Đã kết nối SSH thành công. Đang gửi các lệnh phân tích...")

                # 1. show interfaces status
                raw_status = self._safe_send_command(client, "show interfaces status", _log)

                # 2. show interfaces description
                raw_desc = self._safe_send_command(client, "show interfaces description", _log)

                # 3. show interfaces switchport
                raw_switchport = ""
                if self.settings.check_switchport:
                    raw_switchport = self._safe_send_command(client, "show interfaces switchport", _log)

                # 4. show etherchannel summary
                raw_etherchannel = self._safe_send_command(client, "show etherchannel summary", _log)

                # 5. show mac address-table
                raw_mac = ""
                if self.settings.check_mac:
                    raw_mac = self._safe_send_command(client, "show mac address-table", _log)
                    if "Invalid input" in raw_mac or "% " in raw_mac:
                        raw_mac = self._safe_send_command(client, "show mac-address-table", _log)

                # 6. CDP / LLDP neighbors
                raw_cdp = ""
                raw_lldp = ""
                if self.settings.check_cdp_lldp:
                    raw_cdp = self._safe_send_command(client, "show cdp neighbors", _log)
                    raw_lldp = self._safe_send_command(client, "show lldp neighbors", _log)

                # 7. show interfaces
                raw_interfaces = ""
                if self.settings.check_traffic:
                    raw_interfaces = self._safe_send_command(client, "show interfaces", _log)

                _log("Đã hoàn thành thu thập CLI. Đang tiến hành bóc tách dữ liệu...")
                snapshots = self._parse_all_data(
                    scan_time=scan_time_str,
                    raw_status=raw_status,
                    raw_desc=raw_desc,
                    raw_switchport=raw_switchport,
                    raw_etherchannel=raw_etherchannel,
                    raw_mac=raw_mac,
                    raw_cdp=raw_cdp,
                    raw_lldp=raw_lldp,
                    raw_interfaces=raw_interfaces,
                )

                duration = time.time() - start_time
                _log(f"Thu thập thành công {len(snapshots)} ports trong {duration:.2f}s.")
                return SwitchScanResult(
                    switch_name=self.device.name,
                    switch_ip=self.device.ip,
                    success=True,
                    snapshots=snapshots,
                    duration_seconds=duration,
                )

        except SSHConnectionError as e:
            err_msg = str(e)
            _log(f"Lỗi kết nối SSH: {err_msg}")
            return SwitchScanResult(
                switch_name=self.device.name,
                switch_ip=self.device.ip,
                success=False,
                error_message=err_msg,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            err_msg = f"Lỗi không xác định: {e}"
            _log(err_msg)
            return SwitchScanResult(
                switch_name=self.device.name,
                switch_ip=self.device.ip,
                success=False,
                error_message=err_msg,
                duration_seconds=time.time() - start_time,
            )

    def _safe_send_command(self, client: CiscoSSHClient, cmd: str, log_fn: Callable) -> str:
        """Execute command safely and log any non-critical errors."""
        try:
            return client.send_command(cmd, read_timeout=40)
        except Exception as e:
            log_fn(f"Cảnh báo: Không thể thực thi '{cmd}': {e}")
            return ""

    def _parse_all_data(
        self,
        scan_time: str,
        raw_status: str,
        raw_desc: str,
        raw_switchport: str,
        raw_etherchannel: str,
        raw_mac: str,
        raw_cdp: str,
        raw_lldp: str,
        raw_interfaces: str,
    ) -> List[PortSnapshot]:
        """Combines and parses all CLI output into structured PortSnapshot objects."""

        # 1. Parse Status table
        status_map = self._parse_status_table(raw_status)

        # 2. Parse Description
        desc_map = self._parse_description_table(raw_desc)

        # 3. Parse Switchport mode
        switchport_map = self._parse_switchport_output(raw_switchport)

        # 4. Parse Etherchannel members
        portchannel_map = self._parse_etherchannel_summary(raw_etherchannel)

        # 5. Parse MAC addresses
        mac_map = self._parse_mac_table(raw_mac)

        # 6. Parse CDP / LLDP
        neighbor_map = self._parse_neighbors(raw_cdp, raw_lldp)

        # 7. Parse Show Interfaces counters and timers
        interface_details = self._parse_interfaces_output(raw_interfaces)

        # Merge all interfaces found
        all_interfaces: Set[str] = set()
        all_interfaces.update(status_map.keys())
        all_interfaces.update(interface_details.keys())
        all_interfaces.update(desc_map.keys())

        # Filter out virtual interfaces that are not switch ports (e.g., Null0, Loopback, Vlan interfaces)
        valid_ports = []
        for iface in sorted(list(all_interfaces)):
            norm_name = normalize_interface_name(iface)
            # Skip Vlan, Loopback, Null unless it's a physical or port-channel port
            if norm_name.lower().startswith(("loopback", "null", "vlan")):
                continue
            valid_ports.append(norm_name)

        snapshots: List[PortSnapshot] = []

        for iface in valid_ports:
            short_iface = canonical_short_name(iface)

            # Retrieve from maps trying both normalized and short names
            st = status_map.get(iface) or status_map.get(short_iface) or {}
            desc = desc_map.get(iface) or desc_map.get(short_iface) or st.get("name_desc", "")
            sw_mode = switchport_map.get(iface) or switchport_map.get(short_iface) or {}
            pc_info = portchannel_map.get(iface) or portchannel_map.get(short_iface) or {}
            mac_list = mac_map.get(iface) or mac_map.get(short_iface) or []
            neigh_info = neighbor_map.get(iface) or neighbor_map.get(short_iface) or {}
            if_detail = interface_details.get(iface) or interface_details.get(short_iface) or {}

            # Status resolution
            status_val = st.get("status", if_detail.get("line_status", "unknown")).lower()
            admin_status = if_detail.get("admin_status", "up" if status_val != "disabled" else "administratively down")
            vlan_val = st.get("vlan", sw_mode.get("vlan", "1"))
            duplex_val = st.get("duplex", if_detail.get("duplex", "auto"))
            speed_val = st.get("speed", if_detail.get("speed", "auto"))

            # Trunk detection
            is_trunk = (
                "trunk" in status_val or
                sw_mode.get("is_trunk", False) or
                "trunk" in vlan_val.lower()
            )

            # Port-Channel detection
            is_po = (
                iface.lower().startswith("port-channel") or
                short_iface.lower().startswith("po") or
                pc_info.get("is_member", False)
            )
            po_id = pc_info.get("channel_group", "")
            if not po_id and (iface.lower().startswith("port-channel") or short_iface.lower().startswith("po")):
                po_id = iface

            # CDP / LLDP
            has_cdp = neigh_info.get("has_cdp", False)
            has_lldp = neigh_info.get("has_lldp", False)
            neighbor_str = neigh_info.get("summary", "")

            # Last activity days
            last_in = if_detail.get("last_input", "")
            last_out = if_detail.get("last_output", "")
            last_flap = if_detail.get("last_flap", "")

            # Calculate days from either last input or last output
            days_in = parse_cisco_duration(last_in)
            days_out = parse_cisco_duration(last_out)
            days_flap = parse_cisco_duration(last_flap)

            # Activity days: if never, 9999; if valid, take minimum inactive days
            candidates = [d for d in [days_in, days_out, days_flap] if d >= 0]
            if candidates:
                last_act_days = min(candidates)
            else:
                last_act_days = -1.0

            snapshot = PortSnapshot(
                scan_time=scan_time,
                switch_name=self.device.name,
                switch_ip=self.device.ip,
                interface=iface,
                status=status_val,
                admin_status=admin_status,
                vlan=vlan_val,
                description=desc,
                mac_addresses=mac_list,
                in_packets=if_detail.get("in_packets", 0),
                out_packets=if_detail.get("out_packets", 0),
                in_octets=if_detail.get("in_octets", 0),
                out_octets=if_detail.get("out_octets", 0),
                last_input_str=last_in,
                last_output_str=last_out,
                last_activity_days=last_act_days,
                is_trunk=is_trunk,
                switchport_mode="trunk" if is_trunk else sw_mode.get("operational_mode", "access"),
                is_portchannel=is_po,
                port_channel_id=po_id,
                has_cdp_neighbor=has_cdp,
                has_lldp_neighbor=has_lldp,
                neighbor_info=neighbor_str,
                speed=speed_val,
                duplex=duplex_val,
                raw_info=f"Last flap: {last_flap}; Packets: In={if_detail.get('in_packets', 0)}, Out={if_detail.get('out_packets', 0)}"
            )
            snapshots.append(snapshot)

        return snapshots

    def _parse_status_table(self, raw_status: str) -> Dict[str, dict]:
        """Parse 'show interfaces status'.

        Format typically:
        Port      Name               Status       Vlan       Duplex  Speed Type
        Gi0/1     Uplink to Core     connected    trunk        a-full  a-1000 10/100/1000BaseTX
        Gi0/2                        notconnect   10           auto    auto 10/100/1000BaseTX
        """
        results = {}
        if not raw_status:
            return results

        lines = raw_status.splitlines()
        header_idx = -1
        for i, line in enumerate(lines):
            if re.match(r"^Port\s+Name\s+Status\s+Vlan", line, re.IGNORECASE):
                header_idx = i
                break

        if header_idx == -1:
            # Fallback regex line by line
            for line in lines:
                parts = line.split()
                if len(parts) >= 6 and re.match(r"^(?:[A-Za-z]{2,}\d[/\d]*|Po\d+)", parts[0]):
                    iface = normalize_interface_name(parts[0])
                    results[iface] = {
                        "name_desc": "",
                        "status": parts[-5] if len(parts) >= 6 else parts[1],
                        "vlan": parts[-4] if len(parts) >= 6 else "1",
                        "duplex": parts[-3],
                        "speed": parts[-2],
                        "type": parts[-1],
                    }
            return results

        header = lines[header_idx]
        col_port = header.find("Port")
        col_name = header.find("Name")
        col_status = header.find("Status")
        col_vlan = header.find("Vlan")
        col_duplex = header.find("Duplex")
        col_speed = header.find("Speed")
        col_type = header.find("Type")

        for line in lines[header_idx + 1:]:
            if not line.strip() or line.startswith("-") or len(line) < col_status:
                continue

            port_part = line[col_port:col_name].strip()
            if not port_part or not re.match(r"^[A-Za-z0-9/.-]+$", port_part):
                continue

            name_part = line[col_name:col_status].strip() if col_name != -1 and col_status != -1 else ""
            status_part = line[col_status:col_vlan].strip() if col_status != -1 and col_vlan != -1 else ""
            vlan_part = line[col_vlan:col_duplex].strip() if col_vlan != -1 and col_duplex != -1 else ""
            duplex_part = line[col_duplex:col_speed].strip() if col_duplex != -1 and col_speed != -1 else ""
            speed_part = line[col_speed:col_type].strip() if col_speed != -1 and col_type != -1 else ""
            type_part = line[col_type:].strip() if col_type != -1 else ""

            norm_iface = normalize_interface_name(port_part)
            results[norm_iface] = {
                "name_desc": name_part,
                "status": status_part,
                "vlan": vlan_part,
                "duplex": duplex_part,
                "speed": speed_part,
                "type": type_part,
            }

        return results

    def _parse_description_table(self, raw_desc: str) -> Dict[str, str]:
        """Parse 'show interfaces description'."""
        results = {}
        if not raw_desc:
            return results

        lines = raw_desc.splitlines()
        for line in lines:
            if not line.strip() or line.startswith("Interface") or line.startswith("-"):
                continue
            # Format: Interface Status Protocol Description
            match = re.match(r"^(\S+)\s+(?:up|down|admin down)\s+(?:up|down)\s*(.*)$", line, re.IGNORECASE)
            if match:
                iface = normalize_interface_name(match.group(1))
                desc = match.group(2).strip()
                results[iface] = desc
        return results

    def _parse_switchport_output(self, raw_switchport: str) -> Dict[str, dict]:
        """Parse 'show interfaces switchport'."""
        results = {}
        if not raw_switchport:
            return results

        current_iface = None
        current_data = {}

        for line in raw_switchport.splitlines():
            line_s = line.strip()
            if line_s.startswith("Name:"):
                if current_iface and current_data:
                    results[current_iface] = current_data
                parts = line_s.split("Name:")
                if len(parts) > 1:
                    current_iface = normalize_interface_name(parts[1].strip())
                    current_data = {"is_trunk": False, "operational_mode": "access", "vlan": "1"}
            elif current_iface:
                if "Operational Mode:" in line_s:
                    mode = line_s.split("Operational Mode:")[1].strip().lower()
                    current_data["operational_mode"] = mode
                    if "trunk" in mode:
                        current_data["is_trunk"] = True
                elif "Access Mode VLAN:" in line_s:
                    vlan_info = line_s.split("Access Mode VLAN:")[1].strip()
                    m = re.search(r"(\d+)", vlan_info)
                    if m:
                        current_data["vlan"] = m.group(1)
                elif "Trunking Native Mode VLAN:" in line_s:
                    vlan_info = line_s.split("Trunking Native Mode VLAN:")[1].strip()
                    m = re.search(r"(\d+)", vlan_info)
                    if m:
                        current_data["native_vlan"] = m.group(1)

        if current_iface and current_data:
            results[current_iface] = current_data

        return results

    def _parse_etherchannel_summary(self, raw_ec: str) -> Dict[str, dict]:
        """Parse 'show etherchannel summary' for bundle members."""
        results = {}
        if not raw_ec:
            return results

        # Typical line:
        # 1      Po1(SU)          LACP      Gi0/1(P)    Gi0/2(P)
        for line in raw_ec.splitlines():
            line_s = line.strip()
            if not line_s or line_s.startswith(("-", "Group", "Flags:", "Number")):
                continue
            match = re.match(r"^(\d+)\s+([A-Za-z0-9_-]+)\(.*?\)\s+[A-Za-z0-9_-]+\s+(.*)$", line_s)
            if match:
                po_num = match.group(1)
                po_name = normalize_interface_name(match.group(2))
                members_str = match.group(3)
                results[po_name] = {"is_member": False, "channel_group": po_name}

                # Find member ports like Gi0/1(P), Te1/0/1(b)
                member_tokens = re.findall(r"([A-Za-z0-9/.-]+)\([A-Za-z]+\)", members_str)
                for mem in member_tokens:
                    norm_mem = normalize_interface_name(mem)
                    results[norm_mem] = {"is_member": True, "channel_group": po_name}

        return results

    def _parse_mac_table(self, raw_mac: str) -> Dict[str, List[str]]:
        """Parse 'show mac address-table'."""
        results = {}
        if not raw_mac:
            return results

        # Format:
        # 10    0014.2201.2345    DYNAMIC     Gi0/1
        for line in raw_mac.splitlines():
            line_s = line.strip()
            if not line_s or line_s.startswith(("-", "Vlan", "Mac Address", "Total", "Multicast")):
                continue
            parts = line_s.split()
            if len(parts) >= 4:
                mac = parts[1]
                port_part = parts[-1]
                # Validate MAC format (xxxx.xxxx.xxxx or xx:xx:xx:xx:xx:xx)
                if re.match(r"^[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}$", mac) or ":" in mac:
                    norm_port = normalize_interface_name(port_part)
                    if norm_port not in results:
                        results[norm_port] = []
                    results[norm_port].append(mac)

        return results

    def _parse_neighbors(self, raw_cdp: str, raw_lldp: str) -> Dict[str, dict]:
        """Parse CDP and LLDP neighbor tables."""
        results = {}

        # CDP Parser
        if raw_cdp:
            for line in raw_cdp.splitlines():
                line_s = line.strip()
                if not line_s or line_s.startswith(("Device ID", "Capability", "---", "Total")):
                    continue
                # Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID
                # SW-Dist-01       Gig 0/24          160              R S I   WS-C2960X Gig 0/48
                parts = line_s.split()
                if len(parts) >= 5:
                    dev_id = parts[0]
                    # Local interface might be split across 2 tokens, e.g., 'Gig' '0/1'
                    loc_iface = ""
                    if len(parts) >= 6 and re.match(r"^[A-Za-z]+$", parts[1]) and re.match(r"^\d", parts[2]):
                        loc_iface = normalize_interface_name(parts[1] + parts[2])
                    elif re.match(r"^[A-Za-z]{2,}\d", parts[1]):
                        loc_iface = normalize_interface_name(parts[1])

                    if loc_iface:
                        results[loc_iface] = {
                            "has_cdp": True,
                            "has_lldp": False,
                            "summary": f"CDP: {dev_id} ({parts[-1]})"
                        }

        # LLDP Parser
        if raw_lldp:
            for line in raw_lldp.splitlines():
                line_s = line.strip()
                if not line_s or line_s.startswith(("Device ID", "Capability", "---", "Total")):
                    continue
                parts = line_s.split()
                if len(parts) >= 4:
                    dev_id = parts[0]
                    loc_iface = ""
                    if len(parts) >= 5 and re.match(r"^[A-Za-z]+$", parts[1]) and re.match(r"^\d", parts[2]):
                        loc_iface = normalize_interface_name(parts[1] + parts[2])
                    elif re.match(r"^[A-Za-z]{2,}\d", parts[1]):
                        loc_iface = normalize_interface_name(parts[1])

                    if loc_iface:
                        existing = results.get(loc_iface, {"has_cdp": False, "has_lldp": False, "summary": ""})
                        existing["has_lldp"] = True
                        if existing["summary"]:
                            existing["summary"] += f" | LLDP: {dev_id}"
                        else:
                            existing["summary"] = f"LLDP: {dev_id} ({parts[-1]})"
                        results[loc_iface] = existing

        return results

    def _parse_interfaces_output(self, raw_interfaces: str) -> Dict[str, dict]:
        """Parse 'show interfaces' to extract Last input, output, and packet counters."""
        results = {}
        if not raw_interfaces:
            return results

        # Interface blocks typically start with 'GigabitEthernet0/1 is up/down...'
        blocks = re.split(r"\n(?=[A-Za-z0-9/.-]+ is )", "\n" + raw_interfaces)

        for block in blocks:
            if not block.strip():
                continue
            first_line = block.strip().splitlines()[0]
            m_iface = re.match(r"^([A-Za-z0-9/.-]+)\s+is\s+([^,]+)(?:,\s*line protocol is\s+([^,\n]+))?", first_line)
            if not m_iface:
                continue

            raw_name = m_iface.group(1)
            norm_iface = normalize_interface_name(raw_name)
            admin_status = m_iface.group(2).strip()
            line_proto = m_iface.group(3).strip() if m_iface.group(3) else "down"

            # Last input / output timers
            # e.g.: "Last input 00:00:01, output 00:00:00, output hang never"
            # or: "Last input never, output never, output hang never"
            last_in = ""
            last_out = ""
            m_last = re.search(r"Last input\s+([^,]+),\s*output\s+([^,]+)", block)
            if m_last:
                last_in = m_last.group(1).strip()
                last_out = m_last.group(2).strip()

            # Last link flapped (IOS-XE)
            last_flap = ""
            m_flap = re.search(r"Last link flapped\s+([^\n,]+)", block)
            if m_flap:
                last_flap = m_flap.group(1).strip()

            # Input / Output packets
            # e.g.: "12345 packets input, 67890 bytes"
            in_pkts = 0
            out_pkts = 0
            m_in = re.search(r"(\d+)\s+packets input", block)
            if m_in:
                in_pkts = int(m_in.group(1))

            m_out = re.search(r"(\d+)\s+packets output", block)
            if m_out:
                out_pkts = int(m_out.group(1))

            results[norm_iface] = {
                "admin_status": admin_status,
                "line_status": line_proto,
                "last_input": last_in,
                "last_output": last_out,
                "last_flap": last_flap,
                "in_packets": in_pkts,
                "out_packets": out_pkts,
            }

        return results
