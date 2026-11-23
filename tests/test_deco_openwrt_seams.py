#!/usr/bin/env python3
"""
TDD Seam Test Suite for TP-Link Deco M4R/P9 OpenWrt Flashing & Rework.
Tests:
- Seam 1: Exploit payload integrity & U-Boot shellcode vectors
- Seam 2: OpenWrt uImage binary contract & CRC32 verification
- Seam 3: Sysupgrade flash geometry & SquashFS boundary
- Seam 4: TFTP recovery staging & RRQ packet contract
- Seam 5: OpenWrt UCI network & 802.11k/v/r roaming contract
"""

import atexit
import os
import struct
import tempfile
import unittest
import zlib

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_REAL_STOCK_BIN = os.path.join(REPO_ROOT, "firmware/stock/M4R_en_1.8.0_Build_20250721_Rel.49216/M4R_en_1.8.0_Build_20250721_Rel.49216.bin")
_REAL_EXPLOIT_BIN = os.path.join(REPO_ROOT, "firmware/exploits/deco_all_webfailsafe_faux_fw_tftp_v2.bin")
_REAL_INITRAMFS_BIN = os.path.join(REPO_ROOT, "firmware/openwrt/openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-initramfs-kernel.bin")
_REAL_SYSUPGRADE_BIN = os.path.join(REPO_ROOT, "firmware/openwrt/openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-squashfs-sysupgrade.bin")

_FIXTURE_TMPDIR = None


def _resolve_firmware_test_paths():
    """Use real local images if present (>= deployable size); otherwise synthesize isolated temp fixtures outside REPO_ROOT."""
    global _FIXTURE_TMPDIR
    has_real = (
        os.path.isfile(_REAL_EXPLOIT_BIN)
        and os.path.getsize(_REAL_EXPLOIT_BIN) == 0x8000
        and os.path.isfile(_REAL_INITRAMFS_BIN)
        and os.path.getsize(_REAL_INITRAMFS_BIN) >= 1024 * 1024
        and os.path.isfile(_REAL_SYSUPGRADE_BIN)
        and os.path.getsize(_REAL_SYSUPGRADE_BIN) >= 1024 * 1024
    )
    if has_real:
        return _REAL_STOCK_BIN, _REAL_EXPLOIT_BIN, _REAL_INITRAMFS_BIN, _REAL_SYSUPGRADE_BIN

    _FIXTURE_TMPDIR = tempfile.TemporaryDirectory(prefix="deco_seam_fixtures_")
    atexit.register(_FIXTURE_TMPDIR.cleanup)
    base = _FIXTURE_TMPDIR.name

    exploit_bin = os.path.join(base, "deco_all_webfailsafe_faux_fw_tftp_v2.bin")
    initramfs_bin = os.path.join(base, "openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-initramfs-kernel.bin")
    sysupgrade_bin = os.path.join(base, "openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-squashfs-sysupgrade.bin")

    buf = bytearray(0x8000)
    tag = b"fw-type:"
    buf[0:len(tag)] = tag
    ret_offset = 8 + 256 + 12
    struct.pack_into(">I", buf, ret_offset, 0x80060200)
    cmds = (
        b"setenv serverip 192.168.0.2\x00"
        b"setenv ipaddr 192.168.0.1\x00"
        b"tftpboot 0x82000000 initramfs-kernel.bin\x00"
        b"bootm 0x82000000\x00"
    )
    buf[512:512 + len(cmds)] = cmds
    with open(exploit_bin, "wb") as f:
        f.write(buf)

    payload = b"LZMA_KERNEL_PAYLOAD" * 64
    dcrc = zlib.crc32(payload) & 0xFFFFFFFF
    name = b"MIPS OpenWrt Linux-6.6.144".ljust(32, b"\x00")
    hdr_no_crc = struct.pack(
        ">IIIIIIIBBBB",
        0x27051956,
        0,
        1700000000,
        len(payload),
        0x80060000,
        0x80060000,
        dcrc,
        5,
        5,
        2,
        3,
    ) + name
    hcrc = zlib.crc32(hdr_no_crc) & 0xFFFFFFFF
    hdr = hdr_no_crc[:4] + struct.pack(">I", hcrc) + hdr_no_crc[8:]
    with open(initramfs_bin, "wb") as f:
        f.write(hdr + payload)
    with open(sysupgrade_bin, "wb") as f:
        f.write(hdr + payload + b"hsqs" + b"\x00" * 1024)

    return _REAL_STOCK_BIN, exploit_bin, initramfs_bin, sysupgrade_bin


