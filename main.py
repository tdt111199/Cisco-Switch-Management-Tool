"""Entry point for Cisco Layer 2 Switch Manager application."""

import os
import sys

# Ensure project root and src/ are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui.app import CiscoL2ManagerApp


def main():
    """Start GUI application."""
    app = CiscoL2ManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
