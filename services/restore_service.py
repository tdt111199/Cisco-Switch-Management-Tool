"""Service for restoring configuration with mandatory pre-restore safety backup."""

import os
from datetime import datetime
from typing import Dict, List, Tuple
from core.inventory import SwitchDevice
from core.logger import logger
from core.ssh_client import CiscoSSHClient
from services.backup_service import BackupService, BACKUP_TYPE_RUNNING

RESTORE_TARGET_RUNNING = "running"
RESTORE_TARGET_STARTUP = "startup"


class RestoreService:
    """Manages safe configuration restoration to Cisco switches."""

    def __init__(self, backup_service: BackupService):
        self.backup_service = backup_service

    def restore_configuration(
        self,
        device: SwitchDevice,
        backup_file_path: str,
        restore_target: str = RESTORE_TARGET_RUNNING,
        save_after_restore: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Restores configuration from a local file to the switch.
        MANDATORY REQUIREMENT: Performs an automatic backup of the current
        running-config before applying the restore!

        Returns: (success: bool, safety_backup_path: str, output_message: str)
        """
        if not os.path.isfile(backup_file_path):
            raise FileNotFoundError(f"Tệp sao lưu không tồn tại: {backup_file_path}")

        # Step 1: Mandatory Safety Backup of current running-config
        logger.warning(
            f"BẮT ĐẦU QUY TRÌNH AN TOÀN: Tự động sao lưu Running-config hiện tại của {device.name} trước khi restore...",
            device.name
        )
        try:
            safety_backups = self.backup_service.backup_device(device, backup_type=BACKUP_TYPE_RUNNING)
            safety_backup_path = safety_backups.get(BACKUP_TYPE_RUNNING, "")
            logger.success(f"Bản sao lưu an toàn đã được tạo tại: {safety_backup_path}", device.name)
        except Exception as e:
            error_msg = f"HỦY RESTORE: Không thể tạo bản sao lưu an toàn trước khi khôi phục ({e})."
            logger.error(error_msg, device.name)
            return False, "", error_msg

        # Step 2: Read configuration file
        with open(backup_file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Filter out comments and non-command banners
        config_commands = []
        for line in lines:
            line_str = line.strip()
            # Ignore comments, end markers, empty lines
            if not line_str or line_str.startswith("!") or line_str.lower() in ["end", "exit"]:
                continue
            config_commands.append(line_str)

        if not config_commands:
            return False, safety_backup_path, "Tệp sao lưu không chứa lệnh cấu hình hợp lệ nào."

        # Step 3: Apply configuration to target
        try:
            with CiscoSSHClient(device) as client:
                if restore_target == RESTORE_TARGET_RUNNING:
                    logger.info(f"Đang nạp {len(config_commands)} dòng lệnh vào Running-config...", device.name)
                    output = client.send_config_set(config_commands)
                    if save_after_restore:
                        logger.info("Đang lưu cấu hình vào startup-config sau khi restore...", device.name)
                        client.save_running_to_startup()
                    msg = f"Đã khôi phục Running-config thành công! (Bản sao lưu trước đó: {os.path.basename(safety_backup_path)})"
                    logger.success(msg, device.name)
                    return True, safety_backup_path, f"{msg}\n\nChi tiết thực thi:\n{output}"

                elif restore_target == RESTORE_TARGET_STARTUP:
                    # To restore directly to startup config without modifying running config immediately,
                    # we can load commands into running-config and then write memory, OR transfer file.
                    # In Cisco IOS CLI, restoring directly to startup is commonly done by loading to running
                    # then copy run start, or saving config.
                    logger.info(f"Đang nạp cấu hình và lưu vào Startup-config...", device.name)
                    output = client.send_config_set(config_commands)
                    client.save_running_to_startup()
                    msg = f"Đã nạp và lưu vào Startup-config thành công! (Bản sao lưu trước đó: {os.path.basename(safety_backup_path)})"
                    logger.success(msg, device.name)
                    return True, safety_backup_path, f"{msg}\n\nChi tiết thực thi:\n{output}"

                else:
                    return False, safety_backup_path, f"Mục tiêu restore không hợp lệ: {restore_target}"

        except Exception as e:
            error_msg = f"Khôi phục cấu hình thất bại: {e}"
            logger.error(error_msg, device.name)
            return False, safety_backup_path, error_msg
