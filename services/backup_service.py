"""Service for backing up running-config and startup-config of Cisco switches."""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from core.inventory import SwitchDevice
from core.logger import logger
from core.ssh_client import CiscoSSHClient

BACKUP_TYPE_RUNNING = "running"
BACKUP_TYPE_STARTUP = "startup"
BACKUP_TYPE_BOTH = "both"


class BackupService:
    """Handles single and batch backup operations."""

    def __init__(self, backup_root_dir: str = "backups"):
        self.backup_root_dir = backup_root_dir
        os.makedirs(self.backup_root_dir, exist_ok=True)

    def _sanitize_folder_name(self, name: str) -> str:
        """Create a safe folder name."""
        return re.sub(r'[\/:*?"<>| ]', '_', name)

    def backup_device(
        self,
        device: SwitchDevice,
        backup_type: str = BACKUP_TYPE_BOTH
    ) -> Dict[str, str]:
        """
        Backs up configuration for a single device.
        backup_type can be 'running', 'startup', or 'both'.
        Returns dict of {type: file_path}.
        """
        saved_files = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = self._sanitize_folder_name(f"{device.name}_{device.ip}")
        target_dir = os.path.join(self.backup_root_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        with CiscoSSHClient(device) as client:
            if backup_type in [BACKUP_TYPE_RUNNING, BACKUP_TYPE_BOTH]:
                logger.info("Đang lấy Running-config...", device.name)
                running_cfg = client.send_command("show running-config", read_timeout=60)
                file_name = f"running_config_{timestamp}.cfg"
                file_path = os.path.join(target_dir, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(running_cfg)
                saved_files[BACKUP_TYPE_RUNNING] = file_path
                logger.success(f"Đã lưu Running-config vào: {file_path}", device.name)

            if backup_type in [BACKUP_TYPE_STARTUP, BACKUP_TYPE_BOTH]:
                logger.info("Đang lấy Startup-config...", device.name)
                startup_cfg = client.send_command("show startup-config", read_timeout=60)
                file_name = f"startup_config_{timestamp}.cfg"
                file_path = os.path.join(target_dir, file_name)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(startup_cfg)
                saved_files[BACKUP_TYPE_STARTUP] = file_path
                logger.success(f"Đã lưu Startup-config vào: {file_path}", device.name)

        return saved_files

    def list_backups(self) -> List[Dict[str, str]]:
        """List all existing backup files."""
        backup_records = []
        if not os.path.exists(self.backup_root_dir):
            return backup_records

        for root, _, files in os.walk(self.backup_root_dir):
            for file in files:
                if file.endswith(".cfg") or file.endswith(".txt"):
                    full_path = os.path.join(root, file)
                    stat = os.stat(full_path)
                    folder_name = os.path.basename(root)
                    cfg_type = "Running-config" if "running" in file.lower() else "Startup-config"
                    mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    backup_records.append({
                        "device_folder": folder_name,
                        "file_name": file,
                        "file_path": full_path,
                        "type": cfg_type,
                        "size_bytes": f"{stat.st_size} B",
                        "modified_at": mod_time,
                    })

        # Sort newest first
        backup_records.sort(key=lambda x: x["modified_at"], reverse=True)
        return backup_records
