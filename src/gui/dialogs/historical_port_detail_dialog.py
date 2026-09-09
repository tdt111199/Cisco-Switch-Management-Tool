"""Port Detail & Historical Snapshots Dialog for Cisco Historical Unused Port Scanner."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, List, Optional
import customtkinter as ctk

from core.scanner_models import PortClassification, PortSnapshot, PortSummaryRecord, ProtectedPortRecord


class HistoricalPortDetailDialog(ctk.CTkToplevel):
    """Modal dialog displaying comprehensive details and snapshot history for a single port."""

    def __init__(
        self,
        parent,
        port_summary: PortSummaryRecord,
        snapshots: List[PortSnapshot],
        on_toggle_protect_cb: Optional[Callable[[PortSummaryRecord], None]] = None,
    ):
        super().__init__(parent)
        self.port_summary = port_summary
        self.snapshots = snapshots
        self.on_toggle_protect_cb = on_toggle_protect_cb

        self.title(f"Chi Tiết Lịch Sử Cổng — {port_summary.switch_name} : {port_summary.interface}")
        self.geometry("860x650")
        self.minsize(750, 520)
        self.grab_set()

        self._create_ui()

    def _create_ui(self):
        # 1. Header Info Banner
        header_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        header_frame.pack(fill="x", padx=16, pady=(16, 10))

        # Title & Status
        top_row = ctk.CTkFrame(header_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 6))

        title_lbl = ctk.CTkLabel(
            top_row,
            text=f"🔌 {self.port_summary.switch_name} ({self.port_summary.switch_ip}) ➔ {self.port_summary.interface}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        )
        title_lbl.pack(side="left")

        # Classification Badge
        cls_color = "#10B981" if self.port_summary.classification == PortClassification.ACTIVE else (
            "#EF4444" if self.port_summary.classification == PortClassification.UNUSED else (
                "#F59E0B" if self.port_summary.classification == PortClassification.MONITOR else "#3B82F6"
            )
        )
        badge = ctk.CTkLabel(
            top_row,
            text=f"  {self.port_summary.classification.value}  ",
            fg_color=cls_color,
            text_color="#FFFFFF",
            corner_radius=6,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        badge.pack(side="right")

        # Quick stats grid
        stats_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=16, pady=(0, 12))

        labels = [
            f"Trạng thái: {self.port_summary.current_status}",
            f"VLAN: {self.port_summary.current_vlan}",
            f"Mô tả: {self.port_summary.description or '(Không có)'}",
            f"MAC học được: {', '.join(self.port_summary.current_macs) or '0 MAC'}",
            f"Số ngày Inactive: {self.port_summary.days_unused} ngày",
            f"Chuỗi Scan Inactive: {self.port_summary.consecutive_unused_scans} lần",
            f"Lần đầu ghi nhận: {self.port_summary.first_seen or 'N/A'}",
            f"Hoạt động gần nhất: {self.port_summary.last_active_time or 'Chưa từng (Never)'}",
            f"Số lần kích hoạt: {self.port_summary.active_transitions} lần",
            f"Bảo vệ: {'Có (Protected)' if self.port_summary.is_protected else 'Không'}",
        ]

        for i, text in enumerate(labels):
            col = i % 3
            row = i // 3
            lbl = ctk.CTkLabel(stats_frame, text=text, font=ctk.CTkFont(size=11), anchor="w")
            lbl.grid(row=row, column=col, sticky="w", padx=8, pady=2)

        # 2. Rationale / Explanation Box
        reason_frame = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=6)
        reason_frame.pack(fill="x", padx=16, pady=(0, 10))
        ctk.CTkLabel(
            reason_frame,
            text=f"💡 Lý giải phân loại: {self.port_summary.classification_reason}",
            font=ctk.CTkFont(size=11, italic=True),
            text_color="#CBD5E1",
            anchor="w",
            wraplength=800,
            justify="left"
        ).pack(padx=12, pady=8, fill="x")

        # 3. Snapshot History Table
        lbl_table = ctk.CTkLabel(
            self,
            text=f"📜 LỊCH SỬ SNAPSHOT QUA CÁC PHIÊN QUÉT ({len(self.snapshots)} bản ghi)",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w"
        )
        lbl_table.pack(fill="x", padx=16, pady=(4, 4))

        tree_frame = ctk.CTkFrame(self)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        columns = ("scan_time", "status", "vlan", "macs", "in_pkts", "out_pkts", "last_input", "is_trunk", "neighbor")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=8)

        self.tree.heading("scan_time", text="Thời Điểm Scan")
        self.tree.heading("status", text="Trạng Thái")
        self.tree.heading("vlan", text="VLAN")
        self.tree.heading("macs", text="MAC Address")
        self.tree.heading("in_pkts", text="Gói Vào (In)")
        self.tree.heading("out_pkts", text="Gói Ra (Out)")
        self.tree.heading("last_input", text="Last Input")
        self.tree.heading("is_trunk", text="Trunk?")
        self.tree.heading("neighbor", text="CDP/LLDP")

        self.tree.column("scan_time", width=140, anchor="center")
        self.tree.column("status", width=90, anchor="center")
        self.tree.column("vlan", width=60, anchor="center")
        self.tree.column("macs", width=150, anchor="w")
        self.tree.column("in_pkts", width=80, anchor="e")
        self.tree.column("out_pkts", width=80, anchor="e")
        self.tree.column("last_input", width=90, anchor="center")
        self.tree.column("is_trunk", width=60, anchor="center")
        self.tree.column("neighbor", width=140, anchor="w")

        scrollbar_y = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")

        # Populate snapshots in reverse chronological order
        for s in reversed(self.snapshots):
            macs_str = ", ".join(s.mac_addresses) if s.mac_addresses else "None"
            neigh_str = s.neighbor_info or ("Yes" if (s.has_cdp_neighbor or s.has_lldp_neighbor) else "No")
            self.tree.insert("", "end", values=(
                s.scan_time,
                s.status,
                s.vlan,
                macs_str,
                s.in_packets,
                s.out_packets,
                s.last_input_str or "N/A",
                "Yes" if s.is_trunk else "No",
                neigh_str,
            ))

        # 4. Bottom Action Buttons
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 16))

        protect_btn_text = "🛡️ Bỏ Bảo Vệ (Unprotect)" if self.port_summary.is_protected else "🛡️ Đánh Dấu Bảo Vệ (Protect)"
        protect_btn_color = "#DC2626" if self.port_summary.is_protected else "#2563EB"

        btn_protect = ctk.CTkButton(
            btn_bar,
            text=protect_btn_text,
            fg_color=protect_btn_color,
            command=self._on_toggle_protect,
            font=ctk.CTkFont(weight="bold")
        )
        btn_protect.pack(side="left", padx=(0, 8))

        btn_close = ctk.CTkButton(
            btn_bar,
            text="Đóng",
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy,
            width=90
        )
        btn_close.pack(side="right")

    def _on_toggle_protect(self):
        if self.on_toggle_protect_cb:
            self.on_toggle_protect_cb(self.port_summary)
            self.destroy()