STOCK_BIN, EXPLOIT_BIN, INITRAMFS_BIN, SYSUPGRADE_BIN = _resolve_firmware_test_paths()


class TestDecoExploitPayloadSeam(unittest.TestCase):
    """Verifies Seam 1: Exploit payload integrity and shellcode command strings."""

    def test_exploit_binary_exists(self):
        self.assertTrue(os.path.isfile(EXPLOIT_BIN), "Exploit binary missing")

    def test_exploit_buffer_overflow_pattern(self):
        with open(EXPLOIT_BIN, "rb") as f:
            data = f.read()

        # Check total size is exactly 32 KB (0x8000)
        self.assertEqual(len(data), 0x8000, "Exploit payload must be 32,768 bytes")

        # Check fw-type tag and 256-byte overflow
        fw_type_idx = data.find(b"fw-type:")
        self.assertNotEqual(fw_type_idx, -1, "Missing fw-type: tag")

        # Verify return address overwrite
        ret_offset = fw_type_idx + 8 + 256 + 12
        ret_addr = struct.unpack(">I", data[ret_offset:ret_offset+4])[0]
        self.assertEqual(ret_addr, 0x80060200, "Return address must overwrite to 0x80060200")

    def test_exploit_shellcode_commands(self):
        with open(EXPLOIT_BIN, "rb") as f:
            data = f.read()

        expected_commands = [
            b"setenv serverip 192.168.0.2",
            b"setenv ipaddr 192.168.0.1",
            b"tftpboot 0x82000000 initramfs-kernel.bin",
            b"bootm 0x82000000"
        ]
        for cmd in expected_commands:
            self.assertIn(cmd, data, f"Missing shellcode command: {cmd}")


class TestOpenWrtUImageContractSeam(unittest.TestCase):
    """Verifies Seam 2: OpenWrt uImage binary header contract and CRCs."""

    def test_initramfs_uimage_header(self):
        self.assertTrue(os.path.isfile(INITRAMFS_BIN), "Initramfs kernel missing")
        with open(INITRAMFS_BIN, "rb") as f:
            hdr = f.read(64)
            data = f.read()

        magic, hcrc, time, size, load, ep, dcrc, os_, arch, type_, comp = struct.unpack(">IIIIIIIBBBB", hdr[:32])
        name = hdr[32:64].split(b"\x00")[0].decode()

        self.assertEqual(magic, 0x27051956, "Invalid uImage magic")
        self.assertEqual(arch, 5, "Target architecture must be MIPS (5)")
        self.assertEqual(os_, 5, "Target OS must be Linux (5)")
        self.assertEqual(type_, 2, "Image type must be Kernel (2)")
        self.assertEqual(comp, 3, "Compression must be LZMA (3)")
        self.assertEqual(load, 0x80060000, "Kernel load address must be 0x80060000")
        self.assertEqual(ep, 0x80060000, "Kernel entry point must be 0x80060000")
        self.assertIn("Linux-6.6", name, "Kernel version must be Linux 6.6")

        # Verify Data CRC
        computed_dcrc = zlib.crc32(data) & 0xFFFFFFFF
        self.assertEqual(computed_dcrc, dcrc, "Data CRC mismatch in initramfs image")

        # Verify Header CRC (with hcrc field zeroed)
        hdr_zero_hcrc = hdr[:4] + b"\x00\x00\x00\x00" + hdr[8:]
        computed_hcrc = zlib.crc32(hdr_zero_hcrc) & 0xFFFFFFFF
        self.assertEqual(computed_hcrc, hcrc, "Header CRC mismatch in initramfs image")


