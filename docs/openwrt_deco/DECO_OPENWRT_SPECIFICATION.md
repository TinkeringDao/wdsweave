# TP-Link Deco M4R / P9 — OpenWrt 24.10.8 Architecture & Engineering Specification

## Problem Statement

The home network operates a multi-node TP-Link Deco mesh system (8 nodes total across the home lab and living areas). The stock firmware provided by the vendor exhibits several compounding operational liabilities:
1. **Severe Latency & Bufferbloat**: Stock firmware runs an unmaintained, ancient Linux 3.3.8 kernel (dating back to 2012) with proprietary, closed-source Wi-Fi rate adaptation algorithms, causing severe latency spikes, bufferbloat during concurrent LAN/WAN streams, and packet loss on home lab nodes.
2. **End-of-Life Vendor Software Stack**: TP-Link has frozen active feature development and security patches for older Deco hardware revisions. Cloud-tethered management is dependent on third-party mobile apps and vendor cloud infrastructure (`tplinkdeco.net` / AWS proxies), introducing transient API failures and communication stalls.
3. **Lack of Advanced Networking & Observability**: Stock firmware does not support standard Linux network interfaces, 802.1Q VLAN tagging, native WireGuard tunneling, Prometheus `node_exporter` telemetry, CAKE/FQ-CoDel SQM, or unencumbered local SSH/syslog administration.
4. **Vendor Lock-in & Signature Hardening**: Stock Web UI and mobile application updaters strictly enforce RSA signature verification, rejecting third-party open-source firmware and preventing users from maintaining control over their physical hardware assets.

---

## Solution

Rework the Deco mesh hardware by taking an isolated guinea pig node (such as the offline Deco or a lab satellite node) and flashing modern **OpenWrt 24.10.8 (Linux 6.6.144)** using a clean-room, zero-solder bootloader exploitation vector:
1. **REA Binary Decomposition (`morluto/rea`)**: Decompose the stock TP-Link firmware (`M4R 1.8.0 Build 20250721`), the U-Boot WebFailsafe HTTP exploit, and the target OpenWrt 24.10.8 images to verify exact kernel, architecture, memory offsets, and SquashFS flash boundaries.
2. **U-Boot WebFailsafe Stack Overflow Exploit**: Leverage the unconstrained `sscanf` vulnerability in the stock U-Boot recovery web server on the `fw-type` field to overwrite the return address to `0x80060200` and execute MIPS shellcode.
3. **RAM Bootstrap via TFTP**: Injected shellcode automatically configures U-Boot IP environment (`serverip 192.168.0.2`, `ipaddr 192.168.0.1`), pulls `initramfs-kernel.bin` via TFTP into RAM address `0x82000000`, and executes `bootm`, safely booting OpenWrt into volatile memory without risking SPI flash bricking.
4. **Permanent Sysupgrade**: From the live OpenWrt RAM environment, execute `sysupgrade -v -n` to permanently flash the 16MB SPI NOR memory with the OpenWrt 24.10.8 SquashFS kernel and rootfs.
5. **Decentralized Fast Roaming (802.11k/v/r)**: Provision open-standard fast BSS transition (FT-PSK), Radio Resource Management, and BSS Transition Management to eliminate vendor-dependent mesh lockouts and provide seamless roaming across the home network.

---

## User Stories

1. As a network administrator, I want to inspect and decompose the vendor's stock firmware binary, so that I can determine the exact kernel version, architecture, and memory layout before flashing.
2. As a systems engineer, I want to verify the exact stack overflow offset in the U-Boot recovery HTTP daemon, so that the exploit reliably gains control of the program counter without crashing into invalid memory.
3. As a developer, I want to load an OpenWrt initramfs kernel purely into RAM via TFTP, so that I can verify hardware stability, radio drivers, and ethernet PHY functionality before touching non-volatile SPI flash.
4. As a security architect, I want to replace the vendor's proprietary cloud daemon with an open-source, local-only operating system, so that device telemetry and credentials are never transmitted outside the private LAN.
5. As a home lab user, I want to flash OpenWrt 24.10.8 on a guinea pig Deco M4R node, so that I can benchmark latency, throughput, and CPU utilization against stock Deco nodes.
6. As a network architect, I want to configure bridged Access Point (AP) mode on the guinea pig node, so that existing DHCP and DNS services on the upstream gateway remain authoritative.
7. As a mobile client user, I want 802.11r Fast BSS Transition enabled with a shared mobility domain, so that wireless devices roam between nodes in under 50 milliseconds without dropped TCP sessions.
8. As a Wi-Fi client, I want 802.11k Radio Resource Management active, so that my device receives neighbor AP reports and discovers optimal candidate bands without high battery consumption.
9. As a network administrator, I want 802.11v BSS Transition Management enabled, so that the router can suggest client steering away from congested 2.4 GHz frequencies to clear 5 GHz channels.
10. As an operator, I want an automated Python-based TFTP server that requires zero external dependencies, so that recovery files can be served reliably from macOS without third-party package managers.
11. As a systems auditor, I want a TDD test suite validating the exploit binary, uImage header CRCs, and flash geometry, so that regression or corrupted images are halted before deployment.
12. As a developer, I want to deploy WPA2-PSK and WPA3-SAE mixed mode encryption, so that legacy IoT devices and modern smartphones connect securely to the same SSID.
13. As an operator, I want a verified rollback procedure to the factory stock firmware, so that any node can be restored to the vendor baseline if hardware repurposing is required.
14. As an infrastructure engineer, I want SSH access with Ed25519 key authentication, so that nodes can be scripted and monitored via Ansible or Prometheus.

