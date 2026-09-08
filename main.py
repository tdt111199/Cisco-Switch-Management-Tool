"""Entry point for Cisco Layer 2 Switch Manager application."""

import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import CiscoL2ManagerApp


def main():
    """Start GUI application."""
    app = CiscoL2ManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