class TestSysupgradeFlashGeometrySeam(unittest.TestCase):
    """Verifies Seam 3: Sysupgrade image flash layout and SquashFS boundaries."""

    def test_sysupgrade_layout(self):
        self.assertTrue(os.path.isfile(SYSUPGRADE_BIN), "Sysupgrade binary missing")
        with open(SYSUPGRADE_BIN, "rb") as f:
            full_data = f.read()

        # Parse uImage
        magic, hcrc, time, size, load, ep, dcrc, os_, arch, type_, comp = struct.unpack(">IIIIIIIBBBB", full_data[:32])
        self.assertEqual(magic, 0x27051956, "Invalid uImage magic")

        # SquashFS must immediately follow uImage header (64 bytes) + kernel payload (size bytes)
        squashfs_offset = 64 + size
        self.assertTrue(len(full_data) > squashfs_offset + 4, "Image truncated before SquashFS")
        squashfs_magic = full_data[squashfs_offset:squashfs_offset+4]
        self.assertEqual(squashfs_magic, b"hsqs", "SquashFS magic 'hsqs' not found at expected boundary")

        # Assert flash budget: SPI NOR Flash is 16 MB (16,777,216 B)
        # Safe firmware budget is ~15 MB (allowing 1 MB for U-Boot, ART, config)
        max_allowed_bytes = 15 * 1024 * 1024
        self.assertLess(len(full_data), max_allowed_bytes, "Sysupgrade image exceeds 15 MB flash budget")


class TestTftpStagingSeam(unittest.TestCase):
    """Verifies Seam 4: TFTP recovery staging environment and filename contract."""

    def test_tftp_filename_contract(self):
        # Exploit requests 'initramfs-kernel.bin'
        expected_req_name = "initramfs-kernel.bin"
        with tempfile.TemporaryDirectory(prefix="deco_tftp_stage_") as tftp_staging_dir:
            target_file = os.path.join(tftp_staging_dir, expected_req_name)
            os.symlink(INITRAMFS_BIN, target_file)

            self.assertTrue(os.path.isfile(target_file), f"Staged file {expected_req_name} must exist")
            self.assertEqual(os.path.getsize(target_file), os.path.getsize(INITRAMFS_BIN), "Staged file size mismatch")

    def test_tftp_packet_encoding(self):
        # TFTP Read Request (RRQ) Opcode = 1, Mode = octet
        filename = b"initramfs-kernel.bin"
        mode = b"octet"
        rrq_pkt = struct.pack(">H", 1) + filename + b"\x00" + mode + b"\x00"

        # Verify decoding
        opcode = struct.unpack(">H", rrq_pkt[:2])[0]
        self.assertEqual(opcode, 1, "RRQ opcode must be 1")
        parts = rrq_pkt[2:].split(b"\x00")
        self.assertEqual(parts[0], filename)
        self.assertEqual(parts[1].lower(), mode)


