"""Cryptography helper for encrypting and decrypting switch credentials."""

import base64
import hashlib
import os
import platform
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _get_machine_identifier() -> bytes:
    """Derive a consistent hardware/system identifier for this host."""
    unique_str = f"{platform.node()}:{platform.machine()}:{platform.system()}:CiscoL2ManagerAppKey"
    # On Windows, try reading MachineGuid from registry if accessible
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
            0,
            winreg.KEY_READ | winreg.KEY_WOW64_64KEY
        )
        guid, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        unique_str += f":{guid}"
    except Exception:
        pass
    return unique_str.encode("utf-8")


def _get_cipher_suite(custom_key: str = None) -> Fernet:
    """Get Fernet cipher suite using machine key or custom passphrase."""
    salt = b"cisco_l2_manager_secure_salt_2026"
    passphrase = custom_key.encode("utf-8") if custom_key else _get_machine_identifier()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase))
    return Fernet(key)


def encrypt_secret(plain_text: str, custom_key: str = None) -> str:
    """Encrypt a plaintext string into a safe base64-encoded encrypted token."""
    if not plain_text:
        return ""
    try:
        cipher = _get_cipher_suite(custom_key)
        encrypted = cipher.encrypt(plain_text.encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}")


def decrypt_secret(encrypted_text: str, custom_key: str = None) -> str:
    """Decrypt an encrypted token back into plaintext string."""
    if not encrypted_text:
        return ""
    try:
        cipher = _get_cipher_suite(custom_key)
        decrypted = cipher.decrypt(encrypted_text.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        # Return empty or raise
        return ""
