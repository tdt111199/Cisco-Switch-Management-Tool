"""Safe CLI Configuration and Rollback Generator for Cisco Switches.

Generates shutdown scripts strictly for verified UNUSED ports, with mandatory
exclusion of trunk, uplink, port-channel, CDP/LLDP neighbors, and protected ports.
Generates corresponding rollback scripts with 'no shutdown'.
NEVER applies configuration automatically to devices.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.scanner_models import PortClassification, PortSummaryRecord


class ConfigGenerator:
    """Generates preview-only Cisco IOS shutdown and rollback configuration scripts."""

    @staticmethod
    def filter_eligible_unused_ports(ports: List[PortSummaryRecord]) -> List[PortSummaryRecord]:
        """Strictly filters ports that are eligible for shutdown.

        Excludes:
        - Any port NOT classified as UNUSED
        - Any port marked is_protected = True
        - Any port with is_trunk = True
        - Any port with is_portchannel = True
        - Any port with has_neighbor = True
        """
        eligible = []
        for p in ports:
            if (
                p.classification == PortClassification.UNUSED and
                not p.is_protected and
                not p.is_trunk and
                not p.is_portchannel and
                not p.has_neighbor
            ):
                eligible.append(p)
        return eligible

    @classmethod
    def generate_shutdown_config(
        cls,
        ports: List[PortSummaryRecord],
        author: str = "Network Engineer",
        tag_date: Optional[str] = None,
    ) -> str:
        """Generates Cisco IOS configuration script to shutdown unused ports.

        Groups commands by switch.
        """
        eligible_ports = cls.filter_eligible_unused_ports(ports)
        if not eligible_ports:
            return (
                "! =========================================================================\n"
                "! KHÔNG CÓ CỔNG NÀO ĐỦ ĐIỀU KIỆN UNUSED ĐỂ TẠO CẤU HÌNH SHUTDOWN.\n"
                "! Tất cả các cổng đã được bảo vệ hoặc không thỏa mãn tiêu chí an toàn.\n"
                "! ========================================================================="
            )

        now_str = tag_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_short = datetime.now().strftime("%Y-%m-%d")

        # Group by switch
        by_switch: Dict[Tuple[str, str], List[PortSummaryRecord]] = {}
        for p in eligible_ports:
            key = (p.switch_name, p.switch_ip)
            if key not in by_switch:
                by_switch[key] = []
            by_switch[key].append(p)

        lines = [
            "! " + "=" * 73,
            "! CISCO HISTORICAL UNUSED PORT SCANNER - SHUTDOWN CONFIGURATION SCRIPT",
            f"! Thời gian tạo: {now_str}",
            f"! Người tạo: {author}",
            f"! Tổng số switch: {len(by_switch)} | Tổng số port đủ điều kiện: {len(eligible_ports)}",
            "! ",
            "! LƯU Ý AN TOÀN:",
            "! - Đây là file kịch bản mẫu được sinh tự động để kỹ sư mạng review.",
            "! - Ứng dụng TUYỆT ĐỐI KHÔNG tự động đẩy cấu hình xuống thiết bị.",
            "! - Mọi port Trunk, Uplink, EtherChannel, CDP/LLDP và Protected đã được loại trừ.",
            "! " + "=" * 73,
            "",
        ]

        for (sw_name, sw_ip), sw_ports in by_switch.items():
            lines.append(f"! " + "-" * 73)
            lines.append(f"! Thiết bị: {sw_name} ({sw_ip}) - Số cổng đề xuất: {len(sw_ports)}")
            lines.append(f"! " + "-" * 73)
            lines.append("configure terminal")

            for p in sw_ports:
                lines.append(f"interface {p.interface}")
                # Update description with audit tag while preserving old description
                old_desc = p.description.strip()
                new_desc = f"[UNUSED-SHUTDOWN-{date_short}] {old_desc}".strip()
                lines.append(f" description {new_desc}")
                lines.append(" shutdown")
                lines.append("!")

            lines.append("end")
            lines.append("write memory")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def generate_rollback_config(
        cls,
        ports: List[PortSummaryRecord],
        author: str = "Network Engineer",
    ) -> str:
        """Generates Cisco IOS rollback configuration script to re-enable (no shutdown) ports."""
        eligible_ports = cls.filter_eligible_unused_ports(ports)
        if not eligible_ports:
            return (
                "! =========================================================================\n"
                "! KHÔNG CÓ CỔNG NÀO CẦN TẠO KỊCH BẢN ROLLBACK.\n"
                "! ========================================================================="
            )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Group by switch
        by_switch: Dict[Tuple[str, str], List[PortSummaryRecord]] = {}
        for p in eligible_ports:
            key = (p.switch_name, p.switch_ip)
            if key not in by_switch:
                by_switch[key] = []
            by_switch[key].append(p)

        lines = [
            "! " + "=" * 73,
            "! CISCO HISTORICAL UNUSED PORT SCANNER - ROLLBACK RESTORATION SCRIPT",
            f"! Thời gian tạo: {now_str}",
            f"! Mục đích: Khôi phục hoạt động (no shutdown) cho các port",
            f"! Tổng số switch: {len(by_switch)} | Tổng số port: {len(eligible_ports)}",
            "! " + "=" * 73,
            "",
        ]

        for (sw_name, sw_ip), sw_ports in by_switch.items():
            lines.append(f"! " + "-" * 73)
            lines.append(f"! Thiết bị: {sw_name} ({sw_ip}) - Số cổng khôi phục: {len(sw_ports)}")
            lines.append(f"! " + "-" * 73)
            lines.append("configure terminal")

            for p in sw_ports:
                lines.append(f"interface {p.interface}")
                if p.description.strip():
                    lines.append(f" description {p.description.strip()}")
                lines.append(" no shutdown")
                lines.append("!")

            lines.append("end")
            lines.append("write memory")
            lines.append("")

        return "\n".join(lines)