class TestOpenWrtUciConfigSeam(unittest.TestCase):
    """Verifies Seam 5: Network template, 802.11k/v/r/w roaming, and kernel/hardware unlock tuning."""

    def setUp(self):
        from scripts.generate_deco_openwrt_config import (
            generate_hardware_unlock_script,
            generate_network_config,
            generate_wireless_config,
        )
        self.gen_network = generate_network_config
        self.gen_wireless = generate_wireless_config
        self.gen_unlock = generate_hardware_unlock_script

    def test_network_config_ap_client_mode(self):
        cfg = self.gen_network(mode="ap", ip_last_octet=240, gateway="192.168.1.1", dns="192.168.1.52")
        self.assertIn("config interface 'lan'", cfg)
        self.assertIn("option proto 'static'", cfg)
        self.assertIn("option ipaddr '192.168.1.240'", cfg)
        self.assertIn("option netmask '255.255.255.0'", cfg)
        self.assertIn("option gateway '192.168.1.1'", cfg)
        self.assertIn("list dns '192.168.1.52'", cfg)
        self.assertIn("list ports 'eth0.1'", cfg)
        self.assertIn("option ports '3 5 0t'", cfg)
        self.assertIn("option packet_steering '1'", cfg)
        self.assertIn("option igmp_snooping '1'", cfg)
        self.assertNotIn("list ports 'eth1'", cfg)
        self.assertNotIn("list ports 'eth0'\n", cfg)

    def test_wireless_config_fast_roaming(self):
        cfg = self.gen_wireless(ssid="OpenWrt-Mesh", key="ValidSecretPassword123", mobility_domain="4f57")
        # Radio definitions
        self.assertIn("config wifi-device 'radio0'", cfg)
        self.assertIn("config wifi-device 'radio1'", cfg)

        # Fast Roaming 802.11r
        self.assertIn("option ieee80211r '1'", cfg)
        self.assertIn("option mobility_domain '4f57'", cfg)
        self.assertIn("option ft_over_ds '0'", cfg)
        self.assertIn("option ft_psk_generate_local '1'", cfg)

        # 802.11k Radio Resource Management
        self.assertIn("option ieee80211k '1'", cfg)

        # 802.11v BSS Transition Management
        self.assertIn("option ieee80211v '1'", cfg)
        self.assertIn("option bss_transition '1'", cfg)
        self.assertIn("option wnm_sleep_mode '1'", cfg)

        # 802.11w Protected Management Frames
        self.assertIn("option ieee80211w '1'", cfg)

        # WPA2/WPA3 Mixed or WPA2-PSK
        self.assertIn("option encryption 'psk2+ccmp'", cfg)

    def test_generate_hardware_unlock_script_defaults(self):
        import subprocess
        script = self.gen_unlock()
        self.assertTrue(script.startswith("#!/bin/sh"), "Unlock script must start with #!/bin/sh")
        self.assertIn("network.globals.packet_steering='1'", script)
        self.assertIn("igmp_snooping='1'", script)
        self.assertIn("/sys/kernel/debug/ieee80211/phy", script)
        self.assertIn("aql_txq_limit", script)
        self.assertIn("2000 2000", script)
        self.assertIn("1500 1500", script)
        self.assertIn("ieee80211w='1'", script)
        self.assertIn("switch0", script)
        self.assertIn("reset_mibs", script)
        self.assertIn("ar8xxx_mib_type 1", script)
        self.assertIn("green:power", script)
        proc = subprocess.run(["/bin/sh", "-n"], input=script.encode(), capture_output=True)
        self.assertEqual(proc.returncode, 0, f"Invalid POSIX shell syntax: {proc.stderr.decode()}")

    def test_generate_hardware_unlock_script_custom_parameters(self):
        script = self.gen_unlock(
            aql_limit_ac=1800,
            aql_limit_n=1200,
            enable_packet_steering=False,
            enable_igmp_snooping=False,
        )
        self.assertIn("network.globals.packet_steering='0'", script)
        self.assertIn("igmp_snooping='0'", script)
        self.assertIn("1800 1800", script)
        self.assertIn("1200 1200", script)


