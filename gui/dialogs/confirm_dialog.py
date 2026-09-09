"""Confirmation dialog for sensitive network operations."""

import customtkinter as ctk


class ConfirmDialog(ctk.CTkToplevel):
    """Modal dialog asking user to confirm critical operations."""

    def __init__(self, parent, title: str, message: str, warning_text: str = "", on_confirm=None):
        super().__init__(parent)
        self.parent = parent
        self.on_confirm = on_confirm
        self.confirmed = False

        self.title(title)
        self.geometry("480x260")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.after(10, self._center_window)
        self._create_widgets(title, message, warning_text)

    def _center_window(self):
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() - self.winfo_width()) // 2
        y = self.parent.winfo_y() + (self.parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _create_widgets(self, title: str, message: str, warning_text: str):
        pad_x = 20

        lbl_title = ctk.CTkLabel(
            self,
            text=f"⚠️ {title}",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color="#E5A93C"
        )
        lbl_title.pack(pady=(16, 8))

        lbl_msg = ctk.CTkLabel(
            self,
            text=message,
            wraplength=420,
            justify="left"
        )
        lbl_msg.pack(padx=pad_x, pady=4, fill="x")

        if warning_text:
            warning_frame = ctk.CTkFrame(self, fg_color="#3A2A1A", corner_radius=6)
            warning_frame.pack(padx=pad_x, pady=8, fill="x")
            lbl_warn = ctk.CTkLabel(
                warning_frame,
                text=warning_text,
                text_color="#FFB347",
                wraplength=400,
                justify="left",
                font=ctk.CTkFont(size=12, weight="bold")
            )
            lbl_warn.pack(padx=10, pady=8)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=pad_x, pady=(12, 16))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Hủy bỏ",
            fg_color="#555555",
            hover_color="#444444",
            width=100,
            command=self.destroy
        )
        btn_cancel.pack(side="left")

        btn_ok = ctk.CTkButton(
            btn_frame,
            text="Tôi Đồng Ý & Tiếp Tục",
            fg_color="#C0392B",
            hover_color="#962D22",
            width=160,
            command=self._do_confirm
        )
        btn_ok.pack(side="right")

    def _do_confirm(self):
        self.confirmed = True
        if self.on_confirm:
            self.on_confirm()
        self.destroy()
