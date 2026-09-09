"""Backup and Restore View with safety backup and backup repository browser."""

import os
import subprocess
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk
from core.inventory import SwitchDevice
from core.logger import logger
from gui.dialogs.confirm_dialog import ConfirmDialog
from services.backup_service import (
    BackupService,
    BACKUP_TYPE_BOTH,
    BACKUP_TYPE_RUNNING,
    BACKUP_TYPE_STARTUP,
)
from services.restore_service import (
    RestoreService,
    RESTORE_TARGET_RUNNING,
    RESTORE_TARGET_STARTUP,
)


class BackupRestoreView(ctk.CTkFrame):
    """View handling backup operations and safe configuration restoration."""

    def __init__(self, parent, backup_service: BackupService, restore_service: RestoreService, get_selected_devices_cb, get_all_devices_cb):
        super().__init__(parent, fg_color="transparent")
        self.backup_service = backup_service
        self.restore_service = restore_service
        self.get_selected_devices = get_selected_devices_cb
        self.get_all_devices = get_all_devices_cb

        self._create_widgets()
        self.refresh_backups_list()

    def _create_widgets(self):
        # 1. Top Section: Two Cards (Backup Card & Restore Card)
        top_cards = ctk.CTkFrame(self, fg_color="transparent")
        top_cards.pack(fill="x", padx=10, pady=(10, 5))

        # Backup Card (Left)
        card_backup = ctk.CTkFrame(top_cards, corner_radius=8)
        card_backup.pack(side="left", fill="both", expand=True, padx=(0, 6), pady=2)

        lbl_bk_title = ctk.CTkLabel(
            card_backup,
            text="💾 Sao Lưu Cấu Hình (Backup)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#38BDF8"
        )
        lbl_bk_title.pack(anchor="w", padx=14, pady=(12, 6))

        self.lbl_bk_target = ctk.CTkLabel(
            card_backup,
            text="Mục tiêu: Đang chọn 0 switch (hỗ trợ sao lưu hàng loạt)",
            text_color="gray",
            anchor="w"
        )
        self.lbl_bk_target.pack(fill="x", padx=14, pady=2)

        # Backup options
        f_bk_opt = ctk.CTkFrame(card_backup, fg_color="transparent")
        f_bk_opt.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(f_bk_opt, text="Loại sao lưu:", width=90, anchor="w").pack(side="left")
        self.var_bk_type = ctk.StringVar(value=BACKUP_TYPE_BOTH)
        ctk.CTkRadioButton(f_bk_opt, text="Cả hai (Running & Startup)", variable=self.var_bk_type, value=BACKUP_TYPE_BOTH).pack(side="left", padx=4)
        ctk.CTkRadioButton(f_bk_opt, text="Chỉ Running", variable=self.var_bk_type, value=BACKUP_TYPE_RUNNING).pack(side="left", padx=4)
        ctk.CTkRadioButton(f_bk_opt, text="Chỉ Startup", variable=self.var_bk_type, value=BACKUP_TYPE_STARTUP).pack(side="left", padx=4)

        # Backup button
        self.btn_run_backup = ctk.CTkButton(
            card_backup,
            text="🚀 Bắt Đầu Sao Lưu",
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=36,
            command=self._start_backup_process
        )
        self.btn_run_backup.pack(fill="x", padx=14, pady=(8, 14))

        # Restore Card (Right)
        card_restore = ctk.CTkFrame(top_cards, corner_radius=8)
        card_restore.pack(side="right", fill="both", expand=True, padx=(6, 0), pady=2)

        lbl_res_title = ctk.CTkLabel(
            card_restore,
            text="🔄 Khôi Phục Cấu Hình (Restore)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#F59E0B"
        )
        lbl_res_title.pack(anchor="w", padx=14, pady=(12, 6))

        # Target switch dropdown for restore
        f_res_dev = ctk.CTkFrame(card_restore, fg_color="transparent")
        f_res_dev.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(f_res_dev, text="Switch đích:", width=90, anchor="w").pack(side="left")
        self.combo_res_device = ctk.CTkComboBox(f_res_dev, values=["(Chọn Switch)"], width=260)
        self.combo_res_device.set("(Chọn Switch)")
        self.combo_res_device.pack(side="left", fill="x", expand=True)

        # File picker for backup file
        f_res_file = ctk.CTkFrame(card_restore, fg_color="transparent")
        f_res_file.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(f_res_file, text="Tệp cấu hình:", width=90, anchor="w").pack(side="left")
        self.ent_res_file = ctk.CTkEntry(f_res_file, placeholder_text="Đường dẫn file .cfg / .txt")
        self.ent_res_file.pack(side="left", fill="x", expand=True, padx=(0, 6))
        btn_browse = ctk.CTkButton(f_res_file, text="Chọn tệp...", width=70, command=self._browse_restore_file)
        btn_browse.pack(side="right")

        # Target config & Safety guarantee
        f_res_target = ctk.CTkFrame(card_restore, fg_color="transparent")
        f_res_target.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(f_res_target, text="Khôi phục vào:", width=90, anchor="w").pack(side="left")
        self.combo_res_target = ctk.CTkComboBox(f_res_target, values=["Running-config", "Startup-config"], width=150)
        self.combo_res_target.set("Running-config")
        self.combo_res_target.pack(side="left", padx=(0, 10))

        self.var_safety_backup = ctk.BooleanVar(value=True)
        self.chk_safety = ctk.CTkCheckBox(
            f_res_target,
            text="Tự động sao lưu Running-config trước khi restore",
            variable=self.var_safety_backup,
            state="disabled"  # Mandatory safety requirement!
        )
        self.chk_safety.pack(side="left")

        # Restore button
        self.btn_run_restore = ctk.CTkButton(
            card_restore,
            text="⚠️ Khôi Phục Cấu Hình An Toàn",
            fg_color="#D97706",
            hover_color="#B45309",
            height=36,
            command=self._start_restore_process
        )
        self.btn_run_restore.pack(fill="x", padx=14, pady=(8, 14))

        # 2. Bottom Section: Backup Repository & File Browser
        repo_container = ctk.CTkFrame(self, corner_radius=8)
        repo_container.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Repo toolbar
        repo_bar = ctk.CTkFrame(repo_container, fg_color="transparent")
        repo_bar.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            repo_bar,
            text="📁 Danh Sách Bản Sao Lưu Hiện Có (Backup History)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        btn_open_folder = ctk.CTkButton(
            repo_bar,
            text="📂 Mở Thư Mục Backup",
            fg_color="#475569",
            hover_color="#334155",
            width=140,
            command=self._open_backup_directory
        )
        btn_open_folder.pack(side="right", padx=(6, 0))

        btn_refresh_repo = ctk.CTkButton(
            repo_bar,
            text="🔄 Làm Mới",
            fg_color="#475569",
            hover_color="#334155",
            width=90,
            command=self.refresh_backups_list
        )
        btn_refresh_repo.pack(side="right", padx=(6, 0))

        # Header for backups table
        b_header = ctk.CTkFrame(repo_container, fg_color="#2B2B2B", height=32, corner_radius=4)
        b_header.pack(fill="x", padx=10, pady=(2, 2))
        b_header.pack_propagate(False)

        ctk.CTkLabel(b_header, text="Thiết Bị / Thư Mục", width=220, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
        ctk.CTkLabel(b_header, text="Tên Tệp Sao Lưu", width=260, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(b_header, text="Loại", width=120, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(b_header, text="Dung Lượng", width=90, anchor="center", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(b_header, text="Thời Gian Tạo", width=150, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(b_header, text="Thao Tác", width=130, anchor="center", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=8)

        # Scrollable list of backups
        self.scroll_backups = ctk.CTkScrollableFrame(repo_container, fg_color="transparent")
        self.scroll_backups.pack(fill="both", expand=True, padx=8, pady=(2, 8))

    def update_selected_devices_display(self, selected_devices):
        """Update switch counts and populate restore device dropdown."""
        count = len(selected_devices)
        if count == 0:
            self.lbl_bk_target.configure(text="Mục tiêu: Đang chọn 0 switch (Hãy chọn switch ở tab Quản lý)", text_color="#EF4444")
        elif count == 1:
            self.lbl_bk_target.configure(text=f"Mục tiêu: 1 Switch ({selected_devices[0].name} - {selected_devices[0].ip})", text_color="#22C55E")
        else:
            self.lbl_bk_target.configure(text=f"Mục tiêu: {count} Switch (Sao lưu ĐỒNG LOẠT nhiều switch)", text_color="#EAB308")

        all_devices = self.get_all_devices()
        dev_names = [f"{d.name} ({d.ip})" for d in all_devices]
        self.combo_res_device.configure(values=dev_names if dev_names else ["(Không có thiết bị)"])
        if selected_devices and f"{selected_devices[0].name} ({selected_devices[0].ip})" in dev_names:
            self.combo_res_device.set(f"{selected_devices[0].name} ({selected_devices[0].ip})")

    def refresh_backups_list(self):
        """Reload list of backup files."""
        for widget in self.scroll_backups.winfo_children():
            widget.destroy()

        backups = self.backup_service.list_backups()
        if not backups:
            lbl_empty = ctk.CTkLabel(self.scroll_backups, text="Chưa có bản sao lưu nào được tạo.", text_color="gray")
            lbl_empty.pack(pady=20)
            return

        for idx, item in enumerate(backups):
            row_bg = "#1F1F1F" if idx % 2 == 0 else "#262626"
            row = ctk.CTkFrame(self.scroll_backups, fg_color=row_bg, height=36, corner_radius=4)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=item["device_folder"], width=220, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=item["file_name"], width=260, anchor="w").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=item["type"], width=120, anchor="w", text_color="#38BDF8").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=item["size_bytes"], width=90, anchor="center").pack(side="left", padx=4)
            ctk.CTkLabel(row, text=item["modified_at"], width=150, anchor="w", text_color="gray").pack(side="left", padx=4)

            # Actions: View & Delete & Use for restore
            actions_frame = ctk.CTkFrame(row, fg_color="transparent")
            actions_frame.pack(side="right", padx=6)

            btn_use = ctk.CTkButton(
                actions_frame,
                text="Chọn Restore",
                width=80,
                height=24,
                fg_color="#D97706",
                hover_color="#B45309",
                command=lambda p=item["file_path"]: self._select_file_for_restore(p)
            )
            btn_use.pack(side="left", padx=2)

            btn_view = ctk.CTkButton(
                actions_frame,
                text="👁",
                width=30,
                height=24,
                fg_color="#475569",
                hover_color="#334155",
                command=lambda p=item["file_path"], n=item["file_name"]: self._view_backup_file(p, n)
            )
            btn_view.pack(side="left", padx=2)

            btn_del = ctk.CTkButton(
                actions_frame,
                text="🗑️",
                width=30,
                height=24,
                fg_color="#EF4444",
                hover_color="#DC2626",
                command=lambda p=item["file_path"]: self._delete_backup_file(p)
            )
            btn_del.pack(side="left", padx=2)

    def _select_file_for_restore(self, file_path: str):
        self.ent_res_file.delete(0, "end")
        self.ent_res_file.insert(0, file_path)

    def _browse_restore_file(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Chọn tệp sao lưu Cisco IOS",
            initialdir=self.backup_service.backup_root_dir,
            filetypes=[("Cisco Config (*.cfg, *.txt)", "*.cfg;*.txt"), ("Tất cả tệp (*.*)", "*.*")]
        )
        if path:
            self._select_file_for_restore(path)

    def _view_backup_file(self, file_path: str, file_name: str):
        if not os.path.exists(file_path):
            messagebox.showerror("Lỗi", "Tệp không tồn tại.", parent=self)
            return

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        win = ctk.CTkToplevel(self.winfo_toplevel())
        win.title(f"Xem nội dung: {file_name}")
        win.geometry("700x550")
        win.transient(self.winfo_toplevel())

        top_info = ctk.CTkLabel(win, text=f"Tệp: {file_path}", anchor="w", text_color="gray")
        top_info.pack(fill="x", padx=16, pady=(12, 4))

        txt = ctk.CTkTextbox(win, font=ctk.CTkFont(family="Consolas", size=12))
        txt.pack(fill="both", expand=True, padx=16, pady=8)
        txt.insert("1.0", content)
        txt.configure(state="disabled")

        btn_close = ctk.CTkButton(win, text="Đóng", width=90, command=win.destroy)
        btn_close.pack(pady=(0, 12))

    def _delete_backup_file(self, file_path: str):
        if messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa tệp sao lưu này?\n{os.path.basename(file_path)}", parent=self):
            try:
                os.remove(file_path)
                self.refresh_backups_list()
                logger.info(f"Đã xóa tệp sao lưu: {file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi xóa tệp", str(e), parent=self)

    def _open_backup_directory(self):
        path = os.path.abspath(self.backup_service.backup_root_dir)
        try:
            os.startfile(path)
        except Exception:
            try:
                subprocess.Popen(["explorer", path])
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}", parent=self)

    # ------------------ Process Executions ------------------
    def _start_backup_process(self):
        selected = self.get_selected_devices()
        if not selected:
            messagebox.showwarning("Chưa chọn Switch", "Vui lòng chọn ít nhất một switch ở tab 'Quản lý Thiết bị' để sao lưu.", parent=self)
            return

        bk_type = self.var_bk_type.get()
        self.btn_run_backup.configure(state="disabled", text="Đang sao lưu...")

        def _worker():
            total = len(selected)
            success_cnt = 0
            for dev in selected:
                try:
                    logger.info(f"Bắt đầu sao lưu {bk_type} cho switch {dev.name}...", dev.name)
                    self.backup_service.backup_device(dev, backup_type=bk_type)
                    success_cnt += 1
                except Exception as e:
                    logger.error(f"Sao lưu thất bại trên {dev.name}: {e}", dev.name)

            self.after(0, lambda: self._on_backup_done(success_cnt, total))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_backup_done(self, success_cnt: int, total: int):
        self.btn_run_backup.configure(state="normal", text="🚀 Bắt Đầu Sao Lưu")
        self.refresh_backups_list()
        msg = f"Quá trình sao lưu hoàn tất: {success_cnt}/{total} switch thành công."
        if success_cnt == total:
            messagebox.showinfo("Sao Lưu Thành Công", msg, parent=self)
        else:
            messagebox.showwarning("Hoàn Tất Có Lỗi", msg, parent=self)

    def _start_restore_process(self):
        # Find chosen device
        device_str = self.combo_res_device.get()
        if device_str in ["(Chọn Switch)", "(Không có thiết bị)"]:
            messagebox.showwarning("Chưa chọn Switch", "Vui lòng chọn Switch đích cần khôi phục.", parent=self)
            return

        all_devices = self.get_all_devices()
        target_dev = None
        for d in all_devices:
            if f"{d.name} ({d.ip})" == device_str:
                target_dev = d
                break

        if not target_dev:
            messagebox.showerror("Lỗi", "Không tìm thấy thiết bị đã chọn.", parent=self)
            return

        backup_file = self.ent_res_file.get().strip()
        if not backup_file or not os.path.isfile(backup_file):
            messagebox.showwarning("Tệp không hợp lệ", "Vui lòng chọn một tệp cấu hình hợp lệ để khôi phục.", parent=self)
            return

        target_mode = RESTORE_TARGET_RUNNING if "running" in self.combo_res_target.get().lower() else RESTORE_TARGET_STARTUP

        # Confirm Dialog
        ConfirmDialog(
            parent=self.winfo_toplevel(),
            title="Xác nhận Khôi Phục Cấu Hình",
            message=f"Bạn sắp khôi phục cấu hình từ tệp:\n{os.path.basename(backup_file)}\n\nVào thiết bị: {target_dev.name} ({target_dev.ip})\nMục tiêu: {target_mode.upper()}-CONFIG.",
            warning_text="LƯU Ý AN TOÀN: Hệ thống sẽ TỰ ĐỘNG sao lưu Running-config hiện tại của switch này trước khi ghi đè để bạn có thể rollback khi cần!",
            on_confirm=lambda: self._execute_restore(target_dev, backup_file, target_mode)
        )

    def _execute_restore(self, device: SwitchDevice, backup_file: str, target_mode: str):
        self.btn_run_restore.configure(state="disabled", text="Đang khôi phục an toàn...")

        def _worker():
            ok, safety_path, result_msg = self.restore_service.restore_configuration(
                device=device,
                backup_file_path=backup_file,
                restore_target=target_mode,
                save_after_restore=False
            )
            self.after(0, lambda: self._on_restore_done(ok, safety_path, result_msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_restore_done(self, ok: bool, safety_path: str, result_msg: str):
        self.btn_run_restore.configure(state="normal", text="⚠️ Khôi Phục Cấu Hình An Toàn")
        self.refresh_backups_list()
        if ok:
            messagebox.showinfo(
                "Khôi Phục Thành Công",
                f"{result_msg}\n\nĐã tạo bản sao lưu an toàn trước restore tại:\n{safety_path}",
                parent=self
            )
        else:
            messagebox.showerror("Khôi Phục Thất Bại", result_msg, parent=self)
