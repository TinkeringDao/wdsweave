# Legal, Trademark, Interoperability, & RF Regulatory Notice

## 1. Independent Open-Source Project & Non-Affiliation (Nominative Fair Use)

**`wdsweave` — Deterministic OpenWrt 24.10 Hybrid Wired/WDS Mesh Provisioning, 802.11r/k/v Roaming, & HomePlug AV2 Loop-Isolation Toolkit for TP-Link Deco M4R and Deco P9** is an **independent, non-commercial, community-developed free and open-source software and hardware documentation project** created solely to enable mainline OpenWrt installation, standards-based IEEE 802.11k/v/r/w wireless operation, 802.1Q VLAN switch management, and bufferbloat mitigation on user-owned hardware.

- **No Affiliation or Endorsement:** This project is **not affiliated with, authorized by, sponsored by, or endorsed by TP-Link Technologies Co., Ltd. (`TP-Link`), TP-Link Corporation Pte. Ltd., Qualcomm Incorporated (`Qualcomm Atheros`), GigaDevice Semiconductor Inc. (`GD25Q128`), or the OpenWrt Project.**
- **Indication of Intended Purpose & Nominative Fair Use:**
  - Pursuant to **Article 14(1)(c) of Regulation (EU) 2017/1001 (EUTMR)**, settled Court of Justice of the European Union jurisprudence (*Case C-228/03 — Gillette v. LA-Laboratories*; *Case C-63/97 — BMW v. Deenik*), and **US Nominative Fair Use (`15 U.S.C. §§ 1115(b)(4), 1125`**, *New Kids on the Block v. News America Publishing, Inc.*, 971 F.2d 302 (9th Cir. 1992)), third-party product names and trademarks are referenced strictly as a necessary indication of intended purpose and target hardware compatibility of this provisioning and configuration suite:
    - "TP-Link" and "Deco" are trademarks or registered trademarks of **TP-Link Technologies Co., Ltd. / TP-Link Corporation Pte. Ltd.**
    - "Qualcomm", "Atheros", and "HomePlug" are trademarks or registered trademarks of **Qualcomm Incorporated**.
    - "OpenWrt" is a registered trademark of **Software in the Public Interest, Inc. (SPI)**.
  - Zero corporate logos, proprietary trade dress, or OEM marketing assets are included in this repository.

---

## 2. Open-Source License Provenance, Statutory Interoperability, & Hardware Reverse-Engineering Safe Harbor

### 2.1 Open-Source License Provenance (`MIT License`, `SPDX-License-Identifier: MIT`, Zero Proprietary Binaries)
- All Python provisioning orchestrators ([`scripts/flash_deco_openwrt.py`](scripts/flash_deco_openwrt.py)), TFTP bootstrap servers ([`scripts/tftp_server.py`](scripts/tftp_server.py)), UCI/kernel hardware unlock generators ([`scripts/generate_deco_openwrt_config.py`](scripts/generate_deco_openwrt_config.py)), clean-room container inspectors ([`scripts/rea_deco_deconstruct.py`](scripts/rea_deco_deconstruct.py)), TDD seam test suites ([`tests/test_deco_openwrt_seams.py`](tests/test_deco_openwrt_seams.py)), and hardware/RF technical documentation in this repository are original works distributed under the [MIT License](LICENSE) (`SPDX-License-Identifier: MIT`, `Copyright (c) 2026 TinkeringDao`), containing zero proprietary OEM binaries or verbatim firmware blobs.

### 2.2 European Union (`Directive 2009/24/EC` & `Directive (EU) 2016/943`)
1. **Exclusion of Functional Interfaces & Hardware Register Maps from Copyright (`Article 1(2) of Directive 2009/24/EC`):**
   - Under `Article 1(2) of Directive 2009/24/EC` and settled Court of Justice of the European Union precedent (*SAS Institute Inc. v. World Programming Ltd*, Case `C-406/10`, paras. 39–46), ideas, principles, MTD flash partition offsets, GPIO pin assignments, switch register maps (`QCA8337N` / `AR8337`), and network protocol framing (`U-Boot` HTTP/TFTP recovery headers) are **excluded from copyright protection**.
