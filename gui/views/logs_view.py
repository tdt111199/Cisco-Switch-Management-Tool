"""Live Logging and Batch Device Results View."""

import os
from tkinter import filedialog, messagebox
import customtkinter as ctk
from core.logger import (
    LOG_LEVEL_ERROR,
    LOG_LEVEL_INFO,
    LOG_LEVEL_SUCCESS,
    LOG_LEVEL_WARNING,
    LogMessage,
    logger,
)
from core.task_runner import DeviceTaskResult, TaskStatus


class LogsView(ctk.CTkFrame):
    """View displaying live system logs and per-device batch task status."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.device_status_rows = {}  # {device_id: {"row": CTkFrame, "status_lbl": CTkLabel, "time_lbl": CTkLabel, "out_lbl": CTkLabel}}

        self._create_widgets()
        # Register logger listener
        logger.add_listener(self._on_new_log)

    def _create_widgets(self):
        # Top segment: Batch Task Results Table
        top_frame = ctk.CTkFrame(self, corner_radius=8)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))

        top_header = ctk.CTkFrame(top_frame, fg_color="transparent")
        top_header.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            top_header,
            text="📊 Tiến Độ & Kết Quả Từng Thiết Bị (Batch Device Monitor)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.lbl_batch_summary = ctk.CTkLabel(top_header, text="Trạng thái: Sẵn sàng", text_color="gray")
        self.lbl_batch_summary.pack(side="right")

        # Table Header
        tbl_hdr = ctk.CTkFrame(top_frame, fg_color="#2B2B2B", height=30, corner_radius=4)
        tbl_hdr.pack(fill="x", padx=10, pady=(2, 2))
        tbl_hdr.pack_propagate(False)

        ctk.CTkLabel(tbl_hdr, text="Thiết Bị", width=180, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
        ctk.CTkLabel(tbl_hdr, text="Địa Chỉ IP", width=140, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(tbl_hdr, text="Trạng Thái", width=140, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(tbl_hdr, text="Thời Gian", width=90, anchor="center", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)
        ctk.CTkLabel(tbl_hdr, text="Thông Điệp / Kết Quả", width=340, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)

        # Scrollable device status table
        self.scroll_batch = ctk.CTkScrollableFrame(top_frame, fg_color="transparent", height=160)
        self.scroll_batch.pack(fill="x", padx=8, pady=(2, 8))

        # Bottom segment: Real-time Live Log Box
        bot_frame = ctk.CTkFrame(self, corner_radius=8)
        bot_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Log toolbar
        log_bar = ctk.CTkFrame(bot_frame, fg_color="transparent")
        log_bar.pack(fill="x", padx=10, pady=(8, 4))

        ctk.CTkLabel(
            log_bar,
            text="📜 Nhật Ký Hoạt Động Thời Gian Thực (Live Logs)",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")

        self.var_autoscroll = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(log_bar, text="Tự động cuộn", variable=self.var_autoscroll).pack(side="left", padx=20)

        btn_export_log = ctk.CTkButton(log_bar, text="Xuất File Log", width=100, fg_color="#475569", hover_color="#334155", command=self._export_log)
        btn_export_log.pack(side="right", padx=(6, 0))

        btn_clear_log = ctk.CTkButton(log_bar, text="Xóa Log", width=80, fg_color="#475569", hover_color="#334155", command=self._clear_logs)
        btn_clear_log.pack(side="right")

        # Text console
        self.txt_logs = ctk.CTkTextbox(
            bot_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="none"
        )
        self.txt_logs.pack(fill="both", expand=True, padx=10, pady=(2, 10))

    def _on_new_log(self, entry: LogMessage):
        """Called by AppLogger whenever a new log message arrives."""
        line = entry.formatted() + "\n"
        self.after(0, lambda: self._insert_log_line(line, entry.level))

    def _insert_log_line(self, line: str, level: str):
        self.txt_logs.insert("end", line)
        if self.var_autoscroll.get():
            self.txt_logs.see("end")

    def _clear_logs(self):
        self.txt_logs.delete("1.0", "end")

    def _export_log(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Lưu tệp nhật ký",
            defaultextension=".log",
            filetypes=[("Log Files (*.log)", "*.log"), ("Text Files (*.txt)", "*.txt")]
        )
        if not path:
            return
        try:
            content = self.txt_logs.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Thành công", f"Đã xuất file nhật ký ra:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=self)

    # ------------------ Batch Task Tracking ------------------
    def init_batch_devices(self, devices: list):
        """Clear and initialize device rows before running a batch task."""
        for widget in self.scroll_batch.winfo_children():
            widget.destroy()
        self.device_status_rows = {}

        self.lbl_batch_summary.configure(text=f"Đang chuẩn bị chạy {len(devices)} thiết bị...", text_color="#38BDF8")

        for idx, dev in enumerate(devices):
            row_bg = "#1F1F1F" if idx % 2 == 0 else "#262626"
            row = ctk.CTkFrame(self.scroll_batch, fg_color=row_bg, height=32, corner_radius=4)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=dev.name, width=180, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=8)
            ctk.CTkLabel(row, text=dev.ip, width=140, anchor="w").pack(side="left", padx=4)

            lbl_status = ctk.CTkLabel(row, text="Chờ...", width=140, anchor="w", text_color="gray")
            lbl_status.pack(side="left", padx=4)

            lbl_time = ctk.CTkLabel(row, text="-", width=90, anchor="center", text_color="gray")
            lbl_time.pack(side="left", padx=4)

            lbl_out = ctk.CTkLabel(row, text="Đang trong hàng đợi", width=340, anchor="w", text_color="gray")
            lbl_out.pack(side="left", padx=4)

            self.device_status_rows[dev.id] = {
                "row": row,
                "status_lbl": lbl_status,
                "time_lbl": lbl_time,
                "out_lbl": lbl_out,
            }

    def update_device_result(self, result: DeviceTaskResult):
        """Called by TaskRunner whenever a device state changes."""
        self.after(0, lambda: self._apply_device_result(result))

    def _apply_device_result(self, result: DeviceTaskResult):
        dev_id = result.device.id
        if dev_id not in self.device_status_rows:
            return

        ui = self.device_status_rows[dev_id]
        status_text = result.status.value

        # Status badge color
        if result.status == TaskStatus.PENDING:
            color = "gray"
        elif result.status == TaskStatus.CONNECTING:
            color = "#38BDF8"
            status_text = "🔄 Đang kết nối..."
        elif result.status == TaskStatus.RUNNING:
            color = "#FBBF24"
            status_text = "⚙️ Đang áp dụng..."
        elif result.status == TaskStatus.SUCCESS:
            color = "#4ADE80"
            status_text = "✅ Thành công"
        elif result.status == TaskStatus.FAILED:
            color = "#F87171"
            status_text = "❌ Thất bại"
        else:
            color = "white"

        ui["status_lbl"].configure(text=status_text, text_color=color)
        ui["time_lbl"].configure(text=result.duration_str)

        msg = result.error_message if result.error_message else ("Hoàn thành cấu hình" if result.status == TaskStatus.SUCCESS else "Đang xử lý...")
        ui["out_lbl"].configure(text=msg[:60] + "..." if len(msg) > 60 else msg, text_color=color if result.status == TaskStatus.FAILED else "gray")

    def finish_batch(self, results: list):
        """Called when all batch tasks are done."""
        success_cnt = sum(1 for r in results if r.status == TaskStatus.SUCCESS)
        total = len(results)
        self.after(0, lambda: self.lbl_batch_summary.configure(
            text=f"Hoàn thành: {success_cnt}/{total} thiết bị thành công",
            text_color="#4ADE80" if success_cnt == total else "#FBBF24"
        ))
