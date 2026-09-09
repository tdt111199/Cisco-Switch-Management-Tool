"""Unit tests for Core and Services modules."""

import os
import sys
import unittest

# Ensure src/ and root are in sys.path
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from core.crypto import encrypt_secret, decrypt_secret
from core.inventory import SwitchDevice, InventoryManager
from services.l2_config_builder import L2ConfigBuilder


class TestCrypto(unittest.TestCase):
    def test_encrypt_decrypt(self):
        plain = "Cisco@123456_Secure!"
        enc = encrypt_secret(plain)
        self.assertNotEqual(plain, enc)
        dec = decrypt_secret(enc)
        self.assertEqual(plain, dec)

    def test_empty_string(self):
        self.assertEqual(encrypt_secret(""), "")
        self.assertEqual(decrypt_secret(""), "")


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.test_json = "tests/test_devices.json"
        if os.path.exists(self.test_json):
            os.remove(self.test_json)
        self.inv = InventoryManager(storage_path=self.test_json)

    def tearDown(self):
        if os.path.exists(self.test_json):
            os.remove(self.test_json)

    def test_add_and_load_device(self):
        dev = SwitchDevice(
            name="SW-Core-01",
            ip="192.168.1.254",
            port=22,
            username="admin",
            password="Password123",
            secret="Secret123",
            group="Core",
        )
        self.inv.add_device(dev)
        self.assertEqual(len(self.inv.get_all()), 1)

        # Reload from storage
        inv2 = InventoryManager(storage_path=self.test_json)
        devices = inv2.get_all()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].name, "SW-Core-01")
        self.assertEqual(devices[0].password, "Password123")
        self.assertEqual(devices[0].secret, "Secret123")

    def test_validation(self):
        dev = SwitchDevice(name="", ip="invalid_ip", username="")
        errs = dev.validate()
        self.assertTrue(len(errs) >= 2)

    def test_import_excel_with_vietnamese_headers(self):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Tên Switch", "Địa chỉ IP", "Cổng", "Tài khoản", "Mật khẩu", "Nhóm", "Ghi chú"])
        ws.append(["SW-Floor2", "192.168.2.1", 22, "cisco", "Cisco@123", "Tầng 2", "Switch khu văn phòng"])
        test_excel = "tests/test_switches.xlsx"
        wb.save(test_excel)

        cnt = self.inv.import_file(test_excel)
        self.assertEqual(cnt, 1)
        imported_dev = [d for d in self.inv.get_all() if d.name == "SW-Floor2"][0]
        self.assertEqual(imported_dev.ip, "192.168.2.1")
        self.assertEqual(imported_dev.group, "Tầng 2")
        self.assertEqual(imported_dev.username, "cisco")
        self.assertEqual(imported_dev.password, "Cisco@123")

        if os.path.exists(test_excel):
            os.remove(test_excel)

    def test_import_csv_cp1252_semicolon(self):
        test_csv = "tests/test_cp1252.csv"
        # Write file with windows cp1252 encoding and semicolon delimiter
        content = "Tên Switch;Địa chỉ IP;Port;Username;Password;Nhóm\nSW-CP1252;192.168.3.1;22;admin;Pass123;Default"
        with open(test_csv, "wb") as f:
            f.write(content.encode("cp1252", errors="replace"))

        cnt = self.inv.import_file(test_csv)
        self.assertEqual(cnt, 1)
        imported_dev = [d for d in self.inv.get_all() if d.name == "SW-CP1252"][0]
        self.assertEqual(imported_dev.ip, "192.168.3.1")

        if os.path.exists(test_csv):
            os.remove(test_csv)


class TestL2ConfigBuilder(unittest.TestCase):
    def test_build_vlan(self):
        cmds = L2ConfigBuilder.build_create_vlan(10, "Sales_Dept")
        self.assertIn("vlan 10", cmds)
        self.assertIn("name Sales_Dept", cmds)
        self.assertIn("exit", cmds)

    def test_access_port(self):
        cmds = L2ConfigBuilder.build_access_port("GigabitEthernet0/1", 10, voice_vlan=100)
        self.assertIn("interface GigabitEthernet0/1", cmds)
        self.assertIn("switchport mode access", cmds)
        self.assertIn("switchport access vlan 10", cmds)
        self.assertIn("switchport voice vlan 100", cmds)

    def test_trunk_port(self):
        cmds = L2ConfigBuilder.build_trunk_port("GigabitEthernet0/24", allowed_vlans="10,20,30", native_vlan=99)
        self.assertIn("switchport trunk encapsulation dot1q", cmds)
        self.assertIn("switchport mode trunk", cmds)
        self.assertIn("switchport trunk allowed vlan 10,20,30", cmds)
        self.assertIn("switchport trunk native vlan 99", cmds)

    def test_stp_config(self):
        cmds1 = L2ConfigBuilder.build_stp_mode("rapid-pvst")
        self.assertEqual(cmds1, ["spanning-tree mode rapid-pvst"])

        cmds2 = L2ConfigBuilder.build_stp_vlan_priority("10,20", 4096)
        self.assertEqual(cmds2, ["spanning-tree vlan 10,20 priority 4096"])

        cmds3 = L2ConfigBuilder.build_portfast_bpduguard("Gi0/1-4", True, True, is_global=False)
        self.assertIn("interface range Gi0/1-4", cmds3)
        self.assertIn("spanning-tree portfast", cmds3)
        self.assertIn("spanning-tree bpduguard enable", cmds3)

    def test_etherchannel(self):
        cmds = L2ConfigBuilder.build_etherchannel("Gi0/1-2", group_id=1, mode="active")
        self.assertIn("interface range Gi0/1-2", cmds)
        self.assertIn("channel-group 1 mode active", cmds)

    def test_port_security(self):
        cmds = L2ConfigBuilder.build_port_security("Fa0/1", enable=True, max_mac=2, violation="shutdown", sticky=True)
        self.assertIn("switchport port-security", cmds)
        self.assertIn("switchport port-security maximum 2", cmds)
        self.assertIn("switchport port-security violation shutdown", cmds)
        self.assertIn("switchport port-security mac-address sticky", cmds)

    def test_dhcp_snooping_and_dai(self):
        cmds_dhcp = L2ConfigBuilder.build_dhcp_snooping(
            enable_global=True,
            vlans="10,20",
            trust_interfaces=["Gi0/24"]
        )
        self.assertIn("ip dhcp snooping", cmds_dhcp)
        self.assertIn("ip dhcp snooping vlan 10,20", cmds_dhcp)
        self.assertIn("ip dhcp snooping trust", cmds_dhcp)

        cmds_dai = L2ConfigBuilder.build_dai(vlans="10,20", trust_interfaces=["Gi0/24"])
        self.assertIn("ip arp inspection vlan 10,20", cmds_dai)
        self.assertIn("ip arp inspection trust", cmds_dai)

    def test_storm_control(self):
        cmds = L2ConfigBuilder.build_storm_control("Gi0/1", broadcast_level=20.5, multicast_level=15.0, action="shutdown")
        self.assertIn("storm-control broadcast level 20.5", cmds)
        self.assertIn("storm-control multicast level 15.0", cmds)
        self.assertIn("storm-control action shutdown", cmds)


if __name__ == "__main__":
    unittest.main()
