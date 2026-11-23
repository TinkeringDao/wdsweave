# `wdsweave` (`TinkeringDao/wdsweave`)

[![CI](https://github.com/TinkeringDao/wdsweave/actions/workflows/ci.yml/badge.svg)](https://github.com/TinkeringDao/wdsweave/actions/workflows/ci.yml)
[![Security](https://github.com/TinkeringDao/wdsweave/actions/workflows/security.yml/badge.svg)](https://github.com/TinkeringDao/wdsweave/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Deterministic **OpenWrt 24.10** (`Linux 6.6.144` LTS) hybrid wired/WDS mesh provisioning, IEEE 802.11r/k/v neighbor roaming, and HomePlug AV2 loop-isolation toolkit for **TP-Link Deco M4R (v1 / v2)** and **TP-Link Deco P9 (v2)**.

---

## 1. Overview & Architecture

`wdsweave` provides a test-driven provisioning pipeline, clean-room firmware container inspector, and UCI configuration generator for transitioning Qualcomm Atheros `QCA9563` + `QCA9886` + `QCA8337N` (+ `QCA7500` PLC) Deco nodes from locked stock QSDK firmware (`Linux 3.3.8`) to mainline **OpenWrt 24.10.8 (`Linux 6.6.144` LTS)**.

### Key Capabilities

| Subsystem | Stock Firmware (`1.8.0` / `Linux 3.3.8` QSDK) | OpenWrt `24.10.8` (`Linux 6.6.144` LTS) with `wdsweave` |
| :--- | :--- | :--- |
| **Local SSH & Web Admin** | Locked behind `dropbear` `:20001` (`TPS-2.0-libtmp` binary opcodes) and mobile cloud app | Standard `dropbear` on `:22` (Ed25519 key auth) + local LuCI web UI (`http://192.168.1.1/cgi-bin/luci/`) |
| **Config Persistence** | Volatile `ramfs` over `/etc/config` encrypted via `ktrk.ko` + `libtrk.so` | Persistent `7.2 MB` writable JFFS2 `/overlay` (`~6.8 MB` free) + `~70 MB` free RAM |
| **Switch (`QCA8337N` / `AR8337`)** | Auto-sensed 2-VLAN lock (`wandetect3`) with hardware MAC learning disabled | Full 7-port Gigabit `swconfig` (`switch0`) with **4,096 802.1Q VLANs**, hardware ARL learning, 39 extended MIB counters/port, IGMPv3 snooping, and port mirroring |
| **5 GHz Radio (`QCA9886`)** | Closed QSDK `.ko` blobs spawning up to 16 hidden VAPs on a single locked channel | `ath10k-ct` Wave-2 (`VHT80`, SU/MU-MIMO), 27 channels (`UNII-1`..`UNII-3` + DFS), and **Airtime Queue Limits (`AQL = 2000 µs`)** |
| **2.4 GHz Radio (`AR9561`)** | Legacy driver with large FIFO bufferbloat and no 802.11w PMF | Mainline `ath9k` with **Airtime Fairness (`ATF`)**, **`AQL = 1500 µs`**, and hardware AES-CCMP / `BIP-CMAC-128` (`802.11w`) |
| **Hybrid Wired/WDS & Roaming** | Vendor-locked `awnd`/`apsd`/`nrd` | Standards-based **IEEE 802.11k/v/r** (`FT-PSK` / `FT-SAE`), **802.11w PMF**, pinned 4-address **WDS (`4addr`)**, and `stp=0` bridge fast-forwarding |
| **PLC Loop Isolation (`Deco P9 v2`)** | Closed `plc-ag`/`hyfi-bridging` daemon | `QCA7500` HomePlug AV2 MIMO exposed as `switch0` port with deterministic 802.1Q VLAN isolation preventing hybrid Ethernet + PLC + WDS Layer-2 broadcast loops |
| **Cloud Telemetry & TR-069** | 6 persistent `*.tplinkcloud.com` daemons + WAN `cwmp` (`:7547`) | **Zero** vendor cloud daemons, zero MAC uploads, zero TR-069 listeners |

---

## 2. Repository Structure

- [`docs/openwrt_deco/REA_STOCK_BASELINE_ANALYSIS.md`](docs/openwrt_deco/REA_STOCK_BASELINE_ANALYSIS.md): Clean-room decomposition of stock firmware `1.8.0` / `1.6.2` (`SafeLoader` container, 17-partition layout, `ktrk.ko`/`libtrk.so` config encryption, and 23 proprietary daemons).
- [`docs/openwrt_deco/HARDWARE_SILICON_CAPABILITIES.md`](docs/openwrt_deco/HARDWARE_SILICON_CAPABILITIES.md): Silicon register and driver reference for `QCA9563` SoC, `QCA8337N` 7-port switch (`switch0`), `GD25Q128` 16 MB SPI NOR flash + read-only `art` calibration (`mtd5`), and `QCA7500` PLC modem.
- [`docs/openwrt_deco/RF_WIRELESS_UNLOCK_GUIDE.md`](docs/openwrt_deco/RF_WIRELESS_UNLOCK_GUIDE.md): RF engineering guide for `QCA9886` (`ath10k-ct`) and `AR9561` (`ath9k`), AQL/ATF bufferbloat tuning, IEEE 802.11k/v/r/w fast roaming, and hardware FFT spectral scan.
- [`docs/openwrt_deco/DECO_OPENWRT_SPECIFICATION.md`](docs/openwrt_deco/DECO_OPENWRT_SPECIFICATION.md): Architectural seam specification and flash budget analysis.
- [`docs/openwrt_deco/DECO_OPENWRT_TRANSITION_PLAYBOOK.md`](docs/openwrt_deco/DECO_OPENWRT_TRANSITION_PLAYBOOK.md): Step-by-step U-Boot TFTP recovery, RAM boot verification, permanent `sysupgrade`, and rollback playbook.
- [`scripts/flash_deco_openwrt.py`](scripts/flash_deco_openwrt.py): Automated U-Boot WebFailsafe HTTP/TFTP RAM bootstrap, Dropbear SSH `sysupgrade` streamer, JFFS2 `/overlay` synchronizer, and UCI provisioner.
- [`scripts/generate_deco_openwrt_config.py`](scripts/generate_deco_openwrt_config.py): Programmatic generator for OpenWrt 24.10 `/etc/config/network`, `/etc/config/wireless` (802.11k/v/r/w), and `/usr/sbin/deco-hw-unlock.sh` (`AQL`, `switch0` VLAN/MIBs/IGMPv3, sysctls, and `green:power` LED status).
- [`scripts/tftp_server.py`](scripts/tftp_server.py): Zero-dependency RFC 1350 UDP TFTP server for serving `initramfs-kernel.bin` on `192.168.0.2:69`.
- [`scripts/rea_deco_deconstruct.py`](scripts/rea_deco_deconstruct.py): Clean-room firmware container and `uImage` / SquashFS boundary analyzer.
- [`tests/test_deco_openwrt_seams.py`](tests/test_deco_openwrt_seams.py): 20-test TDD seam suite covering all 6 provisioning and configuration seams.

---

## 3. Local Verification

```bash
python3 -m unittest -v tests/test_deco_openwrt_seams.py
python3 -m compileall -q scripts tests
bash -n scripts/flash-deco-openwrt.sh
```

---

## 4. License & Legal

Licensed under the [MIT License](LICENSE).
Independent, non-commercial open-source project not affiliated with TP-Link, Qualcomm, or the OpenWrt Project (see [`LEGAL.md`](LEGAL.md) and [`SECURITY.md`](SECURITY.md) for statutory router interoperability under `§ 73 Abs. 1 TKG` / `37 C.F.R. § 201.40(b)(12)`, regional RF/DFS regulations, and AS IS warranty disclaimers).
