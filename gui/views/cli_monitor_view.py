"""CLI and Monitoring View for running show and custom commands."""

import threading
from tkinter import messagebox
import customtkinter as ctk
from core.inventory import SwitchDevice
from core.logger import logger
from core.ssh_client import CiscoSSHClient
from services.show_service import ShowService


class CliMonitorView(ctk.CTkFrame):
    """View allowing execution of show and custom CLI commands across switches."""

    def __init__(self, parent, get_selected_devices_cb):
        super().__init__(parent, fg_color="transparent")
        self.get_selected_devices = get_selected_devices_cb

        self._create_widgets()

    def _create_widgets(self):
        # 1. Top Control Bar: Command selection / entry
        ctrl_frame = ctk.CTkFrame(self, corner_radius=8)
        ctrl_frame.pack(fill="x", padx=10, pady=(10, 6))

        # First row: Common show commands dropdown
        r1 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(r1, text="Lệnh Show phổ biến:", width=150, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
        common_cmds = ShowService.get_common_commands()
        combo_values = [f"{cmd}  —  ({desc})" for cmd, desc in common_cmds]
        self.combo_common = ctk.CTkComboBox(
            r1,
            values=combo_values,
            width=480,
            command=self._on_common_cmd_selected
        )
        self.combo_common.set(combo_values[0])
        self.combo_common.pack(side="left", padx=(0, 10))

        btn_run_common = ctk.CTkButton(
            r1,
            text="⚡ Chạy Nhanh",
            fg_color="#0284C7",
            hover_color="#0369A1",
            width=120,
            command=self._run_current_command
        )
        btn_run_common.pack(side="left")

        # Second row: Custom command input
        r2 = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(r2, text="Lệnh CLI tùy chỉnh:", width=150, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.ent_custom_cmd = ctk.CTkEntry(r2, placeholder_text="Nhập lệnh Cisco IOS bất kỳ (VD: show int Gi0/1 switchport, show log...)", width=480)
        self.ent_custom_cmd.insert(0, "show vlan brief")
        self.ent_custom_cmd.pack(side="left", padx=(0, 10))
        self.ent_custom_cmd.bind("<Return>", lambda e: self._run_current_command())

        self.btn_run_custom = ctk.CTkButton(
            r2,
            text="▶ Thực Thi",
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            width=120,
            command=self._run_current_command
        )
        self.btn_run_custom.pack(side="left")

        # 2. Middle status banner
        self.lbl_target = ctk.CTkLabel(
            self,
            text="🎯 Mục tiêu: Đang chọn 0 switch (Hãy chọn switch ở tab Quản lý)",
            anchor="w",
            text_color="gray"
        )
        self.lbl_target.pack(fill="x", padx=14, pady=(2, 4))

        # 3. Output Console
        console_frame = ctk.CTkFrame(self, corner_radius=8)
        console_frame.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        # Console toolbar
        con_tools = ctk.CTkFrame(console_frame, fg_color="transparent")
        con_tools.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(con_tools, text="💻 Kết Quả Thực Thi (CLI Console)", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")

        btn_clear = ctk.CTkButton(con_tools, text="Xóa Console", width=90, fg_color="#475569", hover_color="#334155", command=self._clear_console)
        btn_clear.pack(side="right", padx=(6, 0))

        btn_copy = ctk.CTkButton(con_tools, text="Sao Chép", width=90, fg_color="#475569", hover_color="#334155", command=self._copy_console)
        btn_copy.pack(side="right")

        self.txt_console = ctk.CTkTextbox(
            console_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="none"
        )
        self.txt_console.pack(fill="both", expand=True, padx=10, pady=(2, 10))

    def update_selected_devices_display(self, selected_devices):
        count = len(selected_devices)
        if count == 0:
            self.lbl_target.configure(text="🎯 Mục tiêu: Chưa chọn switch nào (Chọn switch ở tab 'Quản lý Thiết bị')", text_color="#EF4444")
        elif count == 1:
            self.lbl_target.configure(text=f"🎯 Mục tiêu: 1 Switch ({selected_devices[0].name} - {selected_devices[0].ip})", text_color="#22C55E")
        else:
            self.lbl_target.configure(text=f"🎯 Mục tiêu: {count} Switch (Thực thi đồng loạt trên tất cả switch đã chọn)", text_color="#EAB308")

    def _on_common_cmd_selected(self, choice: str):
        # Extract command part before " — "
        cmd_part = choice.split("  —  ")[0].strip()
        self.ent_custom_cmd.delete(0, "end")
        self.ent_custom_cmd.insert(0, cmd_part)

    def _clear_console(self):
        self.txt_console.delete("1.0", "end")

    def _copy_console(self):
        content = self.txt_console.get("1.0", "end-1c")
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Đã sao chép", "Đã sao chép nội dung console vào clipboard.", parent=self)

    def _append_output(self, text: str):
        self.txt_console.insert("end", text + "\n")
        self.txt_console.see("end")

    def _run_current_command(self):
        cmd = self.ent_custom_cmd.get().strip()
        if not cmd:
            messagebox.showwarning("Chưa nhập lệnh", "Vui lòng nhập lệnh CLI cần thực thi.", parent=self)
            return

        selected = self.get_selected_devices()
        if not selected:
            messagebox.showwarning("Chưa chọn Switch", "Vui lòng chọn ít nhất 1 switch để thực thi lệnh.", parent=self)
            return

        self.btn_run_custom.configure(state="disabled", text="Đang chạy...")

        def _worker():
            for dev in selected:
                banner = f"\n{'='*70}\n[THIẾT BỊ: {dev.name} ({dev.ip})] - LỆNH: {cmd}\n{'='*70}\n"
                self.after(0, lambda b=banner: self._append_output(b))
                try:
                    out = ShowService.run_command(dev, cmd)
                    self.after(0, lambda o=out: self._append_output(o))
                except Exception as e:
                    err_msg = f"LỖI: {e}\n"
                    self.after(0, lambda em=err_msg: self._append_output(em))

            self.after(0, self._on_run_finished)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_run_finished(self):
        self.btn_run_custom.configure(state="normal", text="▶ Thực Thi")
