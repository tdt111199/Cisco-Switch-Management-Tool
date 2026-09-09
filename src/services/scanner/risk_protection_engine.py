"""Risk and Protection Engine for Cisco Historical Unused Port Scanner.

Applies strict multi-criteria safety rules to classify ports:
- PROTECTED: In Protected_Ports sheet or user protected.
- TRUNK/UPLINK: Trunk port, CDP/LLDP neighbor discovered, or description contains uplink keywords.
- PORT-CHANNEL: Port-channel or EtherChannel bundle member.
- ACTIVE: Currently connected, learned MACs, or recent traffic.
- UNUSED: Not connected, 0 MAC, no significant traffic, not trunk, not uplink,
          not port-channel, not protected, and Days Unused >= configured threshold.
- MONITOR: Inactive but has not met threshold days yet (under monitoring).
- ERROR: Switch unreachable or command execution failure.
"""

from typing import List, Optional, Set, Tuple

from core.logger import logger
from core.scanner_models import (
    PortClassification,
    PortSummaryRecord,
    ScanSettings,
)


class RiskProtectionEngine:
    """Evaluates port safety criteria and assigns authoritative classifications."""

    def __init__(self, settings: Optional[ScanSettings] = None):
        self.settings = settings or ScanSettings()

    def evaluate_all(
        self,
        summaries: List[PortSummaryRecord],
        protected_ports_set: Set[Tuple[str, str]],
    ) -> List[PortSummaryRecord]:
        """Evaluates and updates classification and reasons for each summary record."""
        for rec in summaries:
            self.evaluate_single(rec, protected_ports_set)
        return summaries

    def evaluate_single(
        self,
        rec: PortSummaryRecord,
        protected_ports_set: Set[Tuple[str, str]],
    ) -> None:
        """Evaluates a single port against multi-criteria rules."""
        key = (rec.switch_name, rec.interface)
        desc_lower = rec.description.lower()

        # 1. Check Protected_Ports explicit user list
        if key in protected_ports_set:
            rec.classification = PortClassification.PROTECTED
            rec.is_protected = True
            rec.protection_reason = "Nằm trong danh sách Protected_Ports do người dùng bảo vệ."
            rec.classification_reason = "Cổng được bảo vệ thủ công. Tuyệt đối không shutdown."
            return

        # 2. Check Port-Channel
        if rec.is_portchannel or rec.interface.lower().startswith("port-channel") or rec.interface.lower().startswith("po"):
            rec.classification = PortClassification.PORT_CHANNEL
            rec.is_protected = True
            rec.protection_reason = "Port-Channel hoặc thành viên EtherChannel bundle."
            rec.classification_reason = "EtherChannel / Port-Channel link — Không phân loại là Unused."
            return

        # 3. Check Trunk
        if rec.is_trunk or "trunk" in rec.current_status.lower() or "trunk" in rec.current_vlan.lower():
            rec.classification = PortClassification.TRUNK_UPLINK
            rec.is_protected = True
            rec.protection_reason = "Cổng Trunk 802.1Q hạ tầng."
            rec.classification_reason = "Trunk port mang lưu lượng nhiều VLAN — Không phân loại là Unused."
            return

        # 4. Check CDP / LLDP Neighbor
        if rec.has_neighbor:
            rec.classification = PortClassification.TRUNK_UPLINK
            rec.is_protected = True
            rec.protection_reason = f"Phát hiện láng giềng CDP/LLDP: {rec.neighbor_info}"
            rec.classification_reason = f"Kết nối thiết bị mạng/hạ tầng: {rec.neighbor_info}"
            return

        # 5. Check Protected Keywords in Description
        for kw in self.settings.protected_keywords:
            if kw and kw in desc_lower:
                rec.classification = PortClassification.TRUNK_UPLINK
                rec.is_protected = True
                rec.protection_reason = f"Mô tả cổng chứa từ khóa bảo vệ '{kw}'"
                rec.classification_reason = f"Description cảnh báo thiết bị quan trọng: '{rec.description}'"
                return

        # 6. Check Active Status
        st = rec.current_status.lower()
        if st in ("connected", "up") or len(rec.current_macs) > 0:
            rec.classification = PortClassification.ACTIVE
            rec.is_protected = False
            rec.protection_reason = ""
            mac_count = len(rec.current_macs)
            rec.classification_reason = f"Cổng đang hoạt động (Status: {rec.current_status}, MAC count: {mac_count})"
            return

        # 7. Check if Error
        if st in ("error", "unknown") and not rec.first_seen:
            rec.classification = PortClassification.ERROR
            rec.is_protected = False
            rec.protection_reason = ""
            rec.classification_reason = "Lỗi thu thập thông tin cổng từ switch."
            return

        # 8. At this point, port is Inactive (down, notconnect, disabled, err-disabled)
        # Check if it qualifies for UNUSED or MONITOR
        threshold = self.settings.threshold_days

        # Strict criteria: 0 MAC, not protected, Days Unused >= threshold
        is_long_inactive = (
            rec.days_unused >= threshold or
            rec.last_input_str.strip().lower() == "never" or
            rec.consecutive_unused_scans >= 3 and rec.days_unused >= (threshold // 2)
        )

        if is_long_inactive:
            rec.classification = PortClassification.UNUSED
            rec.is_protected = False
            rec.protection_reason = ""
            rec.classification_reason = (
                f"Không sử dụng liên tục {rec.days_unused} ngày (> ngưỡng {threshold}d). "
                f"0 MAC học được, 0 traffic, không Trunk/Uplink/Port-Channel. Đủ điều kiện đề xuất shutdown."
            )
        else:
            rec.classification = PortClassification.MONITOR
            rec.is_protected = False
            rec.protection_reason = ""
            rec.classification_reason = (
                f"Đang không kết nối nhưng chưa đạt ngưỡng thời gian ({rec.days_unused}/{threshold} ngày). "
                f"Đưa vào diện theo dõi (MONITOR) qua các phiên scan kế tiếp."
            )
