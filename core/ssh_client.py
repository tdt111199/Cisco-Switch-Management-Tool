"""SSH Client wrapper for Cisco switches powered by Netmiko."""

import socket
import time
from typing import Dict, List, Optional, Tuple
from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)
from core.inventory import SwitchDevice
from core.logger import logger


class SSHConnectionError(Exception):
    """Custom exception for SSH connection failures."""
    pass


class CiscoSSHClient:
    """Manages an SSH session with a Cisco IOS switch."""

    def __init__(self, device: SwitchDevice, timeout: int = 15):
        self.device = device
        self.timeout = timeout
        self.connection = None

    def connect(self) -> None:
        """Establish SSH connection and enter enable mode."""
        conn_params = self.device.to_netmiko_dict()
        conn_params["conn_timeout"] = self.timeout
        conn_params["auth_timeout"] = self.timeout

        logger.info(f"Đang kết nối SSH tới {self.device.name} ({self.device.ip}:{self.device.port})...", self.device.name)

        try:
            self.connection = ConnectHandler(**conn_params)
            # Enter enable mode if not already
            if not self.connection.check_enable_mode():
                self.connection.enable()
            logger.success(f"Kết nối SSH thành công tới {self.device.name} (Prompt: {self.connection.find_prompt()})", self.device.name)
        except NetmikoAuthenticationException as e:
            msg = f"Xác thực thất bại (Sai username/password/enable secret): {e}"
            logger.error(msg, self.device.name)
            raise SSHConnectionError(msg)
        except NetmikoTimeoutException as e:
            msg = f"Hết thời gian chờ kết nối (Timeout): {e}"
            logger.error(msg, self.device.name)
            raise SSHConnectionError(msg)
        except Exception as e:
            msg = f"Lỗi kết nối SSH không xác định: {e}"
            logger.error(msg, self.device.name)
            raise SSHConnectionError(msg)

    def disconnect(self) -> None:
        """Gracefully close SSH connection."""
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass
            self.connection = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def send_command(self, command: str, read_timeout: int = 45) -> str:
        """Send a show/exec command and return output."""
        if not self.connection:
            raise SSHConnectionError("Chưa có kết nối SSH tới thiết bị.")
        try:
            logger.info(f"Thực thi lệnh: {command}", self.device.name)
            output = self.connection.send_command(command, read_timeout=read_timeout)
            return output
        except Exception as e:
            msg = f"Lỗi khi thực thi lệnh '{command}': {e}"
            logger.error(msg, self.device.name)
            raise e

    def send_config_set(self, config_commands: List[str]) -> str:
        """Send a list of configuration commands in config mode."""
        if not self.connection:
            raise SSHConnectionError("Chưa có kết nối SSH tới thiết bị.")
        try:
            clean_commands = [c.strip() for c in config_commands if c.strip() and not c.strip().startswith("!")]
            if not clean_commands:
                return "Không có lệnh cấu hình nào cần thực thi."

            logger.info(f"Bắt đầu áp dụng {len(clean_commands)} lệnh cấu hình...", self.device.name)
            output = self.connection.send_config_set(clean_commands)
            logger.success("Áp dụng cấu hình hoàn tất.", self.device.name)
            return output
        except Exception as e:
            msg = f"Lỗi khi áp dụng cấu hình: {e}"
            logger.error(msg, self.device.name)
            raise e

    def save_running_to_startup(self) -> str:
        """Execute 'write memory' / 'copy running-config startup-config'."""
        if not self.connection:
            raise SSHConnectionError("Chưa có kết nối SSH tới thiết bị.")
        try:
            logger.info("Đang lưu cấu hình vào startup-config (write memory)...", self.device.name)
            output = self.connection.save_config()
            logger.success("Lưu cấu hình thành công (write memory).", self.device.name)
            return output
        except Exception as e:
            logger.error(f"Lỗi khi lưu cấu hình: {e}", self.device.name)
            raise e

    def test_connection(self) -> Tuple[bool, str]:
        """Test SSH connection and retrieve device basic info."""
        try:
            self.connect()
            prompt = self.connection.find_prompt()
            version_output = self.connection.send_command("show version", read_timeout=20)
            # Extract basic IOS model and version
            first_lines = "\n".join([line.strip() for line in version_output.splitlines()[:5] if line.strip()])
            self.disconnect()
            return True, f"Kết nối OK!\nPrompt: {prompt}\nThông tin:\n{first_lines}"
        except Exception as e:
            return False, str(e)
        finally:
            self.disconnect()
