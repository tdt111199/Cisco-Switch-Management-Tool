"""Inventory manager for Cisco switch devices with secure credential persistence."""

import csv
import ipaddress
import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional
from core.crypto import decrypt_secret, encrypt_secret


@dataclass
class SwitchDevice:
    """Model representing a Cisco Switch device."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    ip: str = ""
    port: int = 22
    username: str = ""
    password: str = ""       # Plaintext in-memory, encrypted when persisted
    secret: str = ""         # Enable secret in-memory, encrypted when persisted
    device_type: str = "cisco_ios"
    group: str = "Default"
    notes: str = ""

    def validate(self) -> List[str]:
        """Validate switch parameters and return list of validation errors."""
        errors = []
        if not self.name.strip():
            errors.append("Tên switch (Hostname) không được để trống.")
        if not self.ip.strip():
            errors.append("Địa chỉ IP không được để trống.")
        else:
            # Check if valid IPv4 or valid hostname
            try:
                ipaddress.IPv4Address(self.ip.strip())
            except ValueError:
                # Check valid hostname
                if not re.match(r"^[a-zA-Z0-9.-]+$", self.ip.strip()):
                    errors.append(f"Địa chỉ IP hoặc hostname '{self.ip}' không hợp lệ.")
        if not (1 <= self.port <= 65535):
            errors.append("Cổng SSH (Port) phải nằm trong khoảng 1 - 65535.")
        if not self.username.strip():
            errors.append("Username không được để trống.")
        return errors

    def to_netmiko_dict(self) -> dict:
        """Convert switch data to Netmiko connection parameters."""
        conn_dict = {
            "device_type": self.device_type,
            "host": self.ip.strip(),
            "port": self.port,
            "username": self.username.strip(),
            "password": self.password,
            "secret": self.secret if self.secret else self.password,
            "conn_timeout": 15,
            "auth_timeout": 15,
            "banner_timeout": 15,
            "fast_cli": False,
        }
        return conn_dict


class InventoryManager:
    """Manages the collection of switches, file persistence, import and export."""

    def __init__(self, storage_path: str = "data/devices.json"):
        self.storage_path = storage_path
        self.devices: Dict[str, SwitchDevice] = {}
        self.load()

    def get_all(self) -> List[SwitchDevice]:
        """Return list of all devices."""
        return list(self.devices.values())

    def get_by_id(self, device_id: str) -> Optional[SwitchDevice]:
        """Find device by its UUID."""
        return self.devices.get(device_id)

    def add_device(self, device: SwitchDevice) -> None:
        """Add or update a switch device."""
        errors = device.validate()
        if errors:
            raise ValueError("; ".join(errors))
        if not device.id:
            device.id = str(uuid.uuid4())
        self.devices[device.id] = device
        self.save()

    def update_device(self, device: SwitchDevice) -> None:
        """Update existing device."""
        if device.id not in self.devices:
            raise KeyError(f"Thiết bị với ID '{device.id}' không tồn tại.")
        self.add_device(device)

    def delete_device(self, device_id: str) -> bool:
        """Delete device by ID."""
        if device_id in self.devices:
            del self.devices[device_id]
            self.save()
            return True
        return False

    def get_groups(self) -> List[str]:
        """Return unique list of groups."""
        groups = set()
        for dev in self.devices.values():
            if dev.group:
                groups.add(dev.group)
        return sorted(list(groups)) if groups else ["Default"]

    def save(self) -> None:
        """Save devices to JSON file with encrypted passwords."""
        os.makedirs(os.path.dirname(os.path.abspath(self.storage_path)), exist_ok=True)
        serializable_list = []
        for dev in self.devices.values():
            dev_dict = asdict(dev)
            dev_dict["password"] = encrypt_secret(dev.password)
            dev_dict["secret"] = encrypt_secret(dev.secret)
            serializable_list.append(dev_dict)

        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(serializable_list, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        """Load devices from JSON file and decrypt passwords."""
        self.devices = {}
        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                item["password"] = decrypt_secret(item.get("password", ""))
                item["secret"] = decrypt_secret(item.get("secret", ""))
                dev = SwitchDevice(**item)
                self.devices[dev.id] = dev
        except Exception as e:
            print(f"[Inventory] Lỗi khi tải dữ liệu thiết bị: {e}")

    def export_to_csv(self, file_path: str, include_credentials: bool = False) -> None:
        """Export devices to a CSV file."""
        fieldnames = ["name", "ip", "port", "device_type", "group", "notes"]
        if include_credentials:
            fieldnames.extend(["username", "password", "secret"])

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for dev in self.devices.values():
                row = {
                    "name": dev.name,
                    "ip": dev.ip,
                    "port": dev.port,
                    "device_type": dev.device_type,
                    "group": dev.group,
                    "notes": dev.notes,
                }
                if include_credentials:
                    row["username"] = dev.username
                    row["password"] = dev.password
                    row["secret"] = dev.secret
                writer.writerow(row)

    def export_to_excel(self, file_path: str, include_credentials: bool = False) -> None:
        """Export devices to an Excel (.xlsx) file."""
        try:
            import openpyxl
        except ImportError:
            raise RuntimeError("Thư viện openpyxl chưa được cài đặt.")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Cisco Switches"

        headers = ["Tên Switch", "Địa chỉ IP", "Cổng SSH", "Loại thiết bị", "Nhóm", "Ghi chú"]
        if include_credentials:
            headers.extend(["Username", "Password", "Enable Secret"])
        ws.append(headers)

        for dev in self.devices.values():
            row = [dev.name, dev.ip, dev.port, dev.device_type, dev.group, dev.notes]
            if include_credentials:
                row.extend([dev.username, dev.password, dev.secret])
            ws.append(row)

        wb.save(file_path)

    @staticmethod
    def _map_row_dict(raw_row: dict) -> dict:
        """Map raw Vietnamese or English column headers to standard field names."""
        mapped = {}
        for k, v in raw_row.items():
            if not k:
                continue
            clean_k = str(k).strip().lower()
            val = str(v).strip() if v is not None else ""

            # Name / Hostname
            if any(term in clean_k for term in ["tên", "ten", "hostname", "device", "thiết bị", "thiet bi", "switch", "name"]) and "group" not in clean_k and "nhóm" not in clean_k and "type" not in clean_k:
                if "name" not in mapped or not mapped["name"]:
                    mapped["name"] = val

            # IP Address
            elif any(term in clean_k for term in ["ip", "host", "địa chỉ", "dia chi", "address"]):
                if "ip" not in mapped or not mapped["ip"]:
                    mapped["ip"] = val

            # Port
            elif any(term in clean_k for term in ["port", "cổng", "cong"]):
                mapped["port"] = val

            # Group
            elif any(term in clean_k for term in ["group", "nhóm", "nhom", "phòng", "phong", "khu vực"]):
                mapped["group"] = val

            # Device Type
            elif any(term in clean_k for term in ["loại", "loai", "device_type", "type"]):
                mapped["device_type"] = val

            # Username
            elif any(term in clean_k for term in ["user", "tài khoản", "tai khoan"]):
                mapped["username"] = val

            # Secret (Enable password) - check before general password
            elif any(term in clean_k for term in ["secret", "enable secret", "enable_secret", "enable pass", "mật khẩu enable"]):
                mapped["secret"] = val

            # Password
            elif any(term in clean_k for term in ["pass", "mật khẩu", "mat khau", "pwd"]):
                mapped["password"] = val

            # Notes
            elif any(term in clean_k for term in ["note", "ghi chú", "ghi chu", "mô tả", "mo ta", "desc"]):
                mapped["notes"] = val

        return mapped

    def import_from_excel(self, file_path: str) -> int:
        """Import switch devices from Excel (.xlsx/.xls) file."""
        try:
            import openpyxl
        except ImportError:
            raise RuntimeError("Cần thư viện openpyxl để đọc tệp Excel.")

        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return 0

        header_row = [str(c).strip() if c is not None else "" for c in rows[0]]
        count = 0

        for row_vals in rows[1:]:
            if not any(row_vals):
                continue
            raw_row = {}
            for col_idx, col_name in enumerate(header_row):
                if col_idx < len(row_vals):
                    raw_row[col_name] = row_vals[col_idx]

            mapped = self._map_row_dict(raw_row)
            name = mapped.get("name", "").strip()
            ip = mapped.get("ip", "").strip()
            if not name or not ip:
                continue

            try:
                port = int(mapped.get("port", 22) or 22)
            except ValueError:
                port = 22

            device = SwitchDevice(
                name=name,
                ip=ip,
                port=port,
                username=mapped.get("username", "admin").strip() or "admin",
                password=mapped.get("password", ""),
                secret=mapped.get("secret", ""),
                device_type=mapped.get("device_type", "cisco_ios").strip() or "cisco_ios",
                group=mapped.get("group", "Default").strip() or "Default",
                notes=mapped.get("notes", "").strip(),
            )
            self.add_device(device)
            count += 1

        return count

    def import_from_csv(self, file_path: str) -> int:
        """Import devices from a CSV or text file with auto encoding & delimiter detection."""
        encodings = ["utf-8-sig", "utf-8", "cp1258", "cp1252", "latin-1"]
        content = None

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

        # Determine delimiter: comma, semicolon, tab, pipe
        first_line = content.splitlines()[0] if content.splitlines() else ""
        delimiter = ","
        for d in [";", "\t", "|", ","]:
            if d in first_line:
                delimiter = d
                break

        import io
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        count = 0

        for raw_row in reader:
            mapped = self._map_row_dict(raw_row)
            name = mapped.get("name", "").strip()
            ip = mapped.get("ip", "").strip()
            if not name or not ip:
                continue

            try:
                port = int(mapped.get("port", 22) or 22)
            except ValueError:
                port = 22

            device = SwitchDevice(
                name=name,
                ip=ip,
                port=port,
                username=mapped.get("username", "admin").strip() or "admin",
                password=mapped.get("password", ""),
                secret=mapped.get("secret", ""),
                device_type=mapped.get("device_type", "cisco_ios").strip() or "cisco_ios",
                group=mapped.get("group", "Default").strip() or "Default",
                notes=mapped.get("notes", "").strip(),
            )
            self.add_device(device)
            count += 1

        return count

    def export_to_json(self, file_path: str, include_credentials: bool = True) -> None:
        """Export devices to JSON file."""
        export_list = []
        for dev in self.devices.values():
            dev_dict = asdict(dev)
            if not include_credentials:
                dev_dict["password"] = ""
                dev_dict["secret"] = ""
            export_list.append(dev_dict)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(export_list, f, indent=2, ensure_ascii=False)

    def import_from_json(self, file_path: str) -> int:
        """Import devices from JSON file. Returns number of devices imported."""
        count = 0
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
        data = None
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    data = json.load(f)
                break
            except Exception:
                continue

        if data is None:
            raise ValueError("Không thể đọc tệp JSON (sai định dạng hoặc mã hóa).")

        for item in data:
            mapped = self._map_row_dict(item)
            name = mapped.get("name", item.get("name", "")).strip()
            ip = mapped.get("ip", item.get("ip", "")).strip()
            if not name or not ip:
                continue

            try:
                port = int(mapped.get("port", item.get("port", 22)) or 22)
            except ValueError:
                port = 22

            device = SwitchDevice(
                name=name,
                ip=ip,
                port=port,
                username=mapped.get("username", item.get("username", "admin")).strip() or "admin",
                password=mapped.get("password", item.get("password", "")),
                secret=mapped.get("secret", item.get("secret", "")),
                device_type=mapped.get("device_type", item.get("device_type", "cisco_ios")).strip() or "cisco_ios",
                group=mapped.get("group", item.get("group", "Default")).strip() or "Default",
                notes=mapped.get("notes", item.get("notes", "")).strip(),
            )
            self.add_device(device)
            count += 1
        return count

    def import_file(self, file_path: str) -> int:
        """
        Universal import method: Auto-detects Excel (.xlsx/.xls), CSV, or JSON.
        Inspects file signature (magic bytes) to handle misnamed files.
        """
        # Read first few bytes to check if it's an Excel/ZIP archive (starts with PK\x03\x04)
        is_zip = False
        try:
            with open(file_path, "rb") as f:
                sig = f.read(4)
                if sig == b"PK\x03\x04":
                    is_zip = True
        except Exception:
            pass

        ext = os.path.splitext(file_path)[1].lower()

        if is_zip or ext in [".xlsx", ".xlsm", ".xltx", ".xls"]:
            return self.import_from_excel(file_path)
        elif ext == ".json":
            return self.import_from_json(file_path)
        else:
            return self.import_from_csv(file_path)

