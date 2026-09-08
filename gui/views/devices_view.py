"""Devices Inventory View with CRUD, multi-select, import/export and SSH testing."""

import os
import threading
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
from core.inventory import InventoryManager, SwitchDevice
from core.logger import logger
from core.ssh_client import CiscoSSHClient
from gui.dialogs.device_dialog import DeviceDialog


class DevicesView(ctk.CTkFrame):
    """View managing the list of switches and selection state."""

    def __init__(self, parent, inventory: InventoryManager, on_selection_changed=None):
        super().__init__(parent, fg_color="transparent")
        self.inventory = inventory
        self.on_selection_changed = on_selection_changed
        self.device_check_vars = {}  # {device_id: tk.BooleanVar}

        self._create_widgets()
        self.refresh_table()

    def _create_widgets(self):
        # 1. Top Control Bar (Search, Filter, Actions)
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.pack(fill="x", padx=10, pady=(10, 5))

        # Search box
        self.ent_search = ctk.CTkEntry(top_bar, placeholder_text="🔍 Tìm kiếm theo tên hoặc IP...", width=240)
        self.ent_search.pack(side="left", padx=(0, 10))
        self.ent_search.bind("<KeyRelease>", lambda e: self._apply_filter())

        # Group filter
        self.combo_group = ctk.CTkComboBox(
            top_bar,
            values=["Tất cả nhóm"],
            command=lambda v: self._apply_filter(),
            width=150
        )
        self.combo_group.set("Tất cả nhóm")
        self.combo_group.pack(side="left", padx=(0, 10))

        # Quick action buttons on right of top bar
        self.btn_add = ctk.CTkButton(
            top_bar,
            text="➕ Thêm Switch",
            fg_color="#2FA572",
            hover_color="#107C41",
            width=120,
            command=self._open_add_dialog
        )
        self.btn_add.pack(side="right", padx=(5, 0))

        self.btn_test = ctk.CTkButton(
            top_bar,
            text="⚡ Test SSH",
            fg_color="#3B8ED0",
            hover_color="#36719F",
            width=100,
            command=self._test_selected_devices
        )
        self.btn_test.pack(side="right", padx=(5, 0))

        self.btn_edit = ctk.CTkButton(
            top_bar,
            text="✏️ Sửa",
            fg_color="#4A5568",
            hover_color="#2D3748",
            width=80,
            command=self._open_edit_dialog
        )
        self.btn_edit.pack(side="right", padx=(5, 0))

        self.btn_delete = ctk.CTkButton(
            top_bar,
            text="🗑️ Xóa",
            fg_color="#E53E3E",
            hover_color="#C53030",
            width=80,
            command=self._delete_selected
        )
        self.btn_delete.pack(side="right", padx=(5, 0))

        # 2. Secondary Bar (Batch select, Import/Export, Device count)
        sec_bar = ctk.CTkFrame(self, fg_color="transparent")
        sec_bar.pack(fill="x", padx=10, pady=(5, 5))

        self.var_select_all = ctk.BooleanVar(value=False)
        self.chk_select_all = ctk.CTkCheckBox(
            sec_bar,
            text="Chọn tất cả hiển thị",
            variable=self.var_select_all,
            command=self._toggle_select_all
        )
        self.chk_select_all.pack(side="left")

        self.lbl_count = ctk.CTkLabel(sec_bar, text="Tổng số: 0 switch | Đã chọn: 0", text_color="gray")
        self.lbl_count.pack(side="left", padx=20)

        # Import / Export buttons
        self.btn_export = ctk.CTkButton(
            sec_bar,
            text="📤 Xuất DS",
            fg_color="#4A5568",
            hover_color="#2D3748",
            width=90,
            command=self._export_menu
        )
        self.btn_export.pack(side="right", padx=(5, 0))

        self.btn_import = ctk.CTkButton(
            sec_bar,
            text="📥 Nhập DS",
            fg_color="#4A5568",
            hover_color="#2D3748",
            width=90,
            command=self._import_menu
        )
        self.btn_import.pack(side="right", padx=(5, 0))

        # 3. Main Device List Table
        # We use a custom modern CTkScrollableFrame with rows
        table_container = ctk.CTkFrame(self, corner_radius=8)
        table_container.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Header row
        header_frame = ctk.CTkFrame(table_container, fg_color="#2B2B2B", height=36, corner_radius=6)
        header_frame.pack(fill="x", padx=4, pady=(4, 2))
        header_frame.pack_propagate(False)

        col_configs = [
            ("Chọn", 60),
            ("Tên Switch (Hostname)", 180),
            ("Địa chỉ IP", 140),
            ("Port", 60),
            ("Nhóm", 120),
            ("Loại", 90),
            ("Tài khoản", 100),
            ("Ghi chú", 180),
        ]
        for name, width in col_configs:
            lbl = ctk.CTkLabel(
                header_frame,
                text=name,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=width,
                anchor="w" if width > 60 else "center"
            )
            lbl.pack(side="left", padx=4)

        # Scrollable rows area
        self.scroll_rows = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.scroll_rows.pack(fill="both", expand=True, padx=2, pady=2)

    def refresh_table(self):
        """Re-render switch rows according to current search and filters."""
        # Update group dropdown
        groups = ["Tất cả nhóm"] + self.inventory.get_groups()
        self.combo_group.configure(values=groups)

        self._apply_filter()

    def _apply_filter(self):
        query = self.ent_search.get().strip().lower()
        selected_group = self.combo_group.get()

        # Clear existing rows
        for widget in self.scroll_rows.winfo_children():
            widget.destroy()

        devices = self.inventory.get_all()
        filtered = []
        for dev in devices:
            # Group filter
            if selected_group != "Tất cả nhóm" and dev.group != selected_group:
                continue
            # Query filter
            if query:
                if query not in dev.name.lower() and query not in dev.ip.lower() and query not in dev.notes.lower():
                    continue
            filtered.append(dev)

        # Render rows
        for idx, dev in enumerate(filtered):
            row_bg = "#1F1F1F" if idx % 2 == 0 else "#262626"
            row_frame = ctk.CTkFrame(self.scroll_rows, fg_color=row_bg, height=38, corner_radius=4)
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)

            # Checkbox
            var = self.device_check_vars.setdefault(dev.id, ctk.BooleanVar(value=False))
            chk = ctk.CTkCheckBox(
                row_frame,
                text="",
                variable=var,
                width=24,
                command=self._on_check_changed
            )
            chk.pack(side="left", padx=(16, 20))

            # Labels
            ctk.CTkLabel(row_frame, text=dev.name, width=180, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=dev.ip, width=140, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=str(dev.port), width=60, anchor="center").pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=dev.group, width=120, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=dev.device_type, width=90, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=dev.username, width=100, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row_frame, text=dev.notes or "-", width=180, anchor="w", text_color="gray").pack(side="left", padx=4)

            # Bind double click on row to edit
            row_frame.bind("<Double-Button-1>", lambda e, d=dev: self._open_edit_dialog(d))

        self._update_status_counts()

    def _toggle_select_all(self):
        val = self.var_select_all.get()
        for v in self.device_check_vars.values():
            v.set(val)
        self._on_check_changed()

    def _on_check_changed(self):
        self._update_status_counts()
        if self.on_selection_changed:
            self.on_selection_changed(self.get_selected_devices())

    def _update_status_counts(self):
        total = len(self.inventory.get_all())
        selected = len(self.get_selected_devices())
        self.lbl_count.configure(text=f"Tổng số: {total} switch | Đã chọn: {selected}")

    def get_selected_devices(self) -> list:
        """Return list of SwitchDevice objects currently checked."""
        selected = []
        for dev_id, var in self.device_check_vars.items():
            if var.get():
                dev = self.inventory.get_by_id(dev_id)
                if dev:
                    selected.append(dev)
        return selected

    def _open_add_dialog(self):
        DeviceDialog(
            parent=self.winfo_toplevel(),
            device=None,
            groups=self.inventory.get_groups(),
            on_save=self._on_device_saved
        )

    def _open_edit_dialog(self, target_device=None):
        if not target_device:
            selected = self.get_selected_devices()
            if not selected:
                messagebox.showwarning("Chưa chọn thiết bị", "Vui lòng chọn hoặc nhấp đúp vào 1 switch để sửa.", parent=self)
                return
            target_device = selected[0]

        DeviceDialog(
            parent=self.winfo_toplevel(),
            device=target_device,
            groups=self.inventory.get_groups(),
            on_save=self._on_device_saved
        )

    def _on_device_saved(self, device: SwitchDevice):
        self.inventory.add_device(device)
        self.refresh_table()
        logger.success(f"Đã lưu thông tin switch: {device.name} ({device.ip})")

    def _delete_selected(self):
        selected = self.get_selected_devices()
        if not selected:
            messagebox.showwarning("Chưa chọn thiết bị", "Vui lòng chọn ít nhất một switch để xóa.", parent=self)
            return

        names = ", ".join([d.name for d in selected[:3]])
        if len(selected) > 3:
            names += f" và {len(selected) - 3} switch khác"

        if messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa {len(selected)} switch sau đây?\n{names}", parent=self):
            for dev in selected:
                self.inventory.delete_device(dev.id)
                self.device_check_vars.pop(dev.id, None)
            self.refresh_table()
            logger.info(f"Đã xóa {len(selected)} switch khỏi danh sách.")

    def _test_selected_devices(self):
        selected = self.get_selected_devices()
        if not selected:
            messagebox.showwarning("Chưa chọn thiết bị", "Vui lòng chọn ít nhất một switch để kiểm tra SSH.", parent=self)
            return

        self.btn_test.configure(state="disabled", text="Đang test...")

        def _worker():
            results = []
            for dev in selected:
                client = CiscoSSHClient(dev, timeout=10)
                ok, msg = client.test_connection()
                status_str = "Thành công ✅" if ok else f"Thất bại ❌ ({msg})"
                results.append(f"• {dev.name} ({dev.ip}): {status_str}")
            self.after(0, lambda: self._on_batch_test_done(results))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_batch_test_done(self, results):
        self.btn_test.configure(state="normal", text="⚡ Test SSH")
        report = "\n".join(results)
        messagebox.showinfo("Kết Quả Kiểm Tra SSH", report, parent=self)

    def _export_menu(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Xuất danh sách Switch",
            defaultextension=".xlsx",
            filetypes=[
                ("Excel File (*.xlsx)", "*.xlsx"),
                ("CSV File (*.csv)", "*.csv"),
                ("JSON File (*.json)", "*.json")
            ]
        )
        if not path:
            return
        try:
            if path.endswith(".xlsx") or path.endswith(".xls"):
                self.inventory.export_to_excel(path, include_credentials=False)
            elif path.endswith(".json"):
                self.inventory.export_to_json(path, include_credentials=False)
            else:
                self.inventory.export_to_csv(path, include_credentials=False)
            messagebox.showinfo("Thành công", f"Đã xuất danh sách switch ra file:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi khi xuất", str(e), parent=self)

    def _import_menu(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Nhập danh sách Switch",
            filetypes=[
                ("Tất cả tệp hỗ trợ (*.xlsx;*.csv;*.json)", "*.xlsx;*.xls;*.csv;*.json"),
                ("Excel File (*.xlsx)", "*.xlsx;*.xls"),
                ("CSV File (*.csv)", "*.csv"),
                ("JSON File (*.json)", "*.json"),
                ("Tất cả tệp (*.*)", "*.*")
            ]
        )
        if not path:
            return
        try:
            cnt = self.inventory.import_file(path)
            self.refresh_table()
            messagebox.showinfo("Thành công", f"Đã nhập thành công {cnt} switch từ file:\n{os.path.basename(path)}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi khi nhập", str(e), parent=self)
