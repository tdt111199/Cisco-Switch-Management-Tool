==============================================================================
Cisco Layer 2 Switch Manager - Standalone Executable Release
==============================================================================

This standalone executable package allows you to run the Cisco Layer 2 Switch 
Manager GUI on any 64-bit Windows computer (Windows 10 / 11) without installing 
Python or external dependencies.

How to Run:
1. Double-click CiscoL2Manager.exe to launch the application.
2. In the "Quản Lý Thiết Bị" tab, add switches or click "Nhập DS" to import 
   your switch list from Excel (.xlsx), CSV, or JSON.
3. Sample import templates are provided in the 'examples' folder.
4. Select target switches and navigate through the Layer 2 configuration tabs 
   or Backup & Restore center.

Security Note:
All credentials entered are encrypted locally using AES/Fernet encryption 
derived from the local machine hardware identifier.

For full documentation, source code, and developer instructions, refer to 
the README.md in the source/ directory.