2. **Right to Observe, Study, and Test (`Article 5(3) of Directive 2009/24/EC`):**
   - Permits the lawful user of a computer program and hardware device to observe, study, or test its functioning without prior authorization in order to determine the underlying ideas, partition layouts, and peripheral behavior.
3. **Mandatory Right of Interoperability (`Article 6 of Directive 2009/24/EC`):**
   - Permits independent analysis necessary to achieve the **interoperability** of independently created open-source firmware (`OpenWrt 24.10`) and host provisioning tools with the `TP-Link Deco M4R` and `Deco P9` hardware components (`QCA9563`, `QCA9886`, `QCA8337N`, `GD25Q128`, `QCA7500`).
4. **Statutory Nullity of Contrary EULA Provisions (`Article 8 of Directive 2009/24/EC`):**
   - Under mandatory European Union statutory law, any contractual clauses purporting to restrict or waive rights under `Articles 5(3) or 6 of Directive 2009/24/EC` are **statutorily null and void**.
5. **Lawful Hardware Reverse Engineering (`Article 3(1)(b) of Directive (EU) 2016/943`):**
   - `Article 3(1)(b) of Directive (EU) 2016/943` explicitly authorizes obtaining technical information by observing, examining, disassembling, or testing a product (`TP-Link Deco M4R / P9`) that has been made publicly available on the market or is in the lawful possession of the observer, free from any contractual restriction.

