"""Dialog for adding or editing a Cisco Switch device."""

import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from core.inventory import SwitchDevice
from core.ssh_client import CiscoSSHClient


class DeviceDialog(ctk.CTkToplevel):
    """Modal dialog for adding or editing switch properties."""

    def __init__(self, parent, device: SwitchDevice = None, groups: list = None, on_save=None):
        super().__init__(parent)
        self.parent = parent
        self.device = device
        self.groups = groups or ["Default"]
        self.on_save = on_save
        self.is_edit = device is not None

        self.title("Chỉnh sửa Switch" if self.is_edit else "Thêm Switch mới")
        self.geometry("540x620")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center dialog
        self.after(10, self._center_window)
        self._create_widgets()

    def _center_window(self):
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _create_widgets(self):
        pad_x = 24
        pad_y = 6

        # Title label
        lbl_title = ctk.CTkLabel(
            self,
            text="Thông tin Switch Cisco Layer 2",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_title.pack(pady=(16, 12))

        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=pad_x)

        # Hostname
        ctk.CTkLabel(form_frame, text="Tên Switch (Hostname):", anchor="w").grid(row=0, column=0, sticky="w", pady=pad_y)
        self.ent_name = ctk.CTkEntry(form_frame, placeholder_text="Ví dụ: SW-L2-Floor1", width=300)
        self.ent_name.grid(row=0, column=1, sticky="ew", pady=pad_y)

        # IP Address
        ctk.CTkLabel(form_frame, text="Địa chỉ IP:", anchor="w").grid(row=1, column=0, sticky="w", pady=pad_y)
        self.ent_ip = ctk.CTkEntry(form_frame, placeholder_text="192.168.1.10", width=300)
        self.ent_ip.grid(row=1, column=1, sticky="ew", pady=pad_y)

        # SSH Port
        ctk.CTkLabel(form_frame, text="Cổng SSH (Port):", anchor="w").grid(row=2, column=0, sticky="w", pady=pad_y)
        self.ent_port = ctk.CTkEntry(form_frame, placeholder_text="22", width=300)
        self.ent_port.insert(0, "22")
        self.ent_port.grid(row=2, column=1, sticky="ew", pady=pad_y)

        # Group
        ctk.CTkLabel(form_frame, text="Nhóm thiết bị:", anchor="w").grid(row=3, column=0, sticky="w", pady=pad_y)
        self.combo_group = ctk.CTkComboBox(form_frame, values=self.groups, width=300)
        self.combo_group.set("Default")
        self.combo_group.grid(row=3, column=1, sticky="ew", pady=pad_y)

        # Device Type
        ctk.CTkLabel(form_frame, text="Loại thiết bị:", anchor="w").grid(row=4, column=0, sticky="w", pady=pad_y)
        self.combo_type = ctk.CTkComboBox(form_frame, values=["cisco_ios", "cisco_xe"], width=300)
        self.combo_type.set("cisco_ios")
        self.combo_type.grid(row=4, column=1, sticky="ew", pady=pad_y)

        # Username
        ctk.CTkLabel(form_frame, text="Tài khoản (Username):", anchor="w").grid(row=5, column=0, sticky="w", pady=pad_y)
        self.ent_user = ctk.CTkEntry(form_frame, placeholder_text="admin", width=300)
        self.ent_user.grid(row=5, column=1, sticky="ew", pady=pad_y)

        # Password
        ctk.CTkLabel(form_frame, text="Mật khẩu (Password):", anchor="w").grid(row=6, column=0, sticky="w", pady=pad_y)
        pass_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        pass_frame.grid(row=6, column=1, sticky="ew", pady=pad_y)
        self.ent_pass = ctk.CTkEntry(pass_frame, show="•", width=240)
        self.ent_pass.pack(side="left", fill="x", expand=True)
        self.btn_show_pass = ctk.CTkButton(pass_frame, text="👁", width=40, command=self._toggle_pass)
        self.btn_show_pass.pack(side="right", padx=(5, 0))

        # Enable Secret
        ctk.CTkLabel(form_frame, text="Enable Secret (nếu có):", anchor="w").grid(row=7, column=0, sticky="w", pady=pad_y)
        secret_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        secret_frame.grid(row=7, column=1, sticky="ew", pady=pad_y)
        self.ent_secret = ctk.CTkEntry(secret_frame, show="•", width=240)
        self.ent_secret.pack(side="left", fill="x", expand=True)
        self.btn_show_secret = ctk.CTkButton(secret_frame, text="👁", width=40, command=self._toggle_secret)
        self.btn_show_secret.pack(side="right", padx=(5, 0))

        # Notes
        ctk.CTkLabel(form_frame, text="Ghi chú (Notes):", anchor="w").grid(row=8, column=0, sticky="w", pady=pad_y)
        self.ent_notes = ctk.CTkEntry(form_frame, placeholder_text="Vị trí tủ rack, phòng kỹ thuật...", width=300)
        self.ent_notes.grid(row=8, column=1, sticky="ew", pady=pad_y)

        # Populate if edit
        if self.device:
            self.ent_name.insert(0, self.device.name)
            self.ent_ip.insert(0, self.device.ip)
            self.ent_port.delete(0, "end")
            self.ent_port.insert(0, str(self.device.port))
            self.combo_group.set(self.device.group or "Default")
            self.combo_type.set(self.device.device_type or "cisco_ios")
            self.ent_user.insert(0, self.device.username)
            self.ent_pass.insert(0, self.device.password)
            self.ent_secret.insert(0, self.device.secret)
            self.ent_notes.insert(0, self.device.notes)

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=pad_x, pady=(12, 16))

        self.btn_test = ctk.CTkButton(
            btn_frame,
            text="⚡ Thử kết nối SSH",
            fg_color="#3B8ED0",
            hover_color="#36719F",
            command=self._test_connection
        )
        self.btn_test.pack(side="left")

        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Hủy",
            fg_color="#555555",
            hover_color="#444444",
            width=80,
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(8, 0))

        self.btn_save = ctk.CTkButton(
            btn_frame,
            text="Lưu Thiết Bị",
            fg_color="#2FA572",
            hover_color="#107C41",
            width=120,
            command=self._save_device
        )
        self.btn_save.pack(side="right")

    def _toggle_pass(self):
        current = self.ent_pass.cget("show")
        self.ent_pass.configure(show="" if current == "•" else "•")

    def _toggle_secret(self):
        current = self.ent_secret.cget("show")
        self.ent_secret.configure(show="" if current == "•" else "•")

    def _collect_device(self) -> SwitchDevice:
        try:
            port = int(self.ent_port.get().strip() or 22)
        except ValueError:
            port = 22

        dev_id = self.device.id if self.device else ""
        return SwitchDevice(
            id=dev_id,
            name=self.ent_name.get().strip(),
            ip=self.ent_ip.get().strip(),
            port=port,
            device_type=self.combo_type.get().strip() or "cisco_ios",
            group=self.combo_group.get().strip() or "Default",
            username=self.ent_user.get().strip(),
            password=self.ent_pass.get(),
            secret=self.ent_secret.get(),
            notes=self.ent_notes.get().strip(),
        )

    def _test_connection(self):
        device = self._collect_device()
        errors = device.validate()
        if errors:
            messagebox.showerror("Thông tin chưa hợp lệ", "\n".join(errors), parent=self)
            return

        self.btn_test.configure(state="disabled", text="Đang thử...")

        def _run():
            client = CiscoSSHClient(device, timeout=10)
            ok, msg = client.test_connection()
            self.after(0, lambda: self._on_test_done(ok, msg))

        threading.Thread(target=_run, daemon=True).start()

    def _on_test_done(self, ok: bool, msg: str):
        self.btn_test.configure(state="normal", text="⚡ Thử kết nối SSH")
        if ok:
            messagebox.showinfo("Kết Nối Thành Công", msg, parent=self)
        else:
            messagebox.showerror("Kết Nối Thất Bại", msg, parent=self)

    def _save_device(self):
        device = self._collect_device()
        errors = device.validate()
        if errors:
            messagebox.showerror("Lỗi dữ liệu", "\n".join(errors), parent=self)
            return
        if self.on_save:
            self.on_save(device)
        self.destroy()
