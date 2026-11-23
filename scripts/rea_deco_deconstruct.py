#!/usr/bin/env python3
"""
REA (`morluto/rea`) Firmware Domain Decomposition & Analysis for TP-Link Deco M4R/P9.
Analyzes:
1. Stock TP-Link Firmware (M4R 1.8.0 Build 20250721)
2. U-Boot WebFailsafe Exploit Payload (deco_all_webfailsafe_faux_fw_tftp_v2.bin)
3. OpenWrt 24.10.8 Initramfs Kernel (tplink_deco-m4r-v1-initramfs-kernel.bin)
4. OpenWrt 24.10.8 SquashFS Sysupgrade (tplink_deco-m4r-v1-squashfs-sysupgrade.bin)
"""

import hashlib
import json
import os
import struct
import sys

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def parse_uimage(data: bytes, offset: int):
    if len(data) < offset + 64:
        return None
    magic = struct.unpack(">I", data[offset:offset+4])[0]
    if magic != 0x27051956:
        return None
    hcrc, time, size, load, ep, dcrc, os_, arch, type_, comp = struct.unpack(">IIIIIIBBBB", data[offset+4:offset+32])
    name = data[offset+32:offset+64].split(b"\x00")[0].decode(errors="replace")
    
    os_map = {1: "openbsd", 2: "netbsd", 3: "freebsd", 4: "4.4bsd", 5: "linux", 6: "vxworks", 7: "qnx", 8: "u-boot"}
    arch_map = {1: "ppc", 2: "arm", 3: "x86", 4: "mips", 5: "mips", 6: "arm64", 7: "riscv"}
    type_map = {1: "standalone", 2: "kernel", 3: "ramdisk", 4: "multi", 5: "firmware", 6: "script", 7: "filesystem"}
    comp_map = {0: "none", 1: "gzip", 2: "bzip2", 3: "lzma", 4: "lzo", 5: "lz4", 6: "zstd"}

    return {
        "offset": offset,
        "offset_hex": f"0x{offset:08X}",
        "magic": f"0x{magic:08X}",
        "header_crc": f"0x{hcrc:08X}",
        "timestamp": time,
        "data_size": size,
        "data_crc": f"0x{dcrc:08X}",
        "load_address": f"0x{load:08X}",
        "entry_point": f"0x{ep:08X}",
        "os": os_map.get(os_, f"unknown({os_})"),
        "arch": arch_map.get(arch, f"unknown({arch})"),
        "type": type_map.get(type_, f"unknown({type_})"),
        "compression": comp_map.get(comp, f"unknown({comp})"),
        "image_name": name,
    }

def analyze_stock_fw(path: str):
    with open(path, "rb") as f:
        data = f.read()
    
    size = len(data)
    # Check TP-Link header
    header_raw = data[:512]
    fw_type_idx = header_raw.find(b"fw-type:")
    fw_type = "unknown"
    if fw_type_idx != -1:
        fw_type = header_raw[fw_type_idx:fw_type_idx+32].split(b"\n")[0].split(b"\x00")[0].decode(errors="replace")

    # Find uImage
    uimages = []
    pos = 0
    while True:
        idx = data.find(b"\x27\x05\x19\x56", pos)
        if idx == -1:
            break
        uimg = parse_uimage(data, idx)
        if uimg:
            uimages.append(uimg)
        pos = idx + 4

    # Find SquashFS
    squashfs_offsets = []
    for magic in [b"hsqs", b"sqsh"]:
        pos = 0
        while True:
            idx = data.find(magic, pos)
            if idx == -1:
                break
            squashfs_offsets.append({"magic": magic.decode(), "offset": idx, "offset_hex": f"0x{idx:08X}"})
            pos = idx + 4

    return {
        "file": os.path.basename(path),
        "file_size": size,
        "sha256": sha256_file(path),
        "md5": md5_file(path),
        "vendor_header": {
            "fw_type": fw_type,
            "header_bytes_prefix_hex": header_raw[:32].hex()
        },
        "uimages": uimages,
        "squashfs_filesystems": squashfs_offsets
    }

