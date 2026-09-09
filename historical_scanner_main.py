"""Standalone GUI Entry Point for Cisco Historical Unused Port Scanner.

Provides a dedicated application window for scanning and historical multi-scan analysis.
"""

import os
import sys

# Ensure root directory and src/ are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import customtkinter as ctk

from core.inventory import InventoryManager
from core.logger import logger
from gui.views.historical_scanner_view import HistoricalScannerView
from services.scanner.excel_storage import ExcelStorageManager


class CiscoHistoricalScannerApp(ctk.CTk):
    """Standalone Application Window for Cisco Historical Unused Port Scanner."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Cisco Historical Unused Port Scanner v1.0 — Theo Dõi Lịch Sử Port Switch Cisco")
        self.geometry("1300x840")
        self.minsize(1080, 680)

        # Dark theme by default
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize shared components
        self.inventory = InventoryManager()
        self.storage = ExcelStorageManager()

        # Mount Historical Scanner View
        self.view = HistoricalScannerView(self, inventory=self.inventory, storage_manager=self.storage)
        self.view.pack(fill="both", expand=True)

        logger.info("Ứng dụng Cisco Historical Unused Port Scanner đã sẵn sàng.")


def main():
    app = CiscoHistoricalScannerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
