"""Canvas-based Historical Trend Chart for Cisco Historical Unused Port Scanner.

Visualizes the trend of UNUSED, ACTIVE, and MONITOR ports across historical scan dates.
Self-contained, fast, and fully responsive across light/dark themes without external heavy dependencies.
"""

import tkinter as tk
from typing import List, Optional
import customtkinter as ctk

from core.scanner_models import ScanLogRecord


class HistoricalTrendChart(ctk.CTkFrame):
    """Visualizes historical port metrics over time on a Tkinter Canvas."""

    def __init__(self, master, scan_logs: Optional[List[ScanLogRecord]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.scan_logs = scan_logs or []

        self.canvas = tk.Canvas(
            self,
            bg="#1E293B",  # Dark slate background
            highlightthickness=0,
            relief="flat"
        )
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas.bind("<Configure>", lambda e: self.draw_chart())

    def set_data(self, scan_logs: List[ScanLogRecord]) -> None:
        """Update chart data and redraw."""
        self.scan_logs = scan_logs
        self.draw_chart()

    def draw_chart(self) -> None:
        """Draws the line chart on canvas."""
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w < 50 or h < 50:
            return

        if not self.scan_logs or len(self.scan_logs) < 1:
            self.canvas.create_text(
                w / 2, h / 2,
                text="Chưa có đủ dữ liệu lịch sử phiên quét để vẽ biểu đồ.\nHãy thực hiện quét ít nhất 1 phiên.",
                fill="#94A3B8",
                font=("Arial", 11),
                justify="center"
            )
            return

        # Padding
        pad_left = 60
        pad_right = 30
        pad_top = 35
        pad_bottom = 45

        chart_w = w - pad_left - pad_right
        chart_h = h - pad_top - pad_bottom

        if chart_w <= 20 or chart_h <= 20:
            return

        logs = self.scan_logs[-15:]  # Show last 15 scans maximum for clarity
        n = len(logs)

        # Find max value for Y axis
        max_val = max([max(l.unused_count, l.active_count, l.monitor_count, 1) for l in logs])
        max_y = int(max_val * 1.2) + 1  # 20% margin above max

        # Draw Grid & Y-Axis labels
        y_ticks = 4
        for i in range(y_ticks + 1):
            val = int(max_y * (i / y_ticks))
            y_pos = pad_top + chart_h - (chart_h * (val / max_y))

            # Grid line
            self.canvas.create_line(
                pad_left, y_pos, w - pad_right, y_pos,
                fill="#334155", width=1, dash=(2, 4)
            )
            # Label
            self.canvas.create_text(
                pad_left - 10, y_pos,
                text=str(val),
                fill="#94A3B8",
                font=("Arial", 9),
                anchor="e"
            )

        # Calculate X positions
        x_step = chart_w / max(n - 1, 1) if n > 1 else chart_w / 2
        x_coords = []
        for i in range(n):
            if n == 1:
                x = pad_left + chart_w / 2
            else:
                x = pad_left + i * x_step
            x_coords.append(x)

        # Plot Series: UNUSED (Red), ACTIVE (Green), MONITOR (Yellow)
        series_info = [
            ("unused", [l.unused_count for l in logs], "#EF4444", "Port UNUSED"),
            ("active", [l.active_count for l in logs], "#10B981", "Port ACTIVE"),
            ("monitor", [l.monitor_count for l in logs], "#F59E0B", "Port MONITOR"),
        ]

        for s_key, vals, col, label in series_info:
            points = []
            for i, val in enumerate(vals):
                x = x_coords[i]
                y = pad_top + chart_h - (chart_h * (val / max_y))
                points.append((x, y))

            # Draw lines
            if len(points) > 1:
                flat_pts = [coord for pt in points for coord in pt]
                self.canvas.create_line(*flat_pts, fill=col, width=2.5, smooth=True)

            # Draw points & value badges
            for idx, (x, y) in enumerate(points):
                r = 4.5
                self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="#FFFFFF", width=1.5)
                # Value label above point
                self.canvas.create_text(
                    x, y - 10,
                    text=str(vals[idx]),
                    fill=col,
                    font=("Arial", 8, "bold")
                )

        # Draw X-Axis labels (timestamps)
        for i, l in enumerate(logs):
            x = x_coords[i]
            # Format time: MM-DD HH:MM
            time_label = l.timestamp[5:16] if len(l.timestamp) >= 16 else l.timestamp
            self.canvas.create_text(
                x, pad_top + chart_h + 15,
                text=time_label,
                fill="#94A3B8",
                font=("Arial", 8),
                anchor="center"
            )

        # Draw Title and Legends
        self.canvas.create_text(
            pad_left, 16,
            text="📈 XU HƯỚNG SỬ DỤNG PORT QUA CÁC PHIÊN QUÉT (HISTORICAL SCAN TREND)",
            fill="#38BDF8",
            font=("Arial", 10, "bold"),
            anchor="w"
        )

        # Legend items
        legend_x = w - pad_right - 260
        for s_key, _, col, label in series_info:
            self.canvas.create_rectangle(legend_x, 12, legend_x + 12, 20, fill=col, outline="")
            self.canvas.create_text(
                legend_x + 16, 16,
                text=label,
                fill="#E2E8F0",
                font=("Arial", 9),
                anchor="w"
            )
            legend_x += 90
