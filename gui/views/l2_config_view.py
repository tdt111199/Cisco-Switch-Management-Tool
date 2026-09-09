"""Layer 2 Configuration View with tabs for all L2 features."""

import threading
from tkinter import messagebox
import customtkinter as ctk
from core.inventory import SwitchDevice
from core.logger import logger
from core.ssh_client import CiscoSSHClient
from services.l2_config_builder import L2ConfigBuilder


class L2ConfigView(ctk.CTkFrame):
    """View containing configuration forms for all Layer 2 features."""

    def __init__(self, parent, get_selected_devices_cb, execute_batch_cb):
        super().__init__(parent, fg_color="transparent")
        self.get_selected_devices = get_selected_devices_cb
        self.execute_batch = execute_batch_cb

        self._create_widgets()

    def _create_widgets(self):
        # Header banner showing selected switch info
        self.header_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=6, height=42)
        self.header_frame.pack(fill="x", padx=10, pady=(10, 5))
        self.header_frame.pack_propagate(False)

        self.lbl_selected_info = ctk.CTkLabel(
            self.header_frame,
            text="🎯 Mục tiêu: Chưa chọn switch nào (Hãy chọn switch ở tab 'Quản lý Thiết bị')",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#38BDF8"
        )
        self.lbl_selected_info.pack(side="left", padx=14)

        # Tabview for all L2 features
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Add tabs
        tab_vlan = self.tabs.add("VLAN")
        tab_port = self.tabs.add("Access / Trunk")
        tab_stp = self.tabs.add("STP / BPDU")
        tab_ether = self.tabs.add("EtherChannel")
        tab_sec = self.tabs.add("Port Security")
        tab_dhcp = self.tabs.add("DHCP Snooping & DAI")
        tab_storm = self.tabs.add("Storm Control & Port")
        tab_mac = self.tabs.add("MAC Table")

        # Build each tab UI
        self._build_vlan_tab(tab_vlan)
        self._build_port_tab(tab_port)
        self._build_stp_tab(tab_stp)
        self._build_etherchannel_tab(tab_ether)
        self._build_port_security_tab(tab_sec)
        self._build_dhcp_dai_tab(tab_dhcp)
        self._build_storm_tab(tab_storm)
        self._build_mac_tab(tab_mac)

    def update_selected_devices_display(self, selected_devices):
        """Update header info about selected devices."""
        count = len(selected_devices)
        if count == 0:
            txt = "🎯 Mục tiêu: Chưa chọn switch nào (Hãy chọn switch ở tab 'Quản lý Thiết bị')"
            color = "#F87171"
        elif count == 1:
            txt = f"🎯 Mục tiêu: 1 Switch được chọn: {selected_devices[0].name} ({selected_devices[0].ip})"
            color = "#4ADE80"
        else:
            txt = f"🎯 Mục tiêu: {count} Switch được chọn (Cấu hình HÀNG LOẠT: {', '.join([d.name for d in selected_devices[:3]])}...)"
            color = "#FBBF24"
        self.lbl_selected_info.configure(text=txt, text_color=color)

    # ------------------ Preview / Apply Helper ------------------
    def _render_action_bar(self, parent_tab, get_commands_cb):
        """Standard action footer with 'Preview CLI' and 'Apply' buttons."""
        bar = ctk.CTkFrame(parent_tab, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=(15, 5), side="bottom")

        btn_preview = ctk.CTkButton(
            bar,
            text="👁 Xem Trước Lệnh CLI",
            fg_color="#475569",
            hover_color="#334155",
            width=160,
            command=lambda: self._show_preview_dialog(get_commands_cb())
        )
        btn_preview.pack(side="left")

        btn_apply = ctk.CTkButton(
            bar,
            text="🚀 Áp Dụng Lệnh Cấu Hình",
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            width=180,
            command=lambda: self._apply_commands(get_commands_cb())
        )
        btn_apply.pack(side="right")

    def _show_preview_dialog(self, commands):
        if not commands:
            messagebox.showwarning("Thông báo", "Không có lệnh nào được tạo. Vui lòng kiểm tra lại thông số.", parent=self)
            return

        preview_win = ctk.CTkToplevel(self.winfo_toplevel())
        preview_win.title("Xem trước lệnh CLI (Cisco IOS)")
        preview_win.geometry("520x400")
        preview_win.transient(self.winfo_toplevel())

        lbl = ctk.CTkLabel(preview_win, text="Các lệnh Cisco IOS sẽ được thực thi:", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(padx=16, pady=(14, 6), anchor="w")

        txt = ctk.CTkTextbox(preview_win, font=ctk.CTkFont(family="Consolas", size=12))
        txt.pack(fill="both", expand=True, padx=16, pady=8)
        txt.insert("1.0", "\n".join(commands))
        txt.configure(state="disabled")

        btn_close = ctk.CTkButton(preview_win, text="Đóng", width=80, command=preview_win.destroy)
        btn_close.pack(pady=(0, 14))

    def _apply_commands(self, commands):
        if not commands:
            messagebox.showwarning("Thông báo", "Không có lệnh nào được tạo.", parent=self)
            return

        selected = self.get_selected_devices()
        if not selected:
            messagebox.showwarning("Chưa chọn Switch", "Vui lòng chọn ít nhất 1 switch ở tab 'Quản lý Thiết bị' để áp dụng.", parent=self)
            return

        names = ", ".join([d.name for d in selected[:4]])
        if len(selected) > 4:
            names += f" và {len(selected) - 4} switch khác"

        confirm_msg = f"Bạn có chắc muốn áp dụng {len(commands)} lệnh cấu hình tới {len(selected)} switch sau đây?\n{names}"
        if not messagebox.askyesno("Xác nhận áp dụng", confirm_msg, parent=self):
            return

        # Delegate execution to app's batch runner
        self.execute_batch(commands)

    # ------------------ 1. VLAN TAB ------------------
    def _build_vlan_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Create VLAN section
        grp_create = ctk.CTkFrame(container)
        grp_create.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_create, text="Tạo / Sửa VLAN", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f1 = ctk.CTkFrame(grp_create, fg_color="transparent")
        f1.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f1, text="VLAN ID (1-4094):", width=140, anchor="w").pack(side="left")
        self.ent_vlan_id = ctk.CTkEntry(f1, placeholder_text="Ví dụ: 10", width=120)
        self.ent_vlan_id.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f1, text="Tên VLAN (Name):", width=120, anchor="w").pack(side="left")
        self.ent_vlan_name = ctk.CTkEntry(f1, placeholder_text="Ví dụ: IT_Department", width=200)
        self.ent_vlan_name.pack(side="left")

        # Delete VLAN section
        grp_del = ctk.CTkFrame(container)
        grp_del.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_del, text="Xóa VLAN", font=ctk.CTkFont(weight="bold"), text_color="#EF4444").pack(anchor="w", padx=10, pady=(8, 4))

        f2 = ctk.CTkFrame(grp_del, fg_color="transparent")
        f2.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f2, text="VLAN ID cần xóa:", width=140, anchor="w").pack(side="left")
        self.ent_del_vlan_id = ctk.CTkEntry(f2, placeholder_text="Ví dụ: 20", width=120)
        self.ent_del_vlan_id.pack(side="left")

        def _get_cmds():
            cmds = []
            create_id = self.ent_vlan_id.get().strip()
            if create_id:
                cmds.extend(L2ConfigBuilder.build_create_vlan(int(create_id), self.ent_vlan_name.get().strip()))
            del_id = self.ent_del_vlan_id.get().strip()
            if del_id:
                cmds.extend(L2ConfigBuilder.build_delete_vlan(int(del_id)))
            return cmds

        self._render_action_bar(tab, _get_cmds)

    # ------------------ 2. ACCESS / TRUNK TAB ------------------
    def _build_port_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        grp = ctk.CTkFrame(container)
        grp.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp, text="Cấu hình Switchport (Access / Trunk)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        # Interface input
        f_int = ctk.CTkFrame(grp, fg_color="transparent")
        f_int.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_int, text="Interface / Dải cổng:", width=150, anchor="w").pack(side="left")
        self.ent_port_int = ctk.CTkEntry(f_int, placeholder_text="Gi0/1 hoặc Gi0/1-4, Gi0/10", width=260)
        self.ent_port_int.pack(side="left")

        # Mode Selection
        f_mode = ctk.CTkFrame(grp, fg_color="transparent")
        f_mode.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_mode, text="Chế độ (Port Mode):", width=150, anchor="w").pack(side="left")
        self.var_port_mode = ctk.StringVar(value="access")
        ctk.CTkRadioButton(f_mode, text="Access Mode", variable=self.var_port_mode, value="access").pack(side="left", padx=(0, 20))
        ctk.CTkRadioButton(f_mode, text="Trunk Mode", variable=self.var_port_mode, value="trunk").pack(side="left")

        # Access parameters
        grp_acc = ctk.CTkFrame(container)
        grp_acc.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_acc, text="Thông số Chế độ Access", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_acc = ctk.CTkFrame(grp_acc, fg_color="transparent")
        f_acc.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_acc, text="Access VLAN ID:", width=150, anchor="w").pack(side="left")
        self.ent_acc_vlan = ctk.CTkEntry(f_acc, placeholder_text="Ví dụ: 10", width=120)
        self.ent_acc_vlan.pack(side="left", padx=(0, 20))
        ctk.CTkLabel(f_acc, text="Voice VLAN (tùy chọn):", width=150, anchor="w").pack(side="left")
        self.ent_voice_vlan = ctk.CTkEntry(f_acc, placeholder_text="Ví dụ: 100", width=120)
        self.ent_voice_vlan.pack(side="left")

        # Trunk parameters
        grp_trk = ctk.CTkFrame(container)
        grp_trk.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_trk, text="Thông số Chế độ Trunk", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_trk1 = ctk.CTkFrame(grp_trk, fg_color="transparent")
        f_trk1.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_trk1, text="Allowed VLANs:", width=150, anchor="w").pack(side="left")
        self.ent_trk_allowed = ctk.CTkEntry(f_trk1, placeholder_text="all, hoặc 10,20,30, hoặc add 40", width=260)
        self.ent_trk_allowed.insert(0, "all")
        self.ent_trk_allowed.pack(side="left")

        f_trk2 = ctk.CTkFrame(grp_trk, fg_color="transparent")
        f_trk2.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_trk2, text="Native VLAN ID:", width=150, anchor="w").pack(side="left")
        self.ent_trk_native = ctk.CTkEntry(f_trk2, placeholder_text="Mặc định: 1 hoặc tùy chọn (VD: 99)", width=120)
        self.ent_trk_native.pack(side="left")

        def _get_cmds():
            intf = self.ent_port_int.get().strip()
            if not intf:
                raise ValueError("Vui lòng nhập Interface hoặc dải cổng.")
            mode = self.var_port_mode.get()
            if mode == "access":
                vlan = int(self.ent_acc_vlan.get().strip())
                voice = int(self.ent_voice_vlan.get().strip()) if self.ent_voice_vlan.get().strip() else None
                return L2ConfigBuilder.build_access_port(intf, vlan, voice)
            else:
                allowed = self.ent_trk_allowed.get().strip() or "all"
                native = int(self.ent_trk_native.get().strip()) if self.ent_trk_native.get().strip() else None
                return L2ConfigBuilder.build_trunk_port(intf, allowed_vlans=allowed, native_vlan=native)

        self._render_action_bar(tab, _get_cmds)

    # ------------------ 3. STP / BPDU TAB ------------------
    def _build_stp_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # STP Mode
        grp_mode = ctk.CTkFrame(container)
        grp_mode.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_mode, text="Chế độ Spanning-Tree", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_mode = ctk.CTkFrame(grp_mode, fg_color="transparent")
        f_mode.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_mode, text="STP Mode:", width=150, anchor="w").pack(side="left")
        self.combo_stp_mode = ctk.CTkComboBox(f_mode, values=["Không đổi", "rapid-pvst", "pvst", "mst"], width=160)
        self.combo_stp_mode.set("rapid-pvst")
        self.combo_stp_mode.pack(side="left")

        # STP Priority / Root Role
        grp_prio = ctk.CTkFrame(container)
        grp_prio.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_prio, text="STP Root & Priority theo VLAN", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_vlan = ctk.CTkFrame(grp_prio, fg_color="transparent")
        f_vlan.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_vlan, text="VLAN (dải hoặc list):", width=150, anchor="w").pack(side="left")
        self.ent_stp_vlan = ctk.CTkEntry(f_vlan, placeholder_text="1,10-20", width=160)
        self.ent_stp_vlan.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f_vlan, text="Root Role:", width=80, anchor="w").pack(side="left")
        self.combo_stp_root = ctk.CTkComboBox(f_vlan, values=["(Không set)", "primary", "secondary"], width=140)
        self.combo_stp_root.set("(Không set)")
        self.combo_stp_root.pack(side="left")

        f_prio2 = ctk.CTkFrame(grp_prio, fg_color="transparent")
        f_prio2.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_prio2, text="Hoặc Set Priority (bội số 4096):", width=220, anchor="w").pack(side="left")
        self.combo_stp_prio = ctk.CTkComboBox(
            f_prio2,
            values=["(Không set)", "0", "4096", "8192", "12288", "16384", "20480", "24576", "28672", "32768", "61440"],
            width=140
        )
        self.combo_stp_prio.set("(Không set)")
        self.combo_stp_prio.pack(side="left")

        # PortFast & BPDU Guard
        grp_pf = ctk.CTkFrame(container)
        grp_pf.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_pf, text="PortFast & BPDU Guard", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_pf_scope = ctk.CTkFrame(grp_pf, fg_color="transparent")
        f_pf_scope.pack(fill="x", padx=10, pady=6)
        self.var_pf_global = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_pf_scope, text="Cấu hình PortFast & BPDU Guard TOÀN CỤC (Global)", variable=self.var_pf_global).pack(side="left")

        f_pf_int = ctk.CTkFrame(grp_pf, fg_color="transparent")
        f_pf_int.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_pf_int, text="Interface (nếu cấu hình cổng):", width=180, anchor="w").pack(side="left")
        self.ent_pf_int = ctk.CTkEntry(f_pf_int, placeholder_text="Gi0/1-10", width=200)
        self.ent_pf_int.pack(side="left")

        f_pf_chk = ctk.CTkFrame(grp_pf, fg_color="transparent")
        f_pf_chk.pack(fill="x", padx=10, pady=6)
        self.var_pf_en = ctk.BooleanVar(value=True)
        self.var_bpdu_en = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f_pf_chk, text="Bật PortFast", variable=self.var_pf_en).pack(side="left", padx=(0, 20))
        ctk.CTkCheckBox(f_pf_chk, text="Bật BPDU Guard", variable=self.var_bpdu_en).pack(side="left")

        def _get_cmds():
            cmds = []
            stp_mode = self.combo_stp_mode.get()
            if stp_mode != "Không đổi":
                cmds.extend(L2ConfigBuilder.build_stp_mode(stp_mode))

            vlan = self.ent_stp_vlan.get().strip()
            root_role = self.combo_stp_root.get()
            prio_val = self.combo_stp_prio.get()
            if vlan:
                if root_role != "(Không set)":
                    cmds.extend(L2ConfigBuilder.build_stp_root(vlan, root_role))
                if prio_val != "(Không set)":
                    cmds.extend(L2ConfigBuilder.build_stp_vlan_priority(vlan, int(prio_val)))

            is_glob = self.var_pf_global.get()
            pf_int = self.ent_pf_int.get().strip()
            if is_glob or pf_int:
                cmds.extend(L2ConfigBuilder.build_portfast_bpduguard(
                    interface=pf_int if not is_glob else None,
                    portfast_enable=self.var_pf_en.get(),
                    bpduguard_enable=self.var_bpdu_en.get(),
                    is_global=is_glob
                ))
            return cmds

        self._render_action_bar(tab, _get_cmds)

    # ------------------ 4. ETHERCHANNEL TAB ------------------
    def _build_etherchannel_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        grp = ctk.CTkFrame(container)
        grp.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp, text="Cấu hình EtherChannel (Link Aggregation)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f1 = ctk.CTkFrame(grp, fg_color="transparent")
        f1.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f1, text="Cổng thành viên (Interface range):", width=220, anchor="w").pack(side="left")
        self.ent_eth_int = ctk.CTkEntry(f1, placeholder_text="Ví dụ: Gi0/1-2", width=220)
        self.ent_eth_int.pack(side="left")

        f2 = ctk.CTkFrame(grp, fg_color="transparent")
        f2.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f2, text="Channel-Group ID (1-64):", width=220, anchor="w").pack(side="left")
        self.ent_eth_id = ctk.CTkEntry(f2, placeholder_text="Ví dụ: 1", width=120)
        self.ent_eth_id.insert(0, "1")
        self.ent_eth_id.pack(side="left")

        f3 = ctk.CTkFrame(grp, fg_color="transparent")
        f3.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f3, text="Chế độ (Channel Mode):", width=220, anchor="w").pack(side="left")
        self.combo_eth_mode = ctk.CTkComboBox(
            f3,
            values=["active (LACP)", "passive (LACP)", "desirable (PAgP)", "auto (PAgP)", "on (Static)"],
            width=200
        )
        self.combo_eth_mode.set("active (LACP)")
        self.combo_eth_mode.pack(side="left")

        def _get_cmds():
            intf = self.ent_eth_int.get().strip()
            if not intf:
                raise ValueError("Vui lòng nhập dải cổng thành viên EtherChannel.")
            gid = int(self.ent_eth_id.get().strip())
            mode_raw = self.combo_eth_mode.get().split()[0]
            return L2ConfigBuilder.build_etherchannel(intf, gid, mode_raw)

        self._render_action_bar(tab, _get_cmds)

    # ------------------ 5. PORT SECURITY TAB ------------------
    def _build_port_security_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        grp = ctk.CTkFrame(container)
        grp.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp, text="Cấu hình Bảo Mật Cổng (Port Security)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_int = ctk.CTkFrame(grp, fg_color="transparent")
        f_int.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_int, text="Interface / Dải cổng:", width=180, anchor="w").pack(side="left")
        self.ent_sec_int = ctk.CTkEntry(f_int, placeholder_text="Ví dụ: Fa0/1-10", width=220)
        self.ent_sec_int.pack(side="left")

        f_en = ctk.CTkFrame(grp, fg_color="transparent")
        f_en.pack(fill="x", padx=10, pady=6)
        self.var_sec_enable = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f_en, text="Bật Port Security trên cổng", variable=self.var_sec_enable).pack(side="left")

        f_max = ctk.CTkFrame(grp, fg_color="transparent")
        f_max.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_max, text="Số lượng MAC tối đa (Max MAC):", width=220, anchor="w").pack(side="left")
        self.ent_sec_max = ctk.CTkEntry(f_max, placeholder_text="1", width=100)
        self.ent_sec_max.insert(0, "1")
        self.ent_sec_max.pack(side="left")

        f_viol = ctk.CTkFrame(grp, fg_color="transparent")
        f_viol.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_viol, text="Hành vi vi phạm (Violation):", width=220, anchor="w").pack(side="left")
        self.combo_sec_viol = ctk.CTkComboBox(f_viol, values=["shutdown", "restrict", "protect"], width=160)
        self.combo_sec_viol.set("shutdown")
        self.combo_sec_viol.pack(side="left")

        f_stick = ctk.CTkFrame(grp, fg_color="transparent")
        f_stick.pack(fill="x", padx=10, pady=6)
        self.var_sec_sticky = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f_stick, text="Tự động ghi nhớ MAC động (Sticky MAC)", variable=self.var_sec_sticky).pack(side="left")

        def _get_cmds():
            intf = self.ent_sec_int.get().strip()
            if not intf:
                raise ValueError("Vui lòng nhập interface.")
            enable = self.var_sec_enable.get()
            max_m = int(self.ent_sec_max.get().strip() or 1)
            viol = self.combo_sec_viol.get().strip()
            sticky = self.var_sec_sticky.get()
            return L2ConfigBuilder.build_port_security(intf, enable, max_m, viol, sticky)

        self._render_action_bar(tab, _get_cmds)

    # ------------------ 6. DHCP SNOOPING & DAI TAB ------------------
    def _build_dhcp_dai_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # DHCP Snooping
        grp_dhcp = ctk.CTkFrame(container)
        grp_dhcp.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_dhcp, text="DHCP Snooping", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_dhcp1 = ctk.CTkFrame(grp_dhcp, fg_color="transparent")
        f_dhcp1.pack(fill="x", padx=10, pady=6)
        self.var_dhcp_en = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f_dhcp1, text="Bật DHCP Snooping toàn cục", variable=self.var_dhcp_en).pack(side="left", padx=(0, 20))
        self.var_dhcp_opt82 = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f_dhcp1, text="Bật Option 82", variable=self.var_dhcp_opt82).pack(side="left")

        f_dhcp2 = ctk.CTkFrame(grp_dhcp, fg_color="transparent")
        f_dhcp2.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_dhcp2, text="Áp dụng cho VLANs:", width=180, anchor="w").pack(side="left")
        self.ent_dhcp_vlans = ctk.CTkEntry(f_dhcp2, placeholder_text="Ví dụ: 10,20,30 hoặc 1-100", width=220)
        self.ent_dhcp_vlans.pack(side="left")

        f_dhcp3 = ctk.CTkFrame(grp_dhcp, fg_color="transparent")
        f_dhcp3.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_dhcp3, text="Cổng Tin Cậy (Trust Port/Uplink):", width=180, anchor="w").pack(side="left")
        self.ent_dhcp_trust = ctk.CTkEntry(f_dhcp3, placeholder_text="Ví dụ: Gi0/24 hoặc Gi0/1-2", width=220)
        self.ent_dhcp_trust.pack(side="left")

        # Dynamic ARP Inspection
        grp_dai = ctk.CTkFrame(container)
        grp_dai.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_dai, text="Dynamic ARP Inspection (DAI)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_dai1 = ctk.CTkFrame(grp_dai, fg_color="transparent")
        f_dai1.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_dai1, text="Bật DAI cho VLANs:", width=180, anchor="w").pack(side="left")
        self.ent_dai_vlans = ctk.CTkEntry(f_dai1, placeholder_text="Ví dụ: 10,20", width=220)
        self.ent_dai_vlans.pack(side="left")

        f_dai2 = ctk.CTkFrame(grp_dai, fg_color="transparent")
        f_dai2.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_dai2, text="Cổng Tin Cậy DAI (Trust):", width=180, anchor="w").pack(side="left")
        self.ent_dai_trust = ctk.CTkEntry(f_dai2, placeholder_text="Ví dụ: Gi0/24", width=220)
        self.ent_dai_trust.pack(side="left")

        def _get_cmds():
            cmds = []
            dhcp_vlans = self.ent_dhcp_vlans.get().strip()
            dhcp_trust = [t.strip() for t in self.ent_dhcp_trust.get().split(",") if t.strip()]
            if dhcp_vlans or dhcp_trust or self.var_dhcp_en.get():
                cmds.extend(L2ConfigBuilder.build_dhcp_snooping(
                    enable_global=self.var_dhcp_en.get(),
                    vlans=dhcp_vlans,
                    trust_interfaces=dhcp_trust,
                    information_option=self.var_dhcp_opt82.get()
                ))

            dai_vlans = self.ent_dai_vlans.get().strip()
            dai_trust = [t.strip() for t in self.ent_dai_trust.get().split(",") if t.strip()]
            if dai_vlans or dai_trust:
                cmds.extend(L2ConfigBuilder.build_dai(
                    vlans=dai_vlans,
                    trust_interfaces=dai_trust
                ))
            return cmds

        self._render_action_bar(tab, _get_cmds)

    # ------------------ 7. STORM CONTROL & INTERFACE ------------------
    def _build_storm_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Interface selection
        grp_int = ctk.CTkFrame(container)
        grp_int.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_int, text="Interface Mục Tiêu", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_int = ctk.CTkFrame(grp_int, fg_color="transparent")
        f_int.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_int, text="Interface / Dải cổng:", width=180, anchor="w").pack(side="left")
        self.ent_st_int = ctk.CTkEntry(f_int, placeholder_text="Ví dụ: Gi0/1-10", width=220)
        self.ent_st_int.pack(side="left")

        # Storm Control
        grp_sc = ctk.CTkFrame(container)
        grp_sc.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_sc, text="Kiểm Soát Bão Lưu Lượng (Storm Control)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_bc = ctk.CTkFrame(grp_sc, fg_color="transparent")
        f_bc.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_bc, text="Ngưỡng Broadcast (% 0-100):", width=220, anchor="w").pack(side="left")
        self.ent_sc_bc = ctk.CTkEntry(f_bc, placeholder_text="Ví dụ: 20.0 (để trống nếu không đổi)", width=160)
        self.ent_sc_bc.pack(side="left")

        f_mc = ctk.CTkFrame(grp_sc, fg_color="transparent")
        f_mc.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_mc, text="Ngưỡng Multicast (% 0-100):", width=220, anchor="w").pack(side="left")
        self.ent_sc_mc = ctk.CTkEntry(f_mc, placeholder_text="Ví dụ: 15.0 (để trống nếu không đổi)", width=160)
        self.ent_sc_mc.pack(side="left")

        f_act = ctk.CTkFrame(grp_sc, fg_color="transparent")
        f_act.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_act, text="Hành động khi vượt ngưỡng:", width=220, anchor="w").pack(side="left")
        self.combo_sc_act = ctk.CTkComboBox(f_act, values=["trap", "shutdown"], width=160)
        self.combo_sc_act.set("trap")
        self.combo_sc_act.pack(side="left")

        # Port Settings
        grp_port = ctk.CTkFrame(container)
        grp_port.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_port, text="Cài Đặt Cổng (Description, Speed, Duplex, Shutdown)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f_desc = ctk.CTkFrame(grp_port, fg_color="transparent")
        f_desc.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_desc, text="Description (Mô tả cổng):", width=180, anchor="w").pack(side="left")
        self.ent_p_desc = ctk.CTkEntry(f_desc, placeholder_text="Uplink to Core Switch", width=260)
        self.ent_p_desc.pack(side="left")

        f_sd = ctk.CTkFrame(grp_port, fg_color="transparent")
        f_sd.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_sd, text="Tốc độ (Speed):", width=120, anchor="w").pack(side="left")
        self.combo_p_speed = ctk.CTkComboBox(f_sd, values=["(Không đổi)", "auto", "10", "100", "1000"], width=120)
        self.combo_p_speed.set("(Không đổi)")
        self.combo_p_speed.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f_sd, text="Duplex:", width=60, anchor="w").pack(side="left")
        self.combo_p_duplex = ctk.CTkComboBox(f_sd, values=["(Không đổi)", "auto", "full", "half"], width=120)
        self.combo_p_duplex.set("(Không đổi)")
        self.combo_p_duplex.pack(side="left")

        f_shut = ctk.CTkFrame(grp_port, fg_color="transparent")
        f_shut.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f_shut, text="Trạng thái cổng:", width=180, anchor="w").pack(side="left")
        self.combo_p_state = ctk.CTkComboBox(f_shut, values=["(Không đổi)", "no shutdown (Bật cổng)", "shutdown (Tắt cổng)"], width=180)
        self.combo_p_state.set("(Không đổi)")
        self.combo_p_state.pack(side="left")

        def _get_cmds():
            intf = self.ent_st_int.get().strip()
            if not intf:
                raise ValueError("Vui lòng chỉ định interface.")
            cmds = []
            bc = float(self.ent_sc_bc.get().strip()) if self.ent_sc_bc.get().strip() else None
            mc = float(self.ent_sc_mc.get().strip()) if self.ent_sc_mc.get().strip() else None
            if bc is not None or mc is not None:
                cmds.extend(L2ConfigBuilder.build_storm_control(intf, bc, mc, self.combo_sc_act.get().strip()))

            desc = self.ent_p_desc.get().strip() if self.ent_p_desc.get().strip() else None
            sp = self.combo_p_speed.get() if self.combo_p_speed.get() != "(Không đổi)" else None
            dp = self.combo_p_duplex.get() if self.combo_p_duplex.get() != "(Không đổi)" else None
            shut_str = self.combo_p_state.get()
            shut = True if "shutdown (Tắt cổng)" in shut_str else (False if "no shutdown" in shut_str else None)

            if desc is not None or sp is not None or dp is not None or shut is not None:
                cmds.extend(L2ConfigBuilder.build_interface_settings(intf, desc, sp, dp, shut))
            return cmds

        self._render_action_bar(tab, _get_cmds)

    # ------------------ 8. MAC TABLE TAB ------------------
    def _build_mac_tab(self, tab):
        container = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Static MAC
        grp_static = ctk.CTkFrame(container)
        grp_static.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_static, text="Thêm Static MAC Address", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 4))

        f1 = ctk.CTkFrame(grp_static, fg_color="transparent")
        f1.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f1, text="Địa chỉ MAC (dạng xxxx.xxxx.xxxx):", width=240, anchor="w").pack(side="left")
        self.ent_mac_addr = ctk.CTkEntry(f1, placeholder_text="0011.2233.4455", width=200)
        self.ent_mac_addr.pack(side="left")

        f2 = ctk.CTkFrame(grp_static, fg_color="transparent")
        f2.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f2, text="VLAN ID:", width=120, anchor="w").pack(side="left")
        self.ent_mac_vlan = ctk.CTkEntry(f2, placeholder_text="10", width=100)
        self.ent_mac_vlan.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(f2, text="Interface:", width=80, anchor="w").pack(side="left")
        self.ent_mac_int = ctk.CTkEntry(f2, placeholder_text="Gi0/1", width=140)
        self.ent_mac_int.pack(side="left")

        # Clear Dynamic MAC
        grp_clr = ctk.CTkFrame(container)
        grp_clr.pack(fill="x", pady=6, padx=6)
        ctk.CTkLabel(grp_clr, text="Xóa Bảng MAC Động (Clear Dynamic MAC)", font=ctk.CTkFont(weight="bold"), text_color="#EF4444").pack(anchor="w", padx=10, pady=(8, 4))

        f3 = ctk.CTkFrame(grp_clr, fg_color="transparent")
        f3.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(f3, text="Lọc theo VLAN (tùy chọn):", width=180, anchor="w").pack(side="left")
        self.ent_clr_vlan = ctk.CTkEntry(f3, placeholder_text="Để trống = Xóa tất cả", width=160)
        self.ent_clr_vlan.pack(side="left")

        def _get_cmds():
            cmds = []
            mac = self.ent_mac_addr.get().strip()
            if mac:
                vlan = int(self.ent_mac_vlan.get().strip())
                intf = self.ent_mac_int.get().strip()
                cmds.extend(L2ConfigBuilder.build_mac_static(mac, vlan, intf))

            clr_v = self.ent_clr_vlan.get().strip()
            if clr_v:
                cmds.append(L2ConfigBuilder.build_clear_mac_dynamic(vlan_id=int(clr_v)))
            return cmds

        self._render_action_bar(tab, _get_cmds)
