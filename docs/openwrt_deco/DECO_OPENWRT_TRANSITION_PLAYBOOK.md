# TP-Link Deco M4R / P9 — OpenWrt 24.10.8 Transition Playbook

## 1. Multi-Node Rollout Order & Staging Unit Selection

In a multi-node TP-Link Deco mesh deployment, transition nodes from the network periphery inward so existing wireless satellites retain upstream connectivity throughout the migration:

| Node Role | Model | Hardware Rev | Example LAN IP | Stock Firmware Baseline | Rollout Order |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Spare / Offline Unit** | Deco M4R / P9 | v1.0 / v2.0 | *(Bench staging)* | `1.2.x` – `1.8.0` | **1st (Ideal Bench Candidate)** |
| **Leaf Satellite A** | Deco M4R | v1.0 | `192.168.1.241` | `1.8.0 Build 20250721` | 2nd (Wireless / Wired Leaf) |
| **Leaf Satellite B** | Deco M4R | v2.0 | `192.168.1.242` | `1.6.2 Build 20240308` | 3rd (Secondary Satellite) |
| **Distribution Satellite** | Deco M4R | v2.0 | `192.168.1.243` | `1.8.0 Build 20250721` | 4th (Intermediate Wired Node) |
| **PLC Hybrid Satellite** | Deco P9 | v2.0 | `192.168.1.244` | `1.2.1 Build 20240716` | 5th (`QCA7500` PLC Port 4) |
| **Primary Mesh Gateway** | Deco M4R | v2.0 | `192.168.1.253` | `1.8.0 Build 20250721` | **Last (DO NOT FLASH FIRST)** |

> [!IMPORTANT]
> **Rollout Sequencing Rules**:
> - Always validate TFTP recovery and OpenWrt `sysupgrade` on an **offline spare unit** or a leaf satellite first.
> - **Never flash the Primary Mesh Gateway first**, as remaining stock satellites depend on its proprietary `awnd` / `hyfi-bridging` controller until transitioned to standard IEEE 802.11k/v/r or WDS/802.11s.

---

## 2. Pre-Flight Preparation

### 2.1 Hardware Requirements
- 1x Target TP-Link Deco unit (power supply included).
- 1x Standard RJ45 Ethernet cable.
- 1x Mac or Linux machine with an Ethernet port or USB Ethernet adapter.
- 1x Pin, SIM-ejector tool, or paperclip to press the recessed RESET button.

### 2.2 Network Topology & Staging Environment
The flashing process uses an isolated link between your computer and the Deco:
```
+------------------------------------+          Ethernet Cable          +-------------------------------+
|      Host Machine (Mac/Linux)      | <==============================> |     TP-Link Deco (Guinea Pig) |
| Static IP: 192.168.0.2 / 24        |                                  | Recovery IP: 192.168.0.1      |
| TFTP Server: UDP Port 69           |                                  | OpenWrt Boot: 192.168.1.1     |
+------------------------------------+                                  +-------------------------------+
```

---

## 3. Automated 1-Click Flashing Procedure

The repository provides an automated flashing engine that handles all network configuration, TFTP staging, exploit delivery, and OpenWrt installation.

### Step 1: Run the Pre-Flight Verification Tests
Run the TDD seam test suite to ensure all binaries and payloads are intact:
```bash
python3 -m unittest tests/test_deco_openwrt_seams.py
```
Expected output:
```
Ran 9 tests in 0.012s
OK
```

### Step 2: Connect and Enter U-Boot Recovery Mode
1. Unplug the power adapter from the Deco unit.
2. Connect the Ethernet cable between your computer and **Port 1** of the Deco.
3. Insert a pin into the small **RESET** hole on the bottom of the Deco and hold the button down.
4. While continuing to hold the RESET button, plug the power adapter back into the Deco.
5. Keep holding the button for **5 to 8 seconds** until the top LED pulses amber/yellow or flashes green, then release it.
6. The Deco bootloader HTTP server is now running at `http://192.168.0.1`.

### Step 3: Execute the Flasher Script
Run the flasher wrapper script (specify your ethernet interface, e.g., `en0` or `en7`):
```bash
sudo ./scripts/flash-deco-openwrt.sh en0
```

The script automatically executes the following pipeline:
1. Configures `192.168.0.2/24` alias on your interface.
2. Starts the zero-dependency TFTP server serving `initramfs-kernel.bin`.
3. Pings and discovers `http://192.168.0.1`.
4. Uploads the exploit payload (`deco_all_webfailsafe_faux_fw_tftp_v2.bin`).
5. U-Boot triggers the stack overflow, executes the shellcode, and downloads `initramfs-kernel.bin` via TFTP into RAM (`0x82000000`).
6. The Deco boots into the live OpenWrt RAM environment.
7. The script detects OpenWrt at `192.168.1.1`, transfers `openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-squashfs-sysupgrade.bin`, and triggers `sysupgrade -v -n`.
8. The router flashes the 16MB SPI NOR memory and reboots cleanly into permanent OpenWrt!

---

## 4. Manual Step-by-Step Procedure (Fallback)