### 2.3 United States (`17 U.S.C. §§ 102(b), 107, 1201(f)`, `18 U.S.C. § 1839(6)(B) (DTSA)`)
1. **Uncopyrightable Systems, Hardware Pinouts, & Methods of Operation (`17 U.S.C. § 102(b)`):**
   - SoC register addresses, flash partition boundaries, and hardware initialization sequences required for peripheral operation constitute uncopyrightable functional facts and methods of operation (*Baker v. Selden*, 101 U.S. 99 (1879); *Google LLC v. Oracle America, Inc.*, 593 U.S. 1 (2021); *Lexmark Int'l, Inc. v. Static Control Components, Inc.*, 387 F.3d 522 (6th Cir. 2004)).
2. **Interoperability & Router Firmware Modification Exemptions (`17 U.S.C. § 1201(f)` & `37 C.F.R. § 201.40(b)(12)`):**
   - Developed exclusively for achieving hardware-software interoperability and installing lawful open-source router firmware on user-owned networking equipment (*Sega Enterprises Ltd. v. Accolade, Inc.*, 977 F.2d 1510 (9th Cir. 1992); Library of Congress / U.S. Copyright Office DMCA Section 1201 Triennial Rulemaking Exemptions for computer programs that operate routers and networking devices).
3. **Defend Trade Secrets Act Reverse-Engineering Safe Harbor (`18 U.S.C. § 1839(6)(B) (DTSA)`):**
   - Under federal law, reverse engineering, independent derivation, and board-level observation of a lawfully acquired product on the open market are explicitly excluded from the definition of "improper means".

---

## 3. Authorized Local Owner Execution Only & US CFAA Compliance (`18 U.S.C. § 1030 (CFAA)`)

In accordance with the **Authorized Local Owner Execution Only** principle and the US Computer Fraud and Abuse Act (`18 U.S.C. § 1030 (CFAA)`, *Van Buren v. United States*, 593 U.S. 374 (2021)):

- **Authorized Local Owner Execution Only:** The provisioning scripts ([`scripts/flash_deco_openwrt.py`](scripts/flash_deco_openwrt.py), [`scripts/tftp_server.py`](scripts/tftp_server.py)) and UCI generators ([`scripts/generate_deco_openwrt_config.py`](scripts/generate_deco_openwrt_config.py)) are designed strictly for installation and execution on `TP-Link Deco M4R` and `Deco P9` hardware owned or explicitly authorized by the operator over a direct local Ethernet link (`192.168.0.1/24` / `192.168.1.1/24`).
- **No Unauthorized Access or Cloud Interaction:** This software does not interact with any third-party cloud infrastructure and operates solely on local point-to-point wired interfaces during user-initiated hardware recovery.

---

## 4. Non-Commercial Open-Source Software Exemption (EU CRA `Regulation (EU) 2024/2847` & EU PLD `Directive (EU) 2024/2853`)

- **EU Cyber Resilience Act Exemption (`Regulation (EU) 2024/2847`, Recitals 15 & 18; `Art. 2(5)`):** This repository is developed, maintained, and supplied strictly as **non-commercial free and open-source software outside the course of any commercial activity**. No fee is charged, no paid support or commercial services are offered, and no personal data is collected or monetized. Accordingly, the authors are neither "manufacturers" (`Art. 3(13)`) nor "open-source software stewards" (`Art. 3(14)`), and CE-marking (`Art. 28`), conformity assessment, and commercial manufacturer obligations under Regulation (EU) 2024/2847 do not apply.
- **EU Product Liability Directive Exemption (`Directive (EU) 2024/2853`, `Art. 2(2)` & Recitals 14, 15, 24):** Pursuant to **Article 2(2)** and **Recitals 14–15 of Directive (EU) 2024/2853**, strict liability under this Directive does not apply to free and open-source software developed or supplied outside the course of a commercial activity.

---

## 5. Radio Frequency (RF), DFS, & Spectrum Regulatory Compliance (`Directive 2014/53/EU (RED)` / `ETSI EN 300 328` / `ETSI EN 301 893` / `FCC 47 C.F.R. Part 15.247 & Part 15E`)

Installing OpenWrt firmware on a dual-band 2.4 GHz / 5 GHz wireless router requires configuring the correct regulatory domain (`option country`). **The hardware owner and operator are solely and exclusively responsible for ensuring that their wireless configuration complies with all applicable national and regional spectrum regulations**, including **Directive 2014/53/EU (RED)**, **ETSI EN 300 328** (2.4 GHz RLAN), **ETSI EN 301 893** (5 GHz RLAN, Dynamic Frequency Selection [DFS], and Transmit Power Control [TPC]), and **FCC 47 C.F.R. Part 15.247 / Part 15E**:

- **Factory `art` Partition Integrity (`mtd5`):** The factory Qualcomm Atheros Radio Test (`art`) partition (`0x00ff0000`–`0x01000000`, `64 KB`) contains board-specific per-channel power calibration and frequency trim tables and is strictly preserved read-only (`read-only` in the Linux Device Tree).
- **2.4 GHz ISM Band (`2412–2472 MHz`, `ETSI EN 300 328`):** Maximum allowed EIRP in the European Union is **`20 dBm` (`100 mW`)**.
- **5 GHz RLAN Bands (`UNII-1`, `UNII-2A`, `UNII-2C`, `UNII-3`, `ETSI EN 301 893`):**
  - Channels `36–48` (`5150–5250 MHz`): Indoor use up to `23 dBm` (`200 mW`) EIRP.
  - Channels `52–64` (`5250–5350 MHz`) and `100–140` (`5470–5725 MHz`): Require active **Dynamic Frequency Selection (DFS)** radar detection (`CAC` / Weather Radar `600 s` on channels `120–128`) and **Transmit Power Control (TPC)**.
  - Channels `149–165` (`5745–5825 MHz`, `SRD`): Limited to **`14 dBm` (`25 mW`) EIRP** in the European Union.

---

## 6. AS IS Warranty Disclaimer

THE SOFTWARE, SCRIPTS, CONFIGURATION TEMPLATES, AND DOCUMENTATION ARE PROVIDED **"AS IS"**, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT (SEE [`LICENSE`](LICENSE)). Under this **AS IS Warranty Disclaimer**, any liability of the authors for negligence or consequential hardware/property damage is expressly excluded to the maximum extent permitted by applicable law.

---

## Addendum: German Statutory References (Applicable to Residents of Germany)

For users, contributors, and maintainers residing or operating in Germany, the European Union directives and legal principles set forth above are implemented into German national law via the following corresponding statutory provisions:

- **Trademark Nominative Fair Use / Indication of Intended Purpose (`§ 23 Abs. 1 Nr. 3 MarkenG`, BGH `I ZR 6/10`):** Under Section 23(1) No. 3 of the German Trademark Act (*Markengesetz*), third-party trademarks and product designations may be used without the proprietor's consent where necessary as an indication of the intended purpose (*Bestimmungsangabe*) of interoperable software/firmware, provided such use complies with honest practices.
- **Software Copyright, Observation, Interoperability, & Non-Circumvention (`§§ 69a Abs. 2 & 5, 69d Abs. 3, 69e, 69f Abs. 2, 69g Abs. 2, 95a UrhG`):** Under the German Copyright Act (*Urheberrechtsgesetz*), ideas, principles, and functional interfaces underlying a computer program are excluded from copyright protection (`§ 69a Abs. 2 Satz 2 UrhG`). Lawful users are entitled to observe, study, and test program behavior (`§ 69d Abs. 3 UrhG`) and perform analysis necessary for interoperability (`§ 69e UrhG`); any contractual clauses purporting to waive or restrict these statutory rights are null and void (`§ 69g Abs. 2 UrhG` — *nichtig*). Computer programs are governed by the special provisions of `§§ 69a–69g UrhG` (`§ 69a Abs. 5`, `§ 69f Abs. 2 UrhG`).
- **Hardware Reverse Engineering & Trade Secrets (`§ 3 Abs. 1 Nr. 2 GeschGehG`, `lit. a & b`):** Section 3(1) No. 2 of the German Trade Secrets Act (*Geschäftsgeheimnisgesetz*) expressly permits obtaining technical information by observing, examining, disassembling, or testing a product or object that has been made publicly available (`lit. a`) or is in the lawful possession of the observer free from any valid duty to limit acquisition (`lit. b`).
- **IT Criminal Law, Terminal Device Freedom, & Property Ownership Scope (`§§ 202a–202c, 303a StGB`, `§ 903 BGB`, `§ 73 Abs. 1 TKG`, *BVerfG 2 BvR 2233/07*):** Under the German Criminal Code (*Strafgesetzbuch*), Civil Code (*Bürgerliches Gesetzbuch*), and Telecommunications Act (`§ 73 Abs. 1 TKG` — *Endgerätefreiheit*), all firmware and provisioning utilities are intended strictly for execution by the lawful hardware owner (`§ 903 BGB`) on their own device data (*eigene Daten*, `§ 303a StGB`).
- **Radio Equipment & Spectrum Regulations (`FuAG`, `TKG`, `BNetzA Vfg 10/2022` & `Vfg 59/2021`):** Within Germany, 2.4 GHz and 5 GHz RLAN transceivers are regulated under the German Radio Equipment Act (*Funkanlagengesetz* — `FuAG`), the Telecommunications Act (*Telekommunikationsgesetz* — `TKG`), and the Federal Network Agency (*Bundesnetzagentur* — `BNetzA`) General Allocations for 2.4 GHz and 5 GHz WAS/RLAN.
- **Gratuitous Open-Source Liability Standard (`§§ 521, 523, 524, 599, 600 BGB`):** Under the German Civil Code provisions governing the gratuitous provision of open-source software and documentation, statutory liability for simple negligence (*einfache Fahrlässigkeit*) and implied warranty defects is excluded.
