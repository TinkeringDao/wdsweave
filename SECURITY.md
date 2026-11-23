# Security Policy

## Supported Hardware & Firmware Versions

| Product | Target SoC & Radios | Flash Geometry | Firmware Version | Supported |
| :--- | :--- | :--- | :--- | :--- |
| TP-Link Deco M4R v1 / v2 | `QCA9563` + `QCA9886` + `QCA8337N` | `16 MB` SPI NOR (`GD25Q128`) | OpenWrt `24.10.8` (`Linux 6.6.144`) | Yes |
| TP-Link Deco P9 v2 | `QCA9563` + `QCA9886` + `QCA8337N` + `QCA7500` PLC | `16 MB` SPI NOR (`GD25Q128`) | OpenWrt `24.10.8` (`Linux 6.6.144`) | Yes |

## Hardware, Flash, & RF Safety Boundaries

`wdsweave` operates strictly on user-owned `TP-Link Deco M4R` and `Deco P9` hardware via local wired Ethernet recovery and SSH interfaces:
- **Preserves Factory U-Boot (`mtd0`) & ART Radio Calibration (`mtd5`)**: The two-stage provisioning pipeline boots `initramfs-kernel.bin` strictly in volatile DDR2 RAM (`0x82000000` / `0x80060000`) before executing `sysupgrade` solely against the `firmware` partition (`0x00060000`–`0x00fa0000`), leaving `u-boot` (`0x00000000`–`0x00020000`) and factory `art` RF calibration data (`0x00ff0000`–`0x01000000`) untouched and read-only.
- **Pre-Flash Checksum & Header Verification**: `tests/test_deco_openwrt_seams.py` and `scripts/flash_deco_openwrt.py` validate the `uImage` magic (`0x27051956`), header/data CRC32, SquashFS boundary (`hsqs`), and SHA-256 digest in `/tmp/sysupgrade.bin` prior to writing flash.
- **Authorized Local Owner Execution Only (`18 U.S.C. § 1030 (CFAA)`)**: Provisioning tools communicate exclusively over a direct point-to-point wired Ethernet link (`192.168.0.1/24` / `192.168.1.1/24`) with hardware owned by the operator.
- **RF, DFS, & EIRP Compliance (`Directive 2014/53/EU (RED)` / `ETSI EN 300 328` / `ETSI EN 301 893` / `FCC 47 C.F.R. Part 15.247 & Part 15E`)**: Operators must configure the wireless regulatory country code (`option country`) and transmit power (`txpower`) to comply with local spectrum and Dynamic Frequency Selection (DFS) regulations (see [`LEGAL.md`](LEGAL.md)).

## Reporting a Vulnerability

If you discover a bug, flash geometry issue, or security vulnerability:
1. Open a private security advisory via [GitHub Security Advisories](https://github.com/TinkeringDao/wdsweave/security/advisories/new).
2. Include the commit SHA, hardware revision (`M4R v1`/`v2` or `P9 v2`), and steps to reproduce.
