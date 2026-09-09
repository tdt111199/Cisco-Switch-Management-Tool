"""Cisco Layer 2 Configuration Command Builder.
Generates standard Cisco IOS commands with input validation.
"""

from typing import List, Optional


class L2ConfigBuilder:
    """Utility class to build Cisco IOS CLI commands for Layer 2 features."""

    # ------------------ VLANs ------------------
    @staticmethod
    def build_create_vlan(vlan_id: int, name: str = "") -> List[str]:
        """Create or configure a VLAN."""
        if not (1 <= vlan_id <= 4094):
            raise ValueError("VLAN ID phải nằm trong khoảng từ 1 đến 4094.")
        cmds = [f"vlan {vlan_id}"]
        if name.strip():
            # Cisco vlan name cannot have spaces; sanitize if needed
            safe_name = name.strip().replace(" ", "_")
            cmds.append(f"name {safe_name}")
        cmds.append("exit")
        return cmds

    @staticmethod
    def build_delete_vlan(vlan_id: int) -> List[str]:
        """Delete a VLAN."""
        if vlan_id in [1, 1002, 1003, 1004, 1005]:
            raise ValueError(f"Không thể xóa VLAN mặc định ({vlan_id}).")
        if not (1 <= vlan_id <= 4094):
            raise ValueError("VLAN ID không hợp lệ.")
        return [f"no vlan {vlan_id}"]

    # ------------------ Interface Access / Trunk ------------------
    @staticmethod
    def _format_int_cmd(interface: str) -> str:
        """Helper to format 'interface ...' or 'interface range ...'."""
        clean = interface.strip()
        if any(char in clean for char in ["-", ","]):
            return f"interface range {clean}"
        return f"interface {clean}"

    @staticmethod
    def build_access_port(
        interface: str,
        vlan_id: int,
        voice_vlan: Optional[int] = None
    ) -> List[str]:
        """Configure an interface in Access mode."""
        if not (1 <= vlan_id <= 4094):
            raise ValueError("Access VLAN ID phải nằm trong khoảng từ 1 đến 4094.")
        cmds = [
            L2ConfigBuilder._format_int_cmd(interface),
            "switchport mode access",
            f"switchport access vlan {vlan_id}",
        ]
        if voice_vlan:
            if not (1 <= voice_vlan <= 4094):
                raise ValueError("Voice VLAN ID phải nằm trong khoảng từ 1 đến 4094.")
            cmds.append(f"switchport voice vlan {voice_vlan}")
        cmds.append("exit")
        return cmds

    @staticmethod
    def build_trunk_port(
        interface: str,
        allowed_vlans: str = "all",
        native_vlan: Optional[int] = None,
        encapsulation: str = "dot1q",
    ) -> List[str]:
        """Configure an interface in Trunk mode."""
        cmds = [L2ConfigBuilder._format_int_cmd(interface)]
        # Certain switches (e.g. Catalyst 3560/3750) require encapsulation dot1q before mode trunk
        if encapsulation:
            cmds.append(f"switchport trunk encapsulation {encapsulation}")
        cmds.append("switchport mode trunk")

        if allowed_vlans:
            val = allowed_vlans.strip()
            if val.lower() == "all":
                cmds.append("switchport trunk allowed vlan all")
            elif val.lower().startswith("add "):
                cmds.append(f"switchport trunk allowed vlan {val}")
            elif val.lower().startswith("remove "):
                cmds.append(f"switchport trunk allowed vlan {val}")
            else:
                cmds.append(f"switchport trunk allowed vlan {val}")

        if native_vlan:
            if not (1 <= native_vlan <= 4094):
                raise ValueError("Native VLAN ID phải nằm trong khoảng từ 1 đến 4094.")
            cmds.append(f"switchport trunk native vlan {native_vlan}")

        cmds.append("exit")
        return cmds

    # ------------------ Spanning Tree Protocol (STP) ------------------
    @staticmethod
    def build_stp_mode(mode: str) -> List[str]:
        """Set STP mode: pvst, rapid-pvst, mst."""
        if mode not in ["pvst", "rapid-pvst", "mst"]:
            raise ValueError("Chế độ STP phải là 'pvst', 'rapid-pvst' hoặc 'mst'.")
        return [f"spanning-tree mode {mode}"]

    @staticmethod
    def build_stp_vlan_priority(vlan: str, priority: int) -> List[str]:
        """Set STP priority for VLAN(s). Priority must be multiple of 4096 (0 to 61440)."""
        if priority % 4096 != 0 or not (0 <= priority <= 61440):
            raise ValueError("STP Priority phải là bội số của 4096 (từ 0 đến 61440).")
        return [f"spanning-tree vlan {vlan} priority {priority}"]

    @staticmethod
    def build_stp_root(vlan: str, root_role: str = "primary") -> List[str]:
        """Set root primary or secondary for VLAN(s)."""
        if root_role not in ["primary", "secondary"]:
            raise ValueError("Root role phải là 'primary' hoặc 'secondary'.")
        return [f"spanning-tree vlan {vlan} root {root_role}"]

    @staticmethod
    def build_portfast_bpduguard(
        interface: Optional[str] = None,
        portfast_enable: bool = True,
        bpduguard_enable: bool = True,
        is_global: bool = False
    ) -> List[str]:
        """Configure PortFast and BPDU Guard globally or per interface."""
        cmds = []
        if is_global:
            if portfast_enable:
                cmds.append("spanning-tree portfast default")
            else:
                cmds.append("no spanning-tree portfast default")
            if bpduguard_enable:
                cmds.append("spanning-tree portfast bpduguard default")
            else:
                cmds.append("no spanning-tree portfast bpduguard default")
        else:
            if not interface:
                raise ValueError("Vui lòng chỉ định interface.")
            cmds.append(L2ConfigBuilder._format_int_cmd(interface))
            cmds.append("spanning-tree portfast" if portfast_enable else "spanning-tree portfast disable")
            cmds.append("spanning-tree bpduguard enable" if bpduguard_enable else "spanning-tree bpduguard disable")
            cmds.append("exit")
        return cmds

    # ------------------ EtherChannel ------------------
    @staticmethod
    def build_etherchannel(
        interface: str,
        group_id: int,
        mode: str = "active"
    ) -> List[str]:
        """
        Configure EtherChannel.
        Modes:
          - LACP: active, passive
          - PAgP: desirable, auto
          - Static: on
        """
        valid_modes = ["active", "passive", "desirable", "auto", "on"]
        if mode not in valid_modes:
            raise ValueError(f"Mode EtherChannel không hợp lệ. Chọn một trong: {', '.join(valid_modes)}")
        if not (1 <= group_id <= 64):
            raise ValueError("Channel-group ID phải từ 1 đến 64.")

        cmds = [
            L2ConfigBuilder._format_int_cmd(interface),
            f"channel-group {group_id} mode {mode}",
            "exit"
        ]
        return cmds

    # ------------------ Port Security ------------------
    @staticmethod
    def build_port_security(
        interface: str,
        enable: bool = True,
        max_mac: int = 1,
        violation: str = "shutdown",
        sticky: bool = True,
    ) -> List[str]:
        """Configure Port Security on access interface(s)."""
        cmds = [L2ConfigBuilder._format_int_cmd(interface)]
        if not enable:
            cmds.append("no switchport port-security")
            cmds.append("exit")
            return cmds

        # Ensure switchport mode is access or trunk
        cmds.append("switchport mode access")
        cmds.append("switchport port-security")
        if max_mac > 0:
            cmds.append(f"switchport port-security maximum {max_mac}")
        if violation in ["protect", "restrict", "shutdown"]:
            cmds.append(f"switchport port-security violation {violation}")
        if sticky:
            cmds.append("switchport port-security mac-address sticky")
        cmds.append("exit")
        return cmds

    # ------------------ DHCP Snooping & DAI ------------------
    @staticmethod
    def build_dhcp_snooping(
        enable_global: bool = True,
        vlans: str = "",
        trust_interfaces: Optional[List[str]] = None,
        information_option: bool = True
    ) -> List[str]:
        """Configure DHCP Snooping."""
        cmds = []
        if enable_global:
            cmds.append("ip dhcp snooping")
            if vlans.strip():
                cmds.append(f"ip dhcp snooping vlan {vlans.strip()}")
            if not information_option:
                cmds.append("no ip dhcp snooping information option")
            else:
                cmds.append("ip dhcp snooping information option")
        else:
            cmds.append("no ip dhcp snooping")

        if trust_interfaces:
            for intf in trust_interfaces:
                if intf.strip():
                    cmds.append(L2ConfigBuilder._format_int_cmd(intf))
                    cmds.append("ip dhcp snooping trust")
                    cmds.append("exit")
        return cmds

    @staticmethod
    def build_dai(
        vlans: str,
        trust_interfaces: Optional[List[str]] = None
    ) -> List[str]:
        """Configure Dynamic ARP Inspection (DAI)."""
        cmds = []
        if vlans.strip():
            cmds.append(f"ip arp inspection vlan {vlans.strip()}")
        if trust_interfaces:
            for intf in trust_interfaces:
                if intf.strip():
                    cmds.append(L2ConfigBuilder._format_int_cmd(intf))
                    cmds.append("ip arp inspection trust")
                    cmds.append("exit")
        return cmds

    # ------------------ Storm Control ------------------
    @staticmethod
    def build_storm_control(
        interface: str,
        broadcast_level: Optional[float] = None,
        multicast_level: Optional[float] = None,
        action: str = "trap"  # "trap" or "shutdown"
    ) -> List[str]:
        """Configure Storm Control on interface(s)."""
        cmds = [L2ConfigBuilder._format_int_cmd(interface)]
        if broadcast_level is not None:
            if not (0.0 <= broadcast_level <= 100.0):
                raise ValueError("Ngưỡng broadcast level phải từ 0.0 đến 100.0%.")
            cmds.append(f"storm-control broadcast level {broadcast_level}")
        if multicast_level is not None:
            if not (0.0 <= multicast_level <= 100.0):
                raise ValueError("Ngưỡng multicast level phải từ 0.0 đến 100.0%.")
            cmds.append(f"storm-control multicast level {multicast_level}")
        if action in ["trap", "shutdown"]:
            cmds.append(f"storm-control action {action}")
        cmds.append("exit")
        return cmds

    # ------------------ Interface Management ------------------
    @staticmethod
    def build_interface_settings(
        interface: str,
        description: Optional[str] = None,
        speed: Optional[str] = None,
        duplex: Optional[str] = None,
        shutdown: Optional[bool] = None,
    ) -> List[str]:
        """Configure Interface basic settings (description, speed, duplex, shutdown)."""
        cmds = [L2ConfigBuilder._format_int_cmd(interface)]
        if description is not None:
            if description.strip():
                cmds.append(f"description {description.strip()}")
            else:
                cmds.append("no description")
        if speed:
            cmds.append(f"speed {speed}")
        if duplex:
            cmds.append(f"duplex {duplex}")
        if shutdown is not None:
            cmds.append("shutdown" if shutdown else "no shutdown")
        cmds.append("exit")
        return cmds

    # ------------------ MAC Address Table ------------------
    @staticmethod
    def build_mac_static(mac: str, vlan_id: int, interface: str) -> List[str]:
        """Add static MAC address entry."""
        clean_mac = mac.strip()
        return [f"mac address-table static {clean_mac} vlan {vlan_id} interface {interface.strip()}"]

    @staticmethod
    def build_clear_mac_dynamic(vlan_id: Optional[int] = None, interface: Optional[str] = None) -> str:
        """Generate clear dynamic MAC table command (EXEC command)."""
        cmd = "clear mac address-table dynamic"
        if vlan_id:
            cmd += f" vlan {vlan_id}"
        if interface:
            cmd += f" interface {interface.strip()}"
        return cmd