---

## Implementation Decisions

### Architectural Seams & Hardware Model
- **Target Platform**: Qualcomm Atheros QCA9563 (MIPS 24Kc @ 750 MHz), 128 MB DDR2 RAM, 16 MB SPI NOR flash, dual Gigabit Ethernet ports, Qualcomm Atheros 2.4 GHz + QCA9886 5 GHz radios.
- **Hardware Targets**: Deco M4R v1.0, Deco M4R v2.0 (covered by OpenWrt target `ath79/generic/tplink_deco-m4r-v1`), and Deco P9 v2.0.
- **Kernel Evolution**: Migration from stock Linux 3.3.8 (July 2025 build with 2012 kernel codebase) to mainline Linux 6.6.144 LTS.

### Exploit Vector & Memory Execution Seam
- **Vulnerability**: Stock U-Boot WebFailsafe HTTP server (`http://192.168.0.1`) reads user-submitted `fw-type` string using unconstrained `sscanf()` into a 256-byte stack buffer.
- **Exploit Payload**: `deco_all_webfailsafe_faux_fw_tftp_v2.bin` (32,768 bytes), structured with `b"fw-type:"` followed by 256 padding bytes, register clobber (`$s0-$s2`), and return address overwrite `0x80060200`.
- **Shellcode Execution**: Dynamic U-Boot memory scanner locates `run_command` and `NetReceive` symbols, sets `serverip 192.168.0.2` and `ipaddr 192.168.0.1`, downloads `initramfs-kernel.bin` to `0x82000000`, and executes `bootm 0x82000000`.

### Flash Storage & Sysupgrade Seam
- **Temporary Execution**: RAM-only initramfs kernel image (`openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-initramfs-kernel.bin`, 6.8 MB).
- **Permanent Storage**: Sysupgrade SquashFS image (`openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-squashfs-sysupgrade.bin`, 7.1 MB), written via `/sbin/sysupgrade -v -n /tmp/sysupgrade.bin`.
- **Flash Layout**: 16 MB NOR flash partitioned for U-Boot (128 KB), U-Boot Environment (64 KB), Firmware (Kernel + SquashFS + JFFS2 overlay), ART (Atheros Radio Test / calibration data, 64 KB).

### Network & Roaming Architecture
- **Operating Mode**: Bridge / Access Point (AP) mode. Both physical ethernet ports (`eth0`, `eth1`) bridged into `br-lan`.
- **IP Assignment**: Static IP on `192.168.1.0/24` subnet outside DHCP pool, pointing to gateway `192.168.1.1` and DNS `192.168.1.52`.
- **Fast Roaming Stack**: 802.11r FT-PSK with local key derivation (`ft_psk_generate_local=1`), mobility domain `4f57`, 802.11k RRM neighbor reporting, and 802.11v BSS transition with disassociation imminent hints.

---

## Testing Decisions

### Seam 1: Exploit Payload Verification
- Verify binary size is exactly 32,768 bytes (`0x8000`).
- Assert presence of `fw-type:` overflow header, 256-byte stack fill, and exact return address `0x80060200`.
- Assert presence of essential U-Boot shellcode string primitives (`setenv serverip`, `setenv ipaddr`, `tftpboot`, `bootm`).

### Seam 2: OpenWrt uImage Contract & Cryptographic Verification
- Validate uImage magic `0x27051956`.
- Validate architecture is MIPS (`5`), OS is Linux (`5`), image type is Kernel (`2`), and compression is LZMA (`3`).
- Assert load address and entry point are both `0x80060000`.
- Cryptographically calculate CRC32 of header (with zeroed CRC field) and data payload; verify 100% match against header checksum fields.

### Seam 3: Sysupgrade Layout & Flash Boundary
- Verify SquashFS superblock `hsqs` begins immediately at `offset = 64 + uimage_size`.
- Assert total sysupgrade image size does not exceed the 15 MB flash allocation limit.

### Seam 4: TFTP Server Staging & Packet Engine
- Verify staging directory structure and existence of `initramfs-kernel.bin`.
- Validate RFC 1350 Read Request (RRQ) packet parser and block sequencing logic.

### Seam 5: Network Template & UCI Configuration
- Validate generated `/etc/config/network` for static IP, gateway, and DNS configuration.
- Validate generated `/etc/config/wireless` for dual-band radio configuration and complete 802.11k/v/r parameters.
