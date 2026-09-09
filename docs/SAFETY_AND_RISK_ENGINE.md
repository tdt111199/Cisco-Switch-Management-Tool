# Safety Principles & Risk Protection Engine

## 🛡️ Core Safety Principles

> [!CAUTION]
> **Zero Direct Mutation Principle**:
> The application will **NEVER** push automated `shutdown` commands directly to devices. It exclusively generates human-readable Cisco IOS configuration scripts with rollback counterparts for engineering review.

---

## 🚦 Multi-Criteria Classification Matrix

| Classification | Color Badge | Evaluation Criteria | Eligible for Shutdown? |
|---|---|---|---|
| **`PROTECTED`** | Sky Blue | Port exists in `Protected_Ports` sheet or user toggled "Protected" on GUI. | ❌ **Strictly Excluded** |
| **`TRUNK/UPLINK`** | Purple | Port is 802.1Q trunk (`switchport mode trunk`), CDP/LLDP neighbor found, or description has uplink keywords (`core`, `uplink`, `wan`, `ap`, `router`, `firewall`). | ❌ **Strictly Excluded** |
| **`PORT-CHANNEL`** | Purple | Port-channel interface or member of an EtherChannel bundle (from `show etherchannel summary`). | ❌ **Strictly Excluded** |
| **`ACTIVE`** | Green | Operational status is `connected`/`up`, learned MAC count > 0, or active traffic within last 24 hours. | ❌ **Strictly Excluded** |
| **`MONITOR`** | Yellow | Port is `notconnect`/`down`, 0 MAC, but has not reached the inactivity threshold days (e.g. down for 15 days out of 60 days). | ❌ **Strictly Excluded** |
| **`UNUSED`** | Red | Port is down, 0 MAC, 0 traffic, not trunk, not uplink, not port-channel, not protected, and `Days_Unused >= Threshold`. | ✅ **Eligible for Shutdown Script** |
| **`ERROR`** | Dark Grey | Switch unreachable, authentication failed, or CLI command timeout. | ❌ **Strictly Excluded** |

---

## ⚙️ Safe Config Generation & Rollback

### Shutdown Script Example
```cisco
! =========================================================================
! CISCO HISTORICAL UNUSED PORT SCANNER - SHUTDOWN CONFIGURATION SCRIPT
! Thời gian tạo: 2026-09-09 16:30:00
! Thiết bị: SW-Floor-01 (192.168.10.10) - Số cổng đề xuất: 2
! =========================================================================
configure terminal
interface GigabitEthernet0/12
 description [UNUSED-SHUTDOWN-2026-09-09] Desk-B14
 shutdown
!
interface GigabitEthernet0/14
 description [UNUSED-SHUTDOWN-2026-09-09] Meeting-Room-Aux
 shutdown
!
end
write memory
```

### Rollback Script Example
```cisco
! =========================================================================
! CISCO HISTORICAL UNUSED PORT SCANNER - ROLLBACK RESTORATION SCRIPT
! Thời gian tạo: 2026-09-09 16:30:00
! =========================================================================
configure terminal
interface GigabitEthernet0/12
 description Desk-B14
 no shutdown
!
interface GigabitEthernet0/14
 description Meeting-Room-Aux
 no shutdown
!
end
write memory
```
