"""Thread-safe logging system with real-time GUI callback listeners."""

import logging
import os
import queue
import sys
from datetime import datetime
from typing import Callable, List, Optional

LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_SUCCESS = "SUCCESS"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"


class LogMessage:
    """Represents a structured log entry."""
    def __init__(self, message: str, level: str = LOG_LEVEL_INFO, device_name: str = ""):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.level = level
        self.device_name = device_name
        self.message = message

    def formatted(self) -> str:
        dev_tag = f"[{self.device_name}] " if self.device_name else ""
        return f"[{self.timestamp}] [{self.level}] {dev_tag}{self.message}"


class AppLogger:
    """Singleton-style logger with multi-sink output and GUI callback integration."""
    _instance: Optional["AppLogger"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppLogger, cls).__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        self.listeners: List[Callable[[LogMessage], None]] = []
        self.log_file = "data/app.log"
        os.makedirs(os.path.dirname(os.path.abspath(self.log_file)), exist_ok=True)

    def add_listener(self, callback: Callable[[LogMessage], None]) -> None:
        """Add a callback to receive real-time log messages."""
        if callback not in self.listeners:
            self.listeners.append(callback)

    def remove_listener(self, callback: Callable[[LogMessage], None]) -> None:
        """Remove a callback."""
        if callback in self.listeners:
            self.listeners.remove(callback)

    def log(self, message: str, level: str = LOG_LEVEL_INFO, device_name: str = "") -> None:
        """Log a message to file, console, and dispatch to GUI listeners."""
        entry = LogMessage(message, level, device_name)
        line = entry.formatted()

        # Print safely to stdout/stderr avoiding Windows cp1252 crash
        try:
            print(line)
        except UnicodeEncodeError:
            try:
                sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
                sys.stdout.buffer.flush()
            except Exception:
                pass

        # Append to log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

        # Dispatch to listeners
        for listener in self.listeners:
            try:
                listener(entry)
            except Exception:
                pass

    def info(self, message: str, device_name: str = "") -> None:
        self.log(message, LOG_LEVEL_INFO, device_name)

    def success(self, message: str, device_name: str = "") -> None:
        self.log(message, LOG_LEVEL_SUCCESS, device_name)

    def warning(self, message: str, device_name: str = "") -> None:
        self.log(message, LOG_LEVEL_WARNING, device_name)

    def error(self, message: str, device_name: str = "") -> None:
        self.log(message, LOG_LEVEL_ERROR, device_name)


logger = AppLogger()
