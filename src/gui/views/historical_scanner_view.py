"""Historical Unused Port Scanner GUI View (CustomTkinter).

Provides complete dashboard, KPI cards, switch breakdown with unused rates,
historical trend chart, multi-criteria filtering, interactive port table,
safe shutdown/rollback config generation, and Excel/CSV report exports.
"""

import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Set, Tuple

import customtkinter as ctk

from core.inventory import InventoryManager, SwitchDevice
from core.logger import logger
from core.scanner_models import (
    PortClassification,
    PortSnapshot,
    PortSummaryRecord,
    ProtectedPortRecord,
    ScanLogRecord,
    ScanSettings,
    SwitchScanResult,
)
from gui.dialogs.config_preview_dialog import ConfigPreviewDialog
from gui.dialogs.historical_port_detail_dialog import HistoricalPortDetailDialog
from gui.views.trend_chart_canvas import HistoricalTrendChart
from services.scanner.config_generator import ConfigGenerator
from services.scanner.excel_storage import ExcelStorageManager
from services.scanner.historical_scanner_service import HistoricalScannerService
from services.scanner.report_generator import ReportGenerator


class HistoricalScannerView(ctk.CTkFrame):
    """Main view for Cisco Historical Unused Port Scanner."""

    def __init__(
        self,
        master,
        inventory: Optional[InventoryManager] = None,
        storage_manager: Optional[ExcelStorageManager] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.inventory = inventory or InventoryManager()
        self.storage = storage_manager or ExcelStorageManager()
        self.settings = ScanSettings(threshold_days=60)
        self.scanner_service = HistoricalScannerService(self.storage, self.settings)

        # In-memory datasets
        self.port_summaries: List[PortSummaryRecord] = []
        self.protected_records: List[ProtectedPortRecord] = []
        self.scan_logs: List[ScanLogRecord] = []
        self.selected_port_keys: Set[Tuple[str, str]] = set()

        # Build GUI
        self._create_layout()

        # Load initial data from persistent Excel storage
        self._load_data_from_storage()

    def _create_layout(self):
        # Main vertical layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Table expands

        # 1. Top Control Bar (Scan controls & Threshold)
        self._create_top_control_bar()

        # 2. KPI Cards & Switch Summary Drawer
        self._create_kpi_and_summary_section()

        # 3. Filter & Search Bar
        self._create_filter_bar()

        # 4. Main Data Table & Trend Chart Area
        self._create_main_table_area()

        # 5. Bottom Action Bar (Generate Config, Export, Storage folder)
        self._create_bottom_action_bar()

    # ------------------ 1. Top Control Bar ------------------ #

    def _create_top_control_bar(self):
        control_frame = ctk.CTkFrame(self, fg_color=("#F1F5F9", "#1E293B"), corner_radius=8)
        control_frame.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))

        # Title & Subtitle
        header_left = ctk.CTkFrame(control_frame, fg_color="transparent")
        header_left.pack(side="left", padx=12, pady=10)

        ctk.CTkLabel(
            header_left,
            text="🔍 CISCO HISTORICAL UNUSED PORT SCANNER",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38BDF8"
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_left,
            text="Theo dõi lịch sử đa phiên bằng Excel • Phân tích đa tiêu chí an toàn • Đề xuất shutdown bảo vệ hạ tầng",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        ).pack(anchor="w")

        # Right Controls: Threshold, Scan All, Stop, Import
        header_right = ctk.CTkFrame(control_frame, fg_color="transparent")
        header_right.pack(side="right", padx=12, pady=10)

        # Threshold dropdown
        ctk.CTkLabel(header_right, text="Ngưỡng Inactive:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 4))
        self.combo_threshold = ctk.CTkComboBox(
            header_right,
            values=["30 ngày", "60 ngày (Khuyên dùng)", "90 ngày", "180 ngày", "Tùy chỉnh..."],
            width=170,
            command=self._on_threshold_changed
        )
        self.combo_threshold.set("60 ngày (Khuyên dùng)")
        self.combo_threshold.pack(side="left", padx=(0, 8))

        # Import Switch Excel
        btn_import = ctk.CTkButton(
            header_right,
            text="📥 Import Switch",
            width=115,
            fg_color="#334155",
            hover_color="#475569",
            command=self._on_import_switches_clicked
        )
        btn_import.pack(side="left", padx=(0, 8))

        # Scan All Button
        self.btn_scan = ctk.CTkButton(
            header_right,
            text="🚀 Scan All (Quét Tất Cả)",
            width=165,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            font=ctk.CTkFont(weight="bold"),
            command=self._start_scan
        )
        self.btn_scan.pack(side="left", padx=(0, 6))

        # Cancel Button
        self.btn_cancel = ctk.CTkButton(
            header_right,
            text="⏹ Dừng",
            width=80,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            state="disabled",
            command=self._cancel_scan
        )
        self.btn_cancel.pack(side="left")

    # ------------------ 2. KPI Cards & Summary Section ------------------ #

    def _create_kpi_and_summary_section(self):
        self.kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_container.grid(row=1, column=0, sticky="ew", padx=14, pady=4)

        # 6 KPI Cards Grid
        self.kpi_cards = {}
        cards_def = [
            ("switches", "Tổng Switch", "0", "#0284C7"),
            ("total_ports", "Tổng Số Port", "0", "#64748B"),
            ("active", "Port ACTIVE", "0", "#10B981"),
            ("unused", "Port UNUSED", "0", "#EF4444"),
            ("monitor", "Port MONITOR", "0", "#F59E0B"),
            ("protected", "Port PROTECTED", "0", "#3B82F6"),
        ]

        for idx, (key, title, default_val, col) in enumerate(cards_def):
            card = ctk.CTkFrame(self.kpi_container, fg_color=("#F8FAFC", "#1E293B"), corner_radius=8)
            card.pack(side="left", fill="both", expand=True, padx=4)

            lbl_title = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="gray")
            lbl_title.pack(anchor="w", padx=10, pady=(6, 0))

            lbl_val = ctk.CTkLabel(card, text=default_val, font=ctk.CTkFont(size=18, weight="bold"), text_color=col)
            lbl_val.pack(anchor="w", padx=10, pady=(0, 6))
            self.kpi_cards[key] = lbl_val

        # Collapsible Drawer: Per-Switch Summary & Trend Chart toggle
        bar_toggle = ctk.CTkFrame(self, fg_color="transparent")
        bar_toggle.grid(row=2, column=0, sticky="ew", padx=14, pady=(4, 2))

        self.btn_toggle_chart = ctk.CTkButton(
            bar_toggle,
            text="📈 Hiện Biểu Đồ Xu Hướng",
            width=160,
            height=28,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11),
            command=self._toggle_chart_visibility
        )
        self.btn_toggle_chart.pack(side="left")

        self.lbl_switch_stats = ctk.CTkLabel(
            bar_toggle,
            text="Tỷ lệ Unused theo switch: (Chưa có dữ liệu)",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        self.lbl_switch_stats.pack(side="left", padx=12)

        # Embedded Trend Chart (Hidden by default, expandable)
        self.chart_frame = ctk.CTkFrame(self, height=180, fg_color="#1E293B", corner_radius=8)
        self.trend_chart = HistoricalTrendChart(self.chart_frame)
        self.chart_visible = False

    def _toggle_chart_visibility(self):
        if not self.chart_visible:
            self.chart_frame.grid(row=2, column=0, sticky="ew", padx=14, pady=4)
            self.trend_chart.set_data(self.scan_logs)
            self.btn_toggle_chart.configure(text="📉 Ẩn Biểu Đồ Xu Hướng", fg_color="#1E40AF")
            self.chart_visible = True
        else:
            self.chart_frame.grid_forget()
            self.btn_toggle_chart.configure(text="📈 Hiện Biểu Đồ Xu Hướng", fg_color="#334155")
            self.chart_visible = False

    # ------------------ 3. Filter & Search Bar ------------------ #

    def _create_filter_bar(self):
        filter_frame = ctk.CTkFrame(self, fg_color=("#F8FAFC", "#0F172A"), corner_radius=8)
        filter_frame.grid(row=3, column=0, sticky="ew", padx=14, pady=4)

        # Filter by Switch
        ctk.CTkLabel(filter_frame, text="Switch:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=6)
        self.combo_filter_switch = ctk.CTkComboBox(
            filter_frame,
            values=["Tất cả Switch"],
            width=150,
            command=lambda _: self._apply_filters()
        )
        self.combo_filter_switch.pack(side="left", padx=(0, 10), pady=6)

        # Filter by Status / Classification
        ctk.CTkLabel(filter_frame, text="Phân Loại:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4), pady=6)
        self.combo_filter_status = ctk.CTkComboBox(
            filter_frame,
            values=["Tất cả trạng thái", "UNUSED", "ACTIVE", "MONITOR", "PROTECTED", "TRUNK/UPLINK", "PORT-CHANNEL", "ERROR"],
            width=155,
            command=lambda _: self._apply_filters()
        )
        self.combo_filter_status.pack(side="left", padx=(0, 10), pady=6)

        # Filter by VLAN
        ctk.CTkLabel(filter_frame, text="VLAN:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4), pady=6)
        self.entry_filter_vlan = ctk.CTkEntry(filter_frame, width=70, placeholder_text="Tất cả")
        self.entry_filter_vlan.pack(side="left", padx=(0, 10), pady=6)
        self.entry_filter_vlan.bind("<KeyRelease>", lambda _: self._apply_filters())

        # Search Text
        ctk.CTkLabel(filter_frame, text="Tìm kiếm:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4), pady=6)
        self.entry_search = ctk.CTkEntry(
            filter_frame,
            width=220,
            placeholder_text="Interface, Desc, MAC, lý do..."
        )
        self.entry_search.pack(side="left", padx=(0, 12), pady=6)
        self.entry_search.bind("<KeyRelease>", lambda _: self._apply_filters())

        # Reset Filter Button
        btn_reset = ctk.CTkButton(
            filter_frame,
            text="🔄 Xóa Lọc",
            width=80,
            height=28,
            fg_color="#475569",
            hover_color="#334155",
            command=self._reset_filters
        )
        btn_reset.pack(side="left", padx=(0, 8), pady=6)

        # Counter display
        self.lbl_filter_count = ctk.CTkLabel(filter_frame, text="Hiển thị: 0/0", font=ctk.CTkFont(size=11), text_color="#38BDF8")
        self.lbl_filter_count.pack(side="right", padx=12, pady=6)

    # ------------------ 4. Main Data Table ------------------ #

    def _create_main_table_area(self):
        table_container = ctk.CTkFrame(self)
        table_container.grid(row=4, column=0, sticky="nsew", padx=14, pady=4)
        self.grid_rowconfigure(4, weight=1)

        columns = (
            "check", "switch", "interface", "status", "vlan", "description",
            "macs", "days_unused", "consec_scans", "classification", "is_protected", "reason"
        )
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="extended")

        self.tree.heading("check", text="Chọn", command=self._toggle_select_all)
        self.tree.heading("switch", text="Tên Switch", command=lambda: self._sort_by("switch"))
        self.tree.heading("interface", text="Interface", command=lambda: self._sort_by("interface"))
        self.tree.heading("status", text="Trạng Thái", command=lambda: self._sort_by("status"))
        self.tree.heading("vlan", text="VLAN")
        self.tree.heading("description", text="Description")
        self.tree.heading("macs", text="MAC Address")
        self.tree.heading("days_unused", text="Ngày Inactive", command=lambda: self._sort_by("days_unused"))
        self.tree.heading("consec_scans", text="Chuỗi Scan")
        self.tree.heading("classification", text="Phân Loại", command=lambda: self._sort_by("classification"))
        self.tree.heading("is_protected", text="Bảo Vệ?")
        self.tree.heading("reason", text="Lý Giải Phân Loại")

        self.tree.column("check", width=45, anchor="center")
        self.tree.column("switch", width=120, anchor="w")
        self.tree.column("interface", width=115, anchor="w")
        self.tree.column("status", width=85, anchor="center")
        self.tree.column("vlan", width=55, anchor="center")
        self.tree.column("description", width=140, anchor="w")
        self.tree.column("macs", width=110, anchor="w")
        self.tree.column("days_unused", width=90, anchor="center")
        self.tree.column("consec_scans", width=75, anchor="center")
        self.tree.column("classification", width=105, anchor="center")
        self.tree.column("is_protected", width=65, anchor="center")
        self.tree.column("reason", width=220, anchor="w")

        scrollbar_y = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Style tags
        self.tree.tag_configure("tag_unused", background="#FEE2E2", foreground="#991B1B")
        self.tree.tag_configure("tag_active", background="#DCFCE7", foreground="#166534")
        self.tree.tag_configure("tag_monitor", background="#FEF9C3", foreground="#854D0E")
        self.tree.tag_configure("tag_protected", background="#E0F2FE", foreground="#075985")
        self.tree.tag_configure("tag_trunk", background="#F3E8FF", foreground="#581C87")

        # Events: double click & click checkbox
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Context Menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="🔍 Xem Chi Tiết Lịch Sử (Double-Click)", command=self._view_selected_detail)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🛡️ Đánh Dấu Bảo Vệ (Protect)", command=lambda: self._set_protection_for_selected(True))
        self.context_menu.add_command(label="🔓 Bỏ Đánh Dấu Bảo Vệ (Unprotect)", command=lambda: self._set_protection_for_selected(False))
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy Tên Cổng", command=self._copy_interface_name)

    # ------------------ 5. Bottom Action Bar ------------------ #

    def _create_bottom_action_bar(self):
        action_bar = ctk.CTkFrame(self, fg_color=("#F1F5F9", "#1E293B"), corner_radius=8)
        action_bar.grid(row=5, column=0, sticky="ew", padx=14, pady=(4, 10))

        # Left: Protect / Unprotect selected buttons
        btn_protect = ctk.CTkButton(
            action_bar,
            text="🛡️ Bảo Vệ Cổng Chọn",
            width=135,
            fg_color="#0284C7",
            hover_color="#0369A1",
            font=ctk.CTkFont(size=12),
            command=lambda: self._set_protection_for_selected(True)
        )
        btn_protect.pack(side="left", padx=(10, 6), pady=8)

        btn_unprotect = ctk.CTkButton(
            action_bar,
            text="🔓 Bỏ Bảo Vệ",
            width=100,
            fg_color="#64748B",
            hover_color="#475569",
            font=ctk.CTkFont(size=12),
            command=lambda: self._set_protection_for_selected(False)
        )
        btn_unprotect.pack(side="left", padx=(0, 16), pady=8)

        # Right: Config Generation & Export
        btn_shutdown_cfg = ctk.CTkButton(
            action_bar,
            text="⚠️ Tạo Config Shutdown",
            width=165,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            font=ctk.CTkFont(weight="bold"),
            command=self._generate_shutdown_config
        )
        btn_shutdown_cfg.pack(side="right", padx=(6, 10), pady=8)

        btn_rollback_cfg = ctk.CTkButton(
            action_bar,
            text="🔄 Tạo Config Rollback",
            width=160,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(weight="bold"),
            command=self._generate_rollback_config
        )
        btn_rollback_cfg.pack(side="right", padx=(6, 0), pady=8)

        btn_export_excel = ctk.CTkButton(
            action_bar,
            text="📊 Xuất Excel",
            width=105,
            fg_color="#10B981",
            hover_color="#059669",
            command=self._export_excel
        )
        btn_export_excel.pack(side="right", padx=(6, 0), pady=8)

        btn_export_csv = ctk.CTkButton(
            action_bar,
            text="📄 Xuất CSV",
            width=95,
            fg_color="#334155",
            hover_color="#475569",
            command=self._export_csv
        )
        btn_export_csv.pack(side="right", padx=(6, 0), pady=8)

        btn_open_storage = ctk.CTkButton(
            action_bar,
            text="📂 Thư Mục Excel",
            width=120,
            fg_color="#475569",
            hover_color="#334155",
            command=self._open_storage_folder
        )
        btn_open_storage.pack(side="right", padx=(0, 6), pady=8)

    # ------------------ Core Logic & Handlers ------------------ #

    def _load_data_from_storage(self):
        """Loads persistent data from data/port_history.xlsx."""
        try:
            self.port_summaries = self.storage.load_port_summaries()
            self.protected_records = self.storage.load_protected_ports()
            self.scan_logs = self.storage.load_scan_logs()
            self._update_switch_combobox()
            self._update_kpis_and_switch_breakdown()
            self._apply_filters()
            if self.chart_visible:
                self.trend_chart.set_data(self.scan_logs)
        except Exception as e:
            logger.error(f"Lỗi tải dữ liệu lưu trữ: {e}")

    def _update_switch_combobox(self):
        """Populates switch filter combo with unique switch names."""
        switches = set(p.switch_name for p in self.port_summaries)
        # Also include devices from inventory
        for d in self.inventory.get_all():
            switches.add(d.name)
        val_list = ["Tất cả Switch"] + sorted(list(switches))
        self.combo_filter_switch.configure(values=val_list)

    def _update_kpis_and_switch_breakdown(self):
        """Calculates and renders KPI cards and per-switch summary rates."""
        switches_set = {p.switch_name for p in self.port_summaries}
        total_ports = len(self.port_summaries)
        act_cnt = sum(1 for p in self.port_summaries if p.classification == PortClassification.ACTIVE)
        un_cnt = sum(1 for p in self.port_summaries if p.classification == PortClassification.UNUSED)
        mon_cnt = sum(1 for p in self.port_summaries if p.classification == PortClassification.MONITOR)
        prot_cnt = sum(1 for p in self.port_summaries if p.classification == PortClassification.PROTECTED or p.is_protected)

        self.kpi_cards["switches"].configure(text=str(len(switches_set)))
        self.kpi_cards["total_ports"].configure(text=str(total_ports))
        self.kpi_cards["active"].configure(text=str(act_cnt))
        self.kpi_cards["unused"].configure(text=str(un_cnt))
        self.kpi_cards["monitor"].configure(text=str(mon_cnt))
        self.kpi_cards["protected"].configure(text=str(prot_cnt))

        # Per switch breakdown string
        by_switch: Dict[str, List[PortSummaryRecord]] = {}
        for p in self.port_summaries:
            by_switch.setdefault(p.switch_name, []).append(p)

        stats_parts = []
        for sw_name, ports in sorted(by_switch.items()):
            t = len(ports)
            u = sum(1 for p in ports if p.classification == PortClassification.UNUSED)
            pct = round((u / t * 100.0), 1) if t > 0 else 0.0
            stats_parts.append(f"{sw_name}: {pct}% ({u}/{t})")

        if stats_parts:
            self.lbl_switch_stats.configure(text="Tỷ lệ Unused: " + " | ".join(stats_parts[:4]))
        else:
            self.lbl_switch_stats.configure(text="Tỷ lệ Unused: Chưa có dữ liệu phiên quét")

    def _apply_filters(self):
        """Filters self.port_summaries and populates Treeview."""
        sw_filter = self.combo_filter_switch.get().strip()
        status_filter = self.combo_filter_status.get().strip().upper()
        vlan_filter = self.entry_filter_vlan.get().strip()
        search_kw = self.entry_search.get().strip().lower()

        filtered: List[PortSummaryRecord] = []
        for p in self.port_summaries:
            # Switch filter
            if sw_filter != "TẤT CẢ SWITCH" and sw_filter != "Tất cả Switch" and p.switch_name != sw_filter:
                continue
            # Status / Classification filter
            if status_filter not in ("TẤT CẢ TRẠNG THÁI", "TẤT CẢ"):
                cls_val = p.classification.value if hasattr(p.classification, "value") else str(p.classification)
                if cls_val != status_filter:
                    continue
            # VLAN filter
            if vlan_filter and vlan_filter != p.current_vlan:
                continue
            # Search keyword
            if search_kw:
                combined_txt = f"{p.switch_name} {p.interface} {p.description} {','.join(p.current_macs)} {p.classification_reason}".lower()
                if search_kw not in combined_txt:
                    continue

            filtered.append(p)

        # Clear and repopulate tree
        self.tree.delete(*self.tree.get_children())

        for p in filtered:
            key = (p.switch_name, p.interface)
            is_checked = "☑" if key in self.selected_port_keys else "☐"
            cls_str = p.classification.value if hasattr(p.classification, "value") else str(p.classification)

            tag = "tag_unused" if p.classification == PortClassification.UNUSED else (
                "tag_active" if p.classification == PortClassification.ACTIVE else (
                    "tag_monitor" if p.classification == PortClassification.MONITOR else (
                        "tag_protected" if p.classification == PortClassification.PROTECTED else (
                            "tag_trunk" if p.classification in (PortClassification.TRUNK_UPLINK, PortClassification.PORT_CHANNEL) else ""
                        )
                    )
                )
            )

            row_id = self.tree.insert("", "end", values=(
                is_checked,
                p.switch_name,
                p.interface,
                p.current_status,
                p.current_vlan,
                p.description,
                ", ".join(p.current_macs) or "None",
                f"{p.days_unused}d",
                p.consecutive_unused_scans,
                cls_str,
                "Có" if p.is_protected else "Không",
                p.classification_reason
            ), tags=(tag,))

        self.lbl_filter_count.configure(text=f"Hiển thị: {len(filtered)}/{len(self.port_summaries)}")

    def _reset_filters(self):
        self.combo_filter_switch.set("Tất cả Switch")
        self.combo_filter_status.set("Tất cả trạng thái")
        self.entry_filter_vlan.delete(0, "end")
        self.entry_search.delete(0, "end")
        self._apply_filters()

    def _sort_by(self, col: str):
        # Sort current summaries and reload
        if col == "days_unused":
            self.port_summaries.sort(key=lambda x: x.days_unused, reverse=True)
        elif col == "switch":
            self.port_summaries.sort(key=lambda x: x.switch_name)
        elif col == "interface":
            self.port_summaries.sort(key=lambda x: x.interface)
        elif col == "status":
            self.port_summaries.sort(key=lambda x: x.current_status)
        elif col == "classification":
            self.port_summaries.sort(key=lambda x: x.classification.value)
        self._apply_filters()

    # ------------------ Tree Interaction & Selection ------------------ #

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        # Check column is #1
        if col == "#1":
            values = self.tree.item(item_id, "values")
            sw_name = values[1]
            iface = values[2]
            key = (sw_name, iface)

            if key in self.selected_port_keys:
                self.selected_port_keys.remove(key)
                new_box = "☐"
            else:
                self.selected_port_keys.add(key)
                new_box = "☑"

            # Update cell
            new_vals = list(values)
            new_vals[0] = new_box
            self.tree.item(item_id, values=new_vals)

    def _toggle_select_all(self):
        visible_items = self.tree.get_children()
        if not visible_items:
            return

        all_selected = True
        for item in visible_items:
            vals = self.tree.item(item, "values")
            key = (vals[1], vals[2])
            if key not in self.selected_port_keys:
                all_selected = False
                break

        for item in visible_items:
            vals = list(self.tree.item(item, "values"))
            key = (vals[1], vals[2])
            if all_selected:
                if key in self.selected_port_keys:
                    self.selected_port_keys.remove(key)
                vals[0] = "☐"
            else:
                self.selected_port_keys.add(key)
                vals[0] = "☑"
            self.tree.item(item, values=vals)

    def _on_tree_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        vals = self.tree.item(item_id, "values")
        sw_name = vals[1]
        iface = vals[2]
        self._open_port_detail(sw_name, iface)

    def _open_port_detail(self, switch_name: str, interface: str):
        target = next((p for p in self.port_summaries if p.switch_name == switch_name and p.interface == interface), None)
        if not target:
            return

        # Load snapshots for this port from history
        all_hist = self.storage.load_scan_history()
        port_snaps = [s for s in all_hist if s.switch_name == switch_name and s.interface == interface]

        HistoricalPortDetailDialog(
            parent=self,
            port_summary=target,
            snapshots=port_snaps,
            on_toggle_protect_cb=self._on_port_protect_toggled_from_dialog
        )

    def _on_port_protect_toggled_from_dialog(self, port_summary: PortSummaryRecord):
        is_now_protected = not port_summary.is_protected
        self._set_single_port_protection(port_summary.switch_name, port_summary.interface, is_now_protected)

    def _show_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self.tree.selection_set(item_id)
            self.context_menu.post(event.x_root, event.y_root)

    def _view_selected_detail(self):
        sel = self.tree.selection()
        if sel:
            vals = self.tree.item(sel[0], "values")
            self._open_port_detail(vals[1], vals[2])

    def _copy_interface_name(self):
        sel = self.tree.selection()
        if sel:
            vals = self.tree.item(sel[0], "values")
            self.clipboard_clear()
            self.clipboard_append(vals[2])
            messagebox.showinfo("Thông Báo", f"Đã copy interface '{vals[2]}'")

    # ------------------ Protection Management ------------------ #

    def _set_protection_for_selected(self, protect: bool):
        """Marks or unmarks selected ports as Protected."""
        target_keys = set(self.selected_port_keys)
        # If no checkboxes checked, check if rows are highlighted
        if not target_keys:
            for item in self.tree.selection():
                vals = self.tree.item(item, "values")
                target_keys.add((vals[1], vals[2]))

        if not target_keys:
            messagebox.showwarning("Cảnh Báo", "Vui lòng tick chọn ít nhất một cổng để bảo vệ / bỏ bảo vệ!")
            return

        count = 0
        for sw_name, iface in target_keys:
            self._set_single_port_protection(sw_name, iface, protect, save_excel=False)
            count += 1

        # Save protected ports to Excel
        try:
            self.storage.update_protected_ports(self.protected_records)
            self._update_kpis_and_switch_breakdown()
            self._apply_filters()
            action_txt = "bảo vệ" if protect else "bỏ bảo vệ"
            messagebox.showinfo("Thành Công", f"Đã {action_txt} {count} cổng thành công và lưu vào Excel!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu vào Excel: {e}")

    def _set_single_port_protection(self, switch_name: str, interface: str, protect: bool, save_excel: bool = True):
        # Update summary record
        for p in self.port_summaries:
            if p.switch_name == switch_name and p.interface == interface:
                p.is_protected = protect
                if protect:
                    p.classification = PortClassification.PROTECTED
                    p.protection_reason = "Được bảo vệ bởi người dùng."
                    p.classification_reason = "Cổng được đánh dấu Protected — Tuyệt đối không shutdown."
                else:
                    p.classification = PortClassification.MONITOR
                    p.protection_reason = ""
                    p.classification_reason = "Đã bỏ trạng thái bảo vệ. Đưa về diện theo dõi (MONITOR)."

        # Update protected_records list
        self.protected_records = [r for r in self.protected_records if not (r.switch_name == switch_name and r.interface == interface)]
        if protect:
            self.protected_records.append(ProtectedPortRecord(switch_name=switch_name, interface=interface))

        if save_excel:
            try:
                self.storage.update_protected_ports(self.protected_records)
                self._update_kpis_and_switch_breakdown()
                self._apply_filters()
            except Exception as e:
                logger.error(f"Lỗi cập nhật bảo vệ: {e}")

    # ------------------ Threshold & Import ------------------ #

    def _on_threshold_changed(self, choice: str):
        if "30" in choice:
            self.settings.threshold_days = 30
        elif "60" in choice:
            self.settings.threshold_days = 60
        elif "90" in choice:
            self.settings.threshold_days = 90
        elif "180" in choice:
            self.settings.threshold_days = 180
        elif "Tùy chỉnh" in choice:
            dialog = ctk.CTkInputDialog(text="Nhập số ngày ngưỡng không hoạt động (ví dụ: 45):", title="Cấu Hình Ngưỡng")
            val = dialog.get_input()
            if val and val.isdigit() and int(val) > 0:
                self.settings.threshold_days = int(val)
                self.combo_threshold.set(f"{val} ngày (Tùy chỉnh)")
            else:
                self.combo_threshold.set("60 ngày (Khuyên dùng)")
                self.settings.threshold_days = 60

        # Re-evaluate in-memory summaries with new threshold
        self.scanner_service.protection_engine.settings = self.settings
        prot_set = {(r.switch_name, r.interface) for r in self.protected_records}
        self.port_summaries = self.scanner_service.protection_engine.evaluate_all(self.port_summaries, prot_set)
        self._update_kpis_and_switch_breakdown()
        self._apply_filters()

    def _on_import_switches_clicked(self):
        file_path = filedialog.askopenfilename(
            parent=self,
            title="Chọn file danh sách switch Excel/CSV",
            filetypes=[("Excel & CSV Files", "*.xlsx *.xls *.csv"), ("Excel (*.xlsx)", "*.xlsx"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                if file_path.endswith(".csv"):
                    # Use CSV import if available or excel
                    count = self.inventory.import_from_excel(file_path) if not file_path.endswith(".csv") else 0
                else:
                    count = self.inventory.import_from_excel(file_path)
                messagebox.showinfo("Thành Công", f"Đã import thành công {count} thiết bị switch vào danh sách!")
                self._update_switch_combobox()
            except Exception as e:
                messagebox.showerror("Lỗi Import", f"Không thể import tệp switch: {e}")

    # ------------------ Scan Execution ------------------ #

    def _start_scan(self):
        devices = self.inventory.get_all()
        if not devices:
            messagebox.showwarning("Chưa Có Thiết Bị", "Danh sách thiết bị switch đang trống!\nVui lòng thêm switch hoặc import từ Excel.")
            return

        confirm = messagebox.askyesno(
            "Xác Nhận Quét Lịch Sử",
            f"Bắt đầu kết nối SSH và quét {len(devices)} switch?\n\n"
            f"Ngưỡng Inactive: {self.settings.threshold_days} ngày\n"
            f"Dữ liệu sẽ tự động append vào: {os.path.basename(self.storage.file_path)}\n"
            f"Tệp sao lưu tự động lưu tại: backups/excel_history/"
        )
        if not confirm:
            return

        self.btn_scan.configure(state="disabled", text="⏳ Đang Quét...")
        self.btn_cancel.configure(state="normal")

        def _on_switch_done(dev, res: SwitchScanResult):
            status_txt = f"✓ {dev.name} ({len(res.snapshots)} ports)" if res.success else f"✗ {dev.name} ({res.error_message})"
            self.lbl_switch_stats.configure(text=f"Tiến độ: {status_txt}")

        def _on_all_done(updated_summaries: List[PortSummaryRecord], scan_log: ScanLogRecord):
            self.after(0, lambda: self._handle_scan_finished(updated_summaries, scan_log))

        self.scanner_service.run_batch_scan(
            devices=devices,
            on_switch_complete=_on_switch_done,
            on_all_complete=_on_all_done,
        )

    def _cancel_scan(self):
        self.scanner_service.cancel_scan()
        self.btn_cancel.configure(state="disabled")

    def _handle_scan_finished(self, updated_summaries: List[PortSummaryRecord], scan_log: ScanLogRecord):
        self.btn_scan.configure(state="normal", text="🚀 Scan All (Quét Tất Cả)")
        self.btn_cancel.configure(state="disabled")

        self.port_summaries = updated_summaries
        self.scan_logs.append(scan_log)

        self._update_switch_combobox()
        self._update_kpis_and_switch_breakdown()
        self._apply_filters()

        if self.chart_visible:
            self.trend_chart.set_data(self.scan_logs)

        messagebox.showinfo(
            "Hoàn Thành Phiên Quét",
            f"Phiên quét {scan_log.scan_id} đã hoàn tất trong {scan_log.duration_seconds:.1f}s!\n\n"
            f"- Tổng số port phân tích: {scan_log.total_ports}\n"
            f"- Port ACTIVE: {scan_log.active_count}\n"
            f"- Port UNUSED (Đủ điều kiện): {scan_log.unused_count}\n"
            f"- Port MONITOR: {scan_log.monitor_count}\n"
            f"- Port PROTECTED: {scan_log.protected_count}\n\n"
            f"Dữ liệu đã được append và lưu an toàn vào tệp Excel:\n{self.storage.file_path}"
        )

    # ------------------ Config Generation & Exports ------------------ #

    def _get_target_ports_for_config(self) -> List[PortSummaryRecord]:
        """Gets user-selected ports or all UNUSED ports if none checked."""
        if self.selected_port_keys:
            return [p for p in self.port_summaries if (p.switch_name, p.interface) in self.selected_port_keys]
        # Return all UNUSED
        return [p for p in self.port_summaries if p.classification == PortClassification.UNUSED]

    def _generate_shutdown_config(self):
        ports = self._get_target_ports_for_config()
        if not ports:
            messagebox.showinfo("Thông Báo", "Không có cổng nào được chọn hoặc không có cổng UNUSED nào đủ điều kiện.")
            return

        config_text = ConfigGenerator.generate_shutdown_config(ports)
        ConfigPreviewDialog(
            parent=self,
            title="Kịch Bản Cấu Hình Shutdown Port Cisco (Safe Preview)",
            config_text=config_text,
            is_shutdown=True
        )

    def _generate_rollback_config(self):
        ports = self._get_target_ports_for_config()
        if not ports:
            messagebox.showinfo("Thông Báo", "Không có cổng nào cần tạo cấu hình rollback.")
            return

        config_text = ConfigGenerator.generate_rollback_config(ports)
        ConfigPreviewDialog(
            parent=self,
            title="Kịch Bản Rollback No Shutdown (Preview)",
            config_text=config_text,
            is_shutdown=False
        )

    def _export_excel(self):
        if not self.port_summaries:
            messagebox.showwarning("Cảnh Báo", "Chưa có dữ liệu để xuất báo cáo.")
            return
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Xuất Báo Cáo Tổng Hợp Excel",
            initialfile="Cisco_Unused_Ports_Report.xlsx",
            filetypes=[("Excel Files (*.xlsx)", "*.xlsx")]
        )
        if file_path:
            try:
                ReportGenerator.export_excel_report(self.port_summaries, file_path)
                messagebox.showinfo("Thành Công", f"Đã xuất báo cáo Excel thành công tại:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xuất file: {e}")

    def _export_csv(self):
        if not self.port_summaries:
            messagebox.showwarning("Cảnh Báo", "Chưa có dữ liệu để xuất báo cáo.")
            return
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Xuất Danh Sách Cổng CSV",
            initialfile="Cisco_Ports_Data.csv",
            filetypes=[("CSV Files (*.csv)", "*.csv")]
        )
        if file_path:
            try:
                ReportGenerator.export_csv_report(self.port_summaries, file_path)
                messagebox.showinfo("Thành Công", f"Đã xuất báo cáo CSV thành công tại:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xuất file: {e}")

    def _open_storage_folder(self):
        folder = os.path.dirname(self.storage.file_path)
        try:
            if os.name == "nt":
                os.startfile(folder)
            else:
                subprocess.run(["explorer", folder])
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")