class TestFlasherOrchestratorSeam(unittest.TestCase):
    """Verifies Seam 6: TFTP synchronization, Dropbear SSH streaming, and swconfig bridge preservation."""

    def test_wait_for_tftp_transfer_synchronization(self):
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        class DummyTftpServer:
            def __init__(self):
                self.last_transferred_file = None

        srv = DummyTftpServer()
        self.assertFalse(flasher.wait_for_tftp_transfer(srv, "initramfs-kernel.bin", timeout_sec=0.2, poll_interval=0.05))
        srv.last_transferred_file = "initramfs-kernel.bin"
        self.assertTrue(flasher.wait_for_tftp_transfer(srv, "initramfs-kernel.bin", timeout_sec=0.5, poll_interval=0.05))

    def test_build_recovery_multipart_contract(self):
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        path, headers, body = flasher.build_recovery_multipart_request(EXPLOIT_BIN)
        self.assertEqual(path, "/testurl", "Deco U-Boot recovery form action must be /testurl")
        self.assertIn(b'name="firmware"', body, "Multipart field name must be 'firmware'")
        self.assertIn("multipart/form-data; boundary=", headers["Content-Type"])

    def test_build_sysupgrade_trigger_command_no_nohup(self):
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        cmd = flasher.build_sysupgrade_trigger_command("/tmp/sysupgrade.bin")
        self.assertEqual(cmd, "sysupgrade -v -n /tmp/sysupgrade.bin")
        self.assertNotIn("nohup", cmd, "OpenWrt BusyBox ash does not include nohup")

    def test_is_persistent_overlay_mounted(self):
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        tmpfs_df = "overlayfs:/tmp/root 59.1M 56.0K 59.1M 0% /\n"
        jffs2_df = "/dev/mtdblock4 7.2M 360.0K 6.8M 5% /overlay\noverlayfs:/overlay 7.2M 360.0K 6.8M 5% /\n"
        self.assertFalse(flasher.is_persistent_overlay_mounted(tmpfs_df))
        self.assertTrue(flasher.is_persistent_overlay_mounted(jffs2_df))

    def test_build_ap_uci_commands_preserves_swconfig_bridge(self):
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        cmds = flasher.build_ap_uci_commands(final_ip="192.168.1.240")
        joined = "\n".join(cmds)
        self.assertIn("uci set network.lan.ipaddr='192.168.1.240'", joined)
        self.assertIn("uci set dhcp.lan.ignore='1'", joined)
        self.assertNotIn("ports='eth1'", joined)
        self.assertNotIn("ports='eth0'", joined)

    def test_ci_fixtures_do_not_pollute_repo_firmware_dir(self):
        target_specs = [
            (_REAL_EXPLOIT_BIN, 0x8000),
            (_REAL_INITRAMFS_BIN, 1024 * 1024),
            (_REAL_SYSUPGRADE_BIN, 1024 * 1024),
        ]
        for fpath, min_size in target_specs:
            if os.path.isfile(fpath):
                self.assertGreaterEqual(
                    os.path.getsize(fpath),
                    min_size,
                    f"Synthetic placeholder {fpath} leaked into flasher firmware/ path",
                )

    def test_stage_tftp_files_rejects_synthetic_initramfs(self):
        import sys
        import tempfile
        from unittest import mock
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        with tempfile.TemporaryDirectory() as tmpdir:
            fake_initramfs = os.path.join(tmpdir, "fake-initramfs.bin")
            with open(INITRAMFS_BIN, "rb") as src, open(fake_initramfs, "wb") as dst:
                dst.write(src.read()[:1280])
            with mock.patch.object(flasher, "INITRAMFS_SRC", fake_initramfs), \
                 mock.patch.object(flasher, "STAGE_DIR", os.path.join(tmpdir, "stage")):
                with self.assertRaises((ValueError, RuntimeError)):
                    flasher.stage_tftp_files()

    def test_provision_aborts_when_persistent_overlay_unmounted(self):
        import sys
        from unittest import mock
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        with mock.patch.object(flasher, "wait_for_persistent_overlay", return_value=False), \
             mock.patch.object(flasher.subprocess, "check_call") as mock_call, \
             mock.patch.object(flasher.subprocess, "run") as mock_run:
            with self.assertRaises(RuntimeError):
                flasher.provision_openwrt_ap("192.168.1.1", final_ip="192.168.1.240")
            mock_call.assert_not_called()
            mock_run.assert_not_called()

    def test_build_ap_uci_commands_shell_escapes_ssid_and_key(self):
        import subprocess
        import sys
        sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
        import flash_deco_openwrt as flasher

        tricky_ssid = "Lab's $(uname)"
        tricky_key = "foo'; echo INJECTED; #"
        cmds = flasher.build_ap_uci_commands(
            final_ip="192.168.1.240",
            ssid=tricky_ssid,
            key=tricky_key,
        )
        # Execute all uci commands (all except the final reload line) in POSIX /bin/sh with a stub uci function
        uci_only = "; ".join(cmds[:-1])
        harness = f'uci() {{ printf "UCI:%s\\n" "$*"; }}; {uci_only}'
        proc = subprocess.run(["/bin/sh", "-c", harness], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Shell syntax failed: {proc.stderr}")
        lines = proc.stdout.splitlines()
        self.assertNotIn("INJECTED", lines, "Shell metacharacters in key executed arbitrary command")
        self.assertNotIn("Darwin", proc.stdout, "Command substitution $(uname) executed in shell")
        self.assertIn(f"UCI:set wireless.default_radio0.ssid={tricky_ssid}", lines)
        self.assertIn(f"UCI:set wireless.default_radio0.key={tricky_key}", lines)


if __name__ == "__main__":
    unittest.main()
