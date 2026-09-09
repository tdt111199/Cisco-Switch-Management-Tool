"""Configuration Preview Dialog for Shutdown and Rollback scripts."""

import os
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk


class ConfigPreviewDialog(ctk.CTkToplevel):
    """Modal dialog to review generated Cisco CLI configuration scripts."""

    def __init__(self, parent, title: str, config_text: str, is_shutdown: bool = True):
        super().__init__(parent)
        self.title(title)
        self.geometry("820x620")
        self.minsize(700, 500)
        self.config_text = config_text
        self.is_shutdown = is_shutdown
        self.grab_set()

        self._create_ui()

    def _create_ui(self):
        # 1. Header Banner
        banner_bg = "#7F1D1D" if self.is_shutdown else "#065F46"
        banner_fg = "#FCA5A5" if self.is_shutdown else "#6EE7B7"
        banner_title = "⚠️ KỊCH BẢN CẤU HÌNH SHUTDOWN CỔNG (PREVIEW)" if self.is_shutdown else "🔄 KỊCH BẢN ROLLBACK (NO SHUTDOWN) (PREVIEW)"

        header = ctk.CTkFrame(self, fg_color=banner_bg, corner_radius=8)
        header.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            header,
            text=banner_title,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#FFFFFF"
        ).pack(anchor="w", padx=16, pady=(10, 4))

        sub_text = (
            "Kịch bản cấu hình được sinh tự động cho các port đủ điều kiện UNUSED.\n"
            "Ứng dụng TUYỆT ĐỐI KHÔNG tự động đẩy lệnh xuống switch. Hãy sao chép hoặc lưu file để kỹ sư review."
            if self.is_shutdown else
            "Kịch bản hoàn tác (no shutdown) để khôi phục nhanh trạng thái ban đầu cho các cổng."
        )
        ctk.CTkLabel(
            header,
            text=sub_text,
            font=ctk.CTkFont(size=11),
            text_color=banner_fg,
            justify="left"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # 2. Text Box with Scrollbar
        txt_frame = ctk.CTkFrame(self)
        txt_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.txt_content = ctk.CTkTextbox(
            txt_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none"
        )
        self.txt_content.pack(fill="both", expand=True, padx=4, pady=4)
        self.txt_content.insert("1.0", self.config_text)
        self.txt_content.configure(state="normal")

        # 3. Action Buttons
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=16, pady=(0, 16))

        btn_copy = ctk.CTkButton(
            btn_bar,
            text="📋 Sao Chép (Copy to Clipboard)",
            command=self._copy_to_clipboard,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8"
        )
        btn_copy.pack(side="left", padx=(0, 8))

        btn_save = ctk.CTkButton(
            btn_bar,
            text="💾 Lưu Ra File (.cfg / .txt)",
            command=self._save_to_file,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#059669",
            hover_color="#047857"
        )
        btn_save.pack(side="left", padx=(0, 8))

        btn_close = ctk.CTkButton(
            btn_bar,
            text="Đóng",
            fg_color="#475569",
            hover_color="#334155",
            command=self.destroy,
            width=90
        )
        btn_close.pack(side="right")

    def _copy_to_clipboard(self):
        self.clipboard_clear()
        self.clipboard_append(self.config_text)
        messagebox.showinfo("Thành Công", "Đã sao chép toàn bộ kịch bản cấu hình vào Clipboard!")

    def _save_to_file(self):
        default_name = "shutdown_unused_ports.cfg" if self.is_shutdown else "rollback_unused_ports.cfg"
        file_path = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu kịch bản cấu hình Cisco",
            initialfile=default_name,
            filetypes=[("Cisco Config (*.cfg)", "*.cfg"), ("Text Files (*.txt)", "*.txt"), ("All Files (*.*)", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.config_text)
                messagebox.showinfo("Thành Công", f"Đã lưu tệp cấu hình tại:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")
