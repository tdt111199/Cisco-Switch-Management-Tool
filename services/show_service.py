"""Service for retrieving and inspecting Layer 2 switch operational state."""

from typing import Dict, List, Optional
from core.inventory import SwitchDevice
from core.logger import logger
from core.ssh_client import CiscoSSHClient

COMMON_SHOW_COMMANDS = [
    ("show vlan brief", "Danh sách VLAN và cổng gán"),
    ("show interfaces status", "Trạng thái cổng (VLAN, Duplex, Speed, Type)"),
    ("show mac address-table", "Bảng địa chỉ MAC động và tĩnh"),
    ("show spanning-tree", "Thông tin chi tiết Spanning-Tree (STP)"),
    ("show spanning-tree summary", "Tóm tắt trạng thái STP (Root, PortFast, BPDU)"),
    ("show etherchannel summary", "Tóm tắt các nhóm Port-Channel / EtherChannel"),
    ("show port-security", "Thông tin bảo mật cổng Port-Security"),
    ("show ip dhcp snooping", "Trạng thái DHCP Snooping và cổng tin cậy (Trust)"),
    ("show ip dhcp snooping binding", "Bảng gán địa chỉ IP - MAC của DHCP Snooping"),
    ("show ip arp inspection", "Trạng thái kiểm tra ARP động (DAI)"),
    ("show storm-control", "Cấu hình kiểm soát bão broadcast/multicast"),
    ("show cdp neighbors detail", "Thiết bị hàng xóm kết nối qua CDP"),
    ("show lldp neighbors detail", "Thiết bị hàng xóm kết nối qua LLDP"),
    ("show running-config", "Toàn bộ cấu hình đang chạy (Running-Config)"),
    ("show startup-config", "Cấu hình khởi động (Startup-Config)"),
    ("show version", "Phiên bản Cisco IOS và thông tin phần cứng"),
]


class ShowService:
    """Handles operational state inspection on switches."""

    @staticmethod
    def run_command(device: SwitchDevice, command: str) -> str:
        """Run any show/exec command on device."""
        with CiscoSSHClient(device) as client:
            return client.send_command(command, read_timeout=60)

    @staticmethod
    def get_common_commands() -> List[tuple]:
        """Return predefined common show commands."""
        return COMMON_SHOW_COMMANDS