If you prefer to execute the recovery steps manually without the orchestrator:

1. **Configure your network interface:**
   ```bash
   sudo ifconfig en0 alias 192.168.0.2 255.255.255.0
   ```

2. **Stage and run the TFTP server:**
   ```bash
   python3 scripts/tftp_server.py --host 192.168.0.2 --port 69 --root firmware/tftp_stage
   ```

3. **Put Deco into Recovery Mode:**
   - Hold RESET, plug in power, wait for flashing LED.

4. **Upload Exploit via Browser:**
   - Open browser to `http://192.168.0.1/`.
   - In the firmware upgrade form, select `firmware/exploits/deco_all_webfailsafe_faux_fw_tftp_v2.bin`.
   - Click **Upgrade**.
   - Watch the TFTP terminal: the Deco will request `initramfs-kernel.bin` and download all 6.8 MB in ~15 seconds.

5. **Access OpenWrt RAM Environment:**
   - Change your computer IP to `192.168.1.2 / 255.255.255.0`.
   - Connect via SSH:
     ```bash
     ssh root@192.168.1.1
     ```

6. **Flash Permanent Sysupgrade:**
   ```bash
   # From your Mac:
   scp firmware/openwrt/openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-squashfs-sysupgrade.bin root@192.168.1.1:/tmp/sysupgrade.bin

   # Inside the OpenWrt SSH session:
   sysupgrade -v -n /tmp/sysupgrade.bin
   ```
   - The device will write to SPI NOR flash and reboot automatically (takes ~2 minutes).

---

## 5. Post-Installation Configuration

### 5.1 Accessing the OpenWrt Web Interface (LuCI)
Once rebooted:
1. Connect your browser to `http://192.168.1.1/`.
2. Log in as `root` (no password initially set).
3. Set a strong root password.

### 5.2 Configuring Bridged AP Mode for Home Lab
To integrate the Deco cleanly into the local network (`192.168.1.0/24`) without double-NAT:

```bash
# Set LAN IP on the home lab subnet
uci set network.lan.proto='static'
uci set network.lan.ipaddr='192.168.1.240'
uci set network.lan.netmask='255.255.255.0'
uci set network.lan.gateway='192.168.1.1'
uci add_list network.lan.dns='192.168.1.52'

# Bridge both physical ethernet ports
uci add_list network.@device[0].ports='eth0'
uci add_list network.@device[0].ports='eth1'

# Disable DHCP server (let upstream gateway assign IPs)
uci set dhcp.lan.ignore='1'

# Commit and apply
uci commit network
uci commit dhcp
/etc/init.d/network restart
/etc/init.d/dnsmasq restart
```

### 5.3 Configuring 802.11k/v/r Fast Roaming
Install the full hostapd package (if using standard OpenWrt image, `wpad-basic-mbedtls` supports 802.11r/k/v):
```bash
# Configure 2.4 GHz (radio0)
uci set wireless.default_radio0.ssid='OpenWrt-Mesh'
uci set wireless.default_radio0.encryption='psk2+ccmp'
uci set wireless.default_radio0.key='YourSecureWifiPassword'
uci set wireless.default_radio0.ieee80211r='1'
uci set wireless.default_radio0.mobility_domain='4f57'
uci set wireless.default_radio0.ft_over_ds='0'
uci set wireless.default_radio0.ft_psk_generate_local='1'
uci set wireless.default_radio0.ieee80211k='1'
uci set wireless.default_radio0.ieee80211v='1'
uci set wireless.default_radio0.bss_transition='1'
uci set wireless.default_radio0.wnm_sleep_mode='1'
uci set wireless.radio0.disabled='0'

# Configure 5 GHz (radio1)
uci set wireless.default_radio1.ssid='OpenWrt-Mesh'
uci set wireless.default_radio1.encryption='psk2+ccmp'
uci set wireless.default_radio1.key='YourSecureWifiPassword'
uci set wireless.default_radio1.ieee80211r='1'
uci set wireless.default_radio1.mobility_domain='4f57'
uci set wireless.default_radio1.ft_over_ds='0'
uci set wireless.default_radio1.ft_psk_generate_local='1'
uci set wireless.default_radio1.ieee80211k='1'
uci set wireless.default_radio1.ieee80211v='1'
uci set wireless.default_radio1.bss_transition='1'
uci set wireless.default_radio1.wnm_sleep_mode='1'
uci set wireless.radio1.disabled='0'

# Commit and restart Wi-Fi
uci commit wireless
wifi reload
```

---

## 6. Factory Rollback Procedure

If you ever wish to revert the guinea pig unit to stock TP-Link firmware:
1. Boot the Deco into U-Boot recovery mode (hold RESET while plugging in power).
2. Browse to `http://192.168.0.1/`.
3. Upload the stock firmware binary:
   `firmware/stock/M4R_en_1.8.0_Build_20250721_Rel.49216/M4R_en_1.8.0_Build_20250721_Rel.49216.bin`
4. Click **Upgrade** and wait 3 minutes.
5. The unit will reboot back into factory stock TP-Link firmware.