def analyze_exploit(path: str):
    with open(path, "rb") as f:
        data = f.read()
    
    size = len(data)
    fw_type_idx = data.find(b"fw-type:")
    overflow_len = 0
    ret_addr = None
    if fw_type_idx != -1:
        # Check overflow payload
        ret_offset = fw_type_idx + 8 + 256 + 12
        if len(data) >= ret_offset + 4:
            ret_addr = f"0x{struct.unpack('>I', data[ret_offset:ret_offset+4])[0]:08X}"
            overflow_len = 256

    strings_found = []
    for needle in [b"setenv serverip", b"setenv ipaddr", b"tftpboot", b"bootm"]:
        idx = data.find(needle)
        if idx != -1:
            end = data.find(b"\x00", idx)
            strings_found.append({
                "string": data[idx:end if end != -1 else idx+40].decode(errors="replace"),
                "offset": idx,
                "offset_hex": f"0x{idx:08X}"
            })

    return {
        "file": os.path.basename(path),
        "file_size": size,
        "sha256": sha256_file(path),
        "md5": md5_file(path),
        "exploit_details": {
            "target_service": "U-Boot WebFailsafe HTTPD (sscanf stack buffer overflow)",
            "vulnerability_parameter": "fw-type",
            "stack_buffer_size": overflow_len,
            "saved_registers_clobbered": "$s0, $s1, $s2",
            "overwritten_return_address": ret_addr,
            "embedded_shellcode_commands": strings_found
        }
    }

def analyze_openwrt_image(path: str, kind: str):
    with open(path, "rb") as f:
        data = f.read()

    uimages = []
    pos = 0
    while True:
        idx = data.find(b"\x27\x05\x19\x56", pos)
        if idx == -1:
            break
        uimg = parse_uimage(data, idx)
        if uimg:
            uimages.append(uimg)
        pos = idx + 4

    squashfs_offsets = []
    for magic in [b"hsqs", b"sqsh"]:
        pos = 0
        while True:
            idx = data.find(magic, pos)
            if idx == -1:
                break
            squashfs_offsets.append({"magic": magic.decode(), "offset": idx, "offset_hex": f"0x{idx:08X}"})
            pos = idx + 4

    return {
        "file": os.path.basename(path),
        "image_kind": kind,
        "file_size": len(data),
        "sha256": sha256_file(path),
        "md5": md5_file(path),
        "uimages": uimages,
        "squashfs_filesystems": squashfs_offsets
    }

def main():
    root = os.path.abspath(os.path.dirname(__file__) + "/..")
    stock_path = os.path.join(root, "firmware/stock/M4R_en_1.8.0_Build_20250721_Rel.49216/M4R_en_1.8.0_Build_20250721_Rel.49216.bin")
    exploit_path = os.path.join(root, "firmware/exploits/deco_all_webfailsafe_faux_fw_tftp_v2.bin")
    owrt_initramfs_path = os.path.join(root, "firmware/openwrt/openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-initramfs-kernel.bin")
    owrt_sysupgrade_path = os.path.join(root, "firmware/openwrt/openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-squashfs-sysupgrade.bin")

    report = {
        "architecture": "MIPS 24Kc (Qualcomm Atheros QCA9563)",
        "stock_firmware": analyze_stock_fw(stock_path),
        "exploit_payload": analyze_exploit(exploit_path),
        "openwrt_initramfs": analyze_openwrt_image(owrt_initramfs_path, "initramfs-ram-bootstrap"),
        "openwrt_sysupgrade": analyze_openwrt_image(owrt_sysupgrade_path, "squashfs-flash-permanent"),
        "comparative_analysis": {
            "kernel_upgrade": "Linux 3.3.8 (Stock 2012 baseline) -> Linux 6.6.144 (OpenWrt 24.10.8)",
            "memory_execution_seam": {
                "u_boot_exploit_jump": "0x80060200",
                "u_boot_load_address": "0x80060000",
                "tftp_staged_ram_address": "0x82000000",
                "tftp_staged_filename": "initramfs-kernel.bin"
            }
        }
    }

    out_dir = os.path.join(root, "docs/openwrt_deco")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "rea_deco_decomposition_report.json")
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Decomposition report written to: {out_file}")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
