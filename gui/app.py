"""Main Application Window with modern sidebar navigation."""

import threading
from typing import List
import customtkinter as ctk
from core.inventory import InventoryManager, SwitchDevice
from core.logger import logger
from core.ssh_client import CiscoSSHClient
from core.task_runner import BatchTaskRunner
from gui.views.backup_restore_view import BackupRestoreView
from gui.views.cli_monitor_view import CliMonitorView
from gui.views.devices_view import DevicesView
from gui.views.l2_config_view import L2ConfigView
from gui.views.logs_view import LogsView
from services.backup_service import BackupService
from services.restore_service import RestoreService


class CiscoL2ManagerApp(ctk.CTk):
    """Main Application GUI Window for Cisco Layer 2 Switch Manager."""

    def __init__(self):
        super().__init__()

        # Window properties
        self.title("Cisco Layer 2 Switch Manager v1.0 — Quản Trị Switch Cisco Chuyên Nghiệp")
        self.geometry("1260x820")
        self.minsize(1050, 680)

        # Set appearance theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize Services & Core components
        self.inventory = InventoryManager()
        self.backup_service = BackupService()
        self.restore_service = RestoreService(self.backup_service)
        self.task_runner = BatchTaskRunner(max_workers=6)

        # Build Main Layout
        self._create_layout()

        # Initial selection state update
        self._on_devices_selection_changed(self.view_devices.get_selected_devices())
        logger.info("Ứng dụng Cisco Layer 2 Switch Manager đã sẵn sàng.")

    def _create_layout(self):
        # Main layout grid: 1 row, 2 columns (Sidebar and Content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 1. Left Sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo / App Title
        lbl_brand = ctk.CTkLabel(
            self.sidebar,
            text="🌐 CISCO L2\nMANAGER",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38BDF8"
        )
        lbl_brand.pack(pady=(24, 16))

        # Nav Buttons
        self.nav_buttons = {}
        nav_items = [
            ("devices", "📋 Quản Lý Thiết Bị"),
            ("l2_config", "⚙️ Cấu Hình Layer 2"),
            ("backup_restore", "💾 Sao Lưu & Restore"),
            ("cli_monitor", "💻 Tra Cứu CLI & Lệnh"),
            ("logs", "📜 Nhật Ký & Tiến Độ"),
        ]

        for key, text in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                height=40,
                corner_radius=6,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("#3B82F6", "#1E40AF"),
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda k=key: self._switch_view(k)
            )
            btn.pack(fill="x", padx=12, pady=4)
            self.nav_buttons[key] = btn

        # Bottom sidebar controls: Theme toggle
        self.sidebar_bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.sidebar_bottom.pack(side="bottom", fill="x", padx=12, pady=16)

        ctk.CTkLabel(self.sidebar_bottom, text="Giao diện:", anchor="w", font=ctk.CTkFont(size=11)).pack(anchor="w")
        self.combo_theme = ctk.CTkComboBox(
            self.sidebar_bottom,
            values=["Dark", "Light", "System"],
            command=lambda m: ctk.set_appearance_mode(m.lower())
        )
        self.combo_theme.set("Dark")
        self.combo_theme.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(
            self.sidebar_bottom,
            text="Phiên bản 1.0.0\nChạy độc lập trên Windows",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="left"
        ).pack(anchor="w")

        # 2. Main Content Area (Stack of Views)
        self.content_area = ctk.CTkFrame(self, fg_color="transparent")
        self.content_area.grid(row=0, column=1, sticky="nsew")

        # Instantiate all Views
        self.view_devices = DevicesView(
            self.content_area,
            inventory=self.inventory,
            on_selection_changed=self._on_devices_selection_changed
        )
        self.view_l2_config = L2ConfigView(
            self.content_area,
            get_selected_devices_cb=self.view_devices.get_selected_devices,
            execute_batch_cb=self.execute_batch_commands
        )
        self.view_backup_restore = BackupRestoreView(
            self.content_area,
            backup_service=self.backup_service,
            restore_service=self.restore_service,
            get_selected_devices_cb=self.view_devices.get_selected_devices,
            get_all_devices_cb=self.inventory.get_all
        )
        self.view_cli_monitor = CliMonitorView(
            self.content_area,
            get_selected_devices_cb=self.view_devices.get_selected_devices
        )
        self.view_logs = LogsView(self.content_area)

        self.views = {
            "devices": self.view_devices,
            "l2_config": self.view_l2_config,
            "backup_restore": self.view_backup_restore,
            "cli_monitor": self.view_cli_monitor,
            "logs": self.view_logs,
        }

        # Show initial view
        self._switch_view("devices")

    def _switch_view(self, key: str):
        """Display selected view and update sidebar button highlight."""
        for k, v in self.views.items():
            if k == key:
                v.pack(fill="both", expand=True)
                self.nav_buttons[k].configure(fg_color="#2563EB", text_color="white")
            else:
                v.pack_forget()
                self.nav_buttons[k].configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def _on_devices_selection_changed(self, selected_devices: List[SwitchDevice]):
        """Callback when switch checkboxes change in DevicesView."""
        self.view_l2_config.update_selected_devices_display(selected_devices)
        self.view_backup_restore.update_selected_devices_display(selected_devices)
        self.view_cli_monitor.update_selected_devices_display(selected_devices)

    def execute_batch_commands(self, commands: List[str]):
        """Executes a list of configuration commands across selected switches in background threads."""
        selected = self.view_devices.get_selected_devices()
        if not selected:
            return

        # Prepare Logs View for batch execution
        self.view_logs.init_batch_devices(selected)
        # Automatically switch to logs view so user sees progress
        self._switch_view("logs")

        def _task_worker(device: SwitchDevice) -> str:
            with CiscoSSHClient(device) as client:
                output = client.send_config_set(commands)
                # Auto save running to startup
                client.save_running_to_startup()
                return output

        def _run():
            self.task_runner.run_batch(
                devices=selected,
                task_func=_task_worker,
                on_status_change=self.view_logs.update_device_result,
                on_all_complete=self.view_logs.finish_batch
            )

        threading.Thread(target=_run, daemon=True).start()
