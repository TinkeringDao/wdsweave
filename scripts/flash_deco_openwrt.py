#!/usr/bin/env python3
"""
Automated OpenWrt Flasher & Rework Engine for TP-Link Deco M4R / P9.
Autonomous End-to-End Pipeline:
1. Auto-detects USB Ethernet adapter interface and service name on macOS.
2. Stages TFTP boot files (initramfs-kernel.bin).
3. Configures static IP (192.168.0.2 / 24) via passwordless networksetup.
4. Monitors interface for physical carrier link.
5. Polls for U-Boot WebFailsafe recovery HTTP daemon (192.168.0.1:80).
6. Uploads WebFailsafe exploit payload (deco_all_webfailsafe_faux_fw_tftp_v2.bin).
7. Serves OpenWrt initramfs kernel via pure-Python RFC 1350 TFTP server.
8. Detects OpenWrt RAM environment at 192.168.1.1 (SSH).
9. Uploads and triggers permanent SPI NOR flash via sysupgrade -v -n.
10. Waits for reboot and provisions AP bridge network & 802.11k/v/r roaming.
"""

import argparse
import hashlib
import http.client
import os
import re
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import urllib.request
import zlib

from tftp_server import TftpServer

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIRMWARE_DIR = os.path.join(REPO_ROOT, "firmware")
STAGE_DIR = os.path.join(FIRMWARE_DIR, "tftp_stage")
RECOVERY_BIN = os.path.join(FIRMWARE_DIR, "exploits/deco_all_webfailsafe_faux_fw_tftp_v2.bin")
EXPLOIT_BIN = RECOVERY_BIN
INITRAMFS_SRC = os.path.join(FIRMWARE_DIR, "openwrt/openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-initramfs-kernel.bin")
SYSUPGRADE_SRC = os.path.join(FIRMWARE_DIR, "openwrt/openwrt-24.10.8-ath79-generic-tplink_deco-m4r-v1-squashfs-sysupgrade.bin")
MIN_OPENWRT_IMAGE_BYTES = 1024 * 1024


def validate_recovery_image(recovery_path: str):
    """Verify U-Boot WebFailsafe bootstrap payload exists and matches the 32 KB contract."""
    if not os.path.isfile(recovery_path):
        raise FileNotFoundError(f"Missing U-Boot recovery bootstrap payload: {recovery_path}")
    with open(recovery_path, "rb") as f:
        data = f.read()
    if len(data) != 0x8000 or b"fw-type:" not in data or b"tftpboot 0x82000000 initramfs-kernel.bin" not in data:
        raise ValueError(f"Invalid U-Boot recovery bootstrap payload: {recovery_path}")


def validate_deployable_uimage(image_path: str, require_squashfs: bool = False):
    """Verify an OpenWrt MIPS uImage exists, is deployable (>= 1 MB), and passes CRC32 checks."""
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Missing OpenWrt firmware image: {image_path}")
    total_size = os.path.getsize(image_path)
    if total_size < MIN_OPENWRT_IMAGE_BYTES:
        raise ValueError(
            f"Refusing to stage or flash undersized/placeholder OpenWrt image ({total_size:,} bytes < {MIN_OPENWRT_IMAGE_BYTES:,} bytes): {image_path}"
        )
    with open(image_path, "rb") as f:
        hdr = f.read(64)
        body = f.read()
    if len(hdr) < 64:
        raise ValueError(f"Truncated uImage header in {image_path}")
    magic, hcrc, _time, ksize, load, ep, dcrc, os_, arch, type_, _comp = struct.unpack(">IIIIIIIBBBB", hdr[:32])
    if magic != 0x27051956 or arch != 5 or os_ != 5 or type_ != 2 or load != 0x80060000 or ep != 0x80060000:
        raise ValueError(f"uImage header does not match MIPS OpenWrt contract: {image_path}")
    hdr_zero_hcrc = hdr[:4] + b"\x00\x00\x00\x00" + hdr[8:]
    if (zlib.crc32(hdr_zero_hcrc) & 0xFFFFFFFF) != hcrc:
        raise ValueError(f"uImage header CRC32 mismatch in {image_path}")
    kernel_data = body[:ksize] if require_squashfs else body
    if len(kernel_data) != ksize or (zlib.crc32(kernel_data) & 0xFFFFFFFF) != dcrc:
        raise ValueError(f"uImage kernel payload CRC32 mismatch in {image_path}")
    if require_squashfs and body[ksize:ksize + 4] != b"hsqs":
        raise ValueError(f"Missing SquashFS 'hsqs' rootfs boundary in {image_path}")


def list_wired_ethernet_services():
    """Return all present non-Wi-Fi wired/USB Ethernet (service_name, dev) pairs."""
    results = []
    try:
        existing_ifaces = set(subprocess.check_output(["ifconfig", "-l"]).decode().split())
        out = subprocess.check_output(["networksetup", "-listnetworkserviceorder"]).decode()
        matches = re.findall(
            r"\(\d+\)\s+([^\n]+)\n\(Hardware Port:\s+([^,]+),\s+Device:\s+([^)]+)\)",
            out
        )
        for service_name, hw_port, dev in matches:
            if dev in existing_ifaces and dev != "en0" and not dev.startswith("bridge"):
                low_port = hw_port.lower()
                low_srv = service_name.lower()
                if any(k in low_port or k in low_srv for k in ("usb", "lan", "ethernet", "dock", "tbt")):
                    results.append((service_name, dev))
    except Exception as e:
        print(f"[!] Warning during interface scan: {e}")
    return results


def detect_usb_ethernet():
    """Auto-detect active USB Ethernet network service and BSD device name."""
    candidates = list_wired_ethernet_services()
    for service_name, dev in candidates:
        if check_carrier(dev):
            return service_name, dev
    if candidates:
        return candidates[0]
    return "USB 10/100/1000 LAN", "en5"


def stage_tftp_files():
    """Ensure a validated deployable initramfs-kernel.bin is staged for TFTP serving."""
    validate_deployable_uimage(INITRAMFS_SRC, require_squashfs=False)
    os.makedirs(STAGE_DIR, exist_ok=True)
    target = os.path.join(STAGE_DIR, "initramfs-kernel.bin")
    needs_stage = not os.path.exists(target) or os.path.getsize(target) != os.path.getsize(INITRAMFS_SRC)
    if needs_stage:
        print(f"[*] Staging {INITRAMFS_SRC} -> {target}")
        if os.path.islink(target) or os.path.exists(target):
            os.unlink(target)
        try:
            os.symlink(INITRAMFS_SRC, target)
        except OSError:
            shutil.copyfile(INITRAMFS_SRC, target)
    print(f"[+] TFTP stage ready: {target} ({os.path.getsize(target):,} bytes)")


def configure_macos_ip(service_name: str, ip: str, mask: str, router: str):
    """Set manual IPv4 address on macOS network service without sudo."""
    cmd = ["networksetup", "-setmanual", service_name, ip, mask, router]
    print(f"[*] Configuring {service_name} IP: {ip}/{mask} (gateway: {router})")
    subprocess.check_call(cmd)


def check_carrier(interface: str) -> bool:
    """Check if interface has active physical carrier link."""
    try:
        out = subprocess.check_output(["ifconfig", interface]).decode()
        return "status: active" in out
    except Exception:
        return False


def wait_for_carrier(interface: str, service_name: str = "", max_wait_sec=0):
    """Wait for physical carrier link on interface or any newly attached USB/Dock Ethernet."""
    print(f"[*] Checking physical Ethernet link carrier on {interface} (and scanning hotplug adapters)...")
    start = time.time()
    last_print = 0
    configured_services = {service_name} if service_name else set()
    while True:
        candidates = list_wired_ethernet_services()
        if not candidates and interface:
            candidates = [(service_name, interface)]
        for srv, dev in candidates:
            if srv and srv not in configured_services:
                try:
                    configure_macos_ip(srv, "192.168.0.2", "255.255.255.0", "192.168.0.1")
                    configured_services.add(srv)
                except Exception:
                    pass
            if check_carrier(dev):
                print(f"\n[+] Ethernet carrier ACTIVE on {dev} ('{srv}')!")
                return srv or service_name, dev
        now = time.time()
        if max_wait_sec and (now - start) >= max_wait_sec:
            break
        if now - last_print >= 10:
            elapsed = int(now - start)
            limit_str = f" / {max_wait_sec}s" if max_wait_sec else ""
            watched = ", ".join(d for _, d in candidates) or interface
            print(f"[*] Standing by for Ethernet link carrier on [{watched}]... ({elapsed}s elapsed{limit_str})")
            last_print = now
        time.sleep(1.0)
    print(f"\n[-] Carrier wait timed out on {interface}.")
    return None, None


def wait_for_failsafe(target_host="192.168.0.1", timeout_sec=0) -> bool:
    """Wait for TP-Link U-Boot WebFailsafe HTTP server to respond (0 = wait indefinitely)."""
    print(f"[*] Polling Deco U-Boot WebFailsafe at http://{target_host}/...")
    start = time.time()
    last_print = 0
    while True:
        try:
            req = urllib.request.Request(f"http://{target_host}/", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    print(f"\n[+] U-Boot WebFailsafe detected! HTTP {resp.status}")
                    return True
        except Exception:
            pass
        now = time.time()
        if timeout_sec and (now - start) >= timeout_sec:
            break
        if now - last_print >= 10:
            elapsed = int(now - start)
            limit_str = f" / {timeout_sec}s" if timeout_sec else ""
            print(f"[*] Polling http://{target_host}/... ({elapsed}s elapsed{limit_str})")
            last_print = now
        time.sleep(1.0)
    print("\n[-] Timed out waiting for WebFailsafe.")
    return False


def build_recovery_multipart_request(recovery_path=RECOVERY_BIN):
    """Build HTTP path, headers, and multipart body matching Deco U-Boot WebFailsafe form (action='testurl', name='firmware')."""
    with open(recovery_path, "rb") as f:
        file_bytes = f.read()

    boundary = "---------------------------735328452125301328829941198"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="firmware"; filename="{os.path.basename(recovery_path)}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()

    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
        "User-Agent": "Mozilla/5.0",
        "Connection": "close"
    }
    return "/testurl", headers, body


def upload_recovery_image(target_host="192.168.0.1", recovery_path=RECOVERY_BIN) -> bool:
    """Upload U-Boot TFTP recovery bootstrap image via WebFailsafe multipart HTTP POST."""
    validate_recovery_image(recovery_path)
    print(f"\n[*] Uploading U-Boot recovery bootstrap image: {recovery_path} ({os.path.getsize(recovery_path):,} bytes)...")
    path, headers, body = build_recovery_multipart_request(recovery_path)

    try:
        conn = http.client.HTTPConnection(target_host, timeout=10)
        conn.request("POST", path, body=body, headers=headers)
        resp = conn.getresponse()
        print(f"[+] Recovery image uploaded to {path}. HTTP response: {resp.status} {resp.reason}")
        return True
    except (http.client.HTTPException, socket.error) as e:
        print(f"[+] Connection closed by target on {path}: {e} (Expected: U-Boot initiating TFTP bootstrap)")
        return True


upload_exploit = upload_recovery_image


def start_tftp_server(host="0.0.0.0", port=69, root=STAGE_DIR):
    """Start standalone TFTP server in a daemon thread."""
    server = TftpServer(host, port, root)
    t = threading.Thread(target=server.start, daemon=True)
    t.start()
    return server, t


def wait_for_tftp_transfer(
    tftp_server,
    expected_filename="initramfs-kernel.bin",
    timeout_sec=120,
    poll_interval=1.0
) -> bool:
    """Wait until TftpServer finishes serving expected_filename over UDP port 69."""
    print(f"[*] Waiting for U-Boot TFTP download of '{expected_filename}' to complete (timeout: {timeout_sec}s)...")
    start = time.time()
    while time.time() - start < timeout_sec:
        if getattr(tftp_server, "last_transferred_file", None) == expected_filename:
            print(f"[+] Confirmed full TFTP transfer of '{expected_filename}'!")
            return True
        time.sleep(poll_interval)
    print(f"[-] Timed out waiting for TFTP transfer of '{expected_filename}'.")
    return False


def wait_for_ssh(target_ip="192.168.1.1", port=22, timeout_sec=120) -> bool:
    """Wait for OpenWrt SSH port 22 to become reachable."""
    print(f"\n[*] Waiting for OpenWrt SSH at {target_ip}:{port} (timeout: {timeout_sec}s)...")
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            res = s.connect_ex((target_ip, port))
            s.close()
            if res == 0:
                print(f"\n[+] OpenWrt SSH port {port} reachable at {target_ip}!")
                return True
        except Exception:
            pass
        time.sleep(2.0)
        sys.stdout.write("*")
        sys.stdout.flush()
    print("\n[-] SSH wait timed out.")
    return False


def _sh_single_quote(value: str) -> str:
    """Wrap value in POSIX single quotes with embedded single quotes escaped safely for BusyBox ash."""
    return "'" + str(value).replace("'", "'\"'\"'") + "'"


def build_sysupgrade_trigger_command(remote_path="/tmp/sysupgrade.bin") -> str:
    """Return BusyBox ash compatible OpenWrt sysupgrade invocation."""
    return f"sysupgrade -v -n {shlex.quote(remote_path)}"


def flash_permanent_sysupgrade(target_ip="192.168.1.1", sysupgrade_path=SYSUPGRADE_SRC):
    """Stream sysupgrade image over Dropbear SSH, verify SHA-256, and execute sysupgrade -v -n."""
    validate_deployable_uimage(sysupgrade_path, require_squashfs=True)
    print(f"\n[*] Streaming permanent sysupgrade image over SSH: {sysupgrade_path}...")
    remote_path = "/tmp/sysupgrade.bin"

    with open(sysupgrade_path, "rb") as f:
        payload = f.read()
    expected_sha256 = hashlib.sha256(payload).hexdigest()

    ssh_opts = [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10"
    ]
    upload_cmd = ["ssh"] + ssh_opts + [f"root@{target_ip}", f"cat > {remote_path} && sha256sum {remote_path}"]
    print(f"[*] Streaming {len(payload):,} bytes to root@{target_ip}:{remote_path}...")
    out = subprocess.check_output(upload_cmd, input=payload).decode().strip()
    print(f"[*] Remote sha256sum output: {out}")
    remote_sha256 = out.split()[0] if out else ""
    if remote_sha256 != expected_sha256:
        raise RuntimeError(f"SHA-256 mismatch on {remote_path}: expected {expected_sha256}, got {remote_sha256}")
    print(f"[+] Verified remote SHA-256 matches ({expected_sha256})!")

    print("[*] Triggering permanent SPI NOR flash via sysupgrade -v -n...")
    trigger_cmd = build_sysupgrade_trigger_command(remote_path)
    ssh_cmd = ["ssh"] + ssh_opts + [f"root@{target_ip}", trigger_cmd]
    print(f"[*] Running: {' '.join(ssh_cmd)}")
    proc = subprocess.run(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
    output_text = proc.stdout.decode(errors="replace").strip()
    if output_text:
        print(output_text)
    print("[+] Sysupgrade stage2 handed off to procd. Device is writing SPI NOR flash and rebooting!")


def is_persistent_overlay_mounted(df_output: str) -> bool:
    """Return True if persistent JFFS2 overlay (/overlay) is mounted as root overlayfs."""
    return "overlayfs:/overlay" in df_output or " /overlay" in df_output


def wait_for_persistent_overlay(target_ip="192.168.1.1", timeout_sec=120) -> bool:
    """Wait until OpenWrt fstools finishes formatting JFFS2 rootfs_data and mounts /overlay."""
    print(f"[*] Waiting for persistent JFFS2 /overlay mount on {target_ip} (timeout: {timeout_sec}s)...")
    ssh_opts = [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10"
    ]
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            out = subprocess.check_output(["ssh"] + ssh_opts + [f"root@{target_ip}", "df -h"]).decode()
            if is_persistent_overlay_mounted(out):
                print(f"[+] Persistent JFFS2 /overlay is mounted on {target_ip}!")
                return True
        except Exception:
            pass
        time.sleep(3.0)
    print(f"[-] Timed out waiting for persistent /overlay on {target_ip}.")
    return False


def verify_openwrt_release(target_ip="192.168.1.1") -> str:
    """Query /etc/openwrt_release and board metadata over SSH."""
    ssh_opts = [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10"
    ]
    cmd = ["ssh"] + ssh_opts + [f"root@{target_ip}", "cat /etc/openwrt_release; ubus call system board"]
    out = subprocess.check_output(cmd).decode().strip()
    print(f"\n[+] Verified OpenWrt system state at {target_ip}:\n{out}")
    return out


def build_ap_uci_commands(
    final_ip="192.168.1.240",
    gateway="192.168.1.1",
    dns="192.168.1.52",
    ssid="OpenWrt-Mesh",
    key="ChangeMe-80211r-Passphrase"
):
    """Build UCI command list for Deco M4R v1 bridged AP & 802.11k/v/r roaming."""
    q_ip = _sh_single_quote(final_ip)
    q_gw = _sh_single_quote(gateway)
    q_dns = _sh_single_quote(dns)
    q_ssid = _sh_single_quote(ssid)
    q_key = _sh_single_quote(key)
    return [
        # Network: Preserve default eth0.1 swconfig bridge in br-lan and set static LAN IP
        "uci set network.lan.proto='static'",
        f"uci set network.lan.ipaddr={q_ip}",
        "uci set network.lan.netmask='255.255.255.0'",
        f"uci set network.lan.gateway={q_gw}",
        "uci -q delete network.lan.dns || true",
        f"uci add_list network.lan.dns={q_dns}",
        "uci set dhcp.lan.ignore='1'",
        "uci commit network",
        "uci commit dhcp",

        # Wireless: Enable 802.11k/v/r fast roaming on 2.4 GHz (radio0) and 5 GHz (radio1)
        "uci set wireless.radio0.disabled='0'",
        "uci set wireless.radio0.country='DE'",
        f"uci set wireless.default_radio0.ssid={q_ssid}",
        "uci set wireless.default_radio0.encryption='psk2+ccmp'",
        f"uci set wireless.default_radio0.key={q_key}",
        "uci set wireless.default_radio0.ieee80211r='1'",
        "uci set wireless.default_radio0.mobility_domain='4f57'",
        "uci set wireless.default_radio0.ft_over_ds='0'",
        "uci set wireless.default_radio0.ft_psk_generate_local='1'",
        "uci set wireless.default_radio0.ieee80211k='1'",
        "uci set wireless.default_radio0.ieee80211v='1'",
        "uci set wireless.default_radio0.bss_transition='1'",
        "uci set wireless.default_radio0.wnm_sleep_mode='1'",

        "uci set wireless.radio1.disabled='0'",
        "uci set wireless.radio1.country='DE'",
        f"uci set wireless.default_radio1.ssid={q_ssid}",
        "uci set wireless.default_radio1.encryption='psk2+ccmp'",
        f"uci set wireless.default_radio1.key={q_key}",
        "uci set wireless.default_radio1.ieee80211r='1'",
        "uci set wireless.default_radio1.mobility_domain='4f57'",
        "uci set wireless.default_radio1.ft_over_ds='0'",
        "uci set wireless.default_radio1.ft_psk_generate_local='1'",
        "uci set wireless.default_radio1.ieee80211k='1'",
        "uci set wireless.default_radio1.ieee80211v='1'",
        "uci set wireless.default_radio1.bss_transition='1'",
        "uci set wireless.default_radio1.wnm_sleep_mode='1'",
        "uci commit wireless",

        # Restart wireless & network asynchronously
        "wifi reload; /etc/init.d/dnsmasq restart; (sleep 2; /etc/init.d/network restart) >/dev/null 2>&1 &"
    ]


def provision_openwrt_ap(
    target_ip="192.168.1.1",
    final_ip="192.168.1.240",
    ssid="OpenWrt-Mesh",
    key=None,
):
    """Apply AP bridge network, SSH key, and 802.11k/v/r wireless configuration via SSH."""
    if not wait_for_persistent_overlay(target_ip, timeout_sec=120):
        raise RuntimeError(
            f"Persistent JFFS2 /overlay is not mounted on {target_ip}; aborting provisioning so settings are not written to volatile RAM."
        )
    resolved_key = key or os.environ.get("DECO_WIFI_KEY") or "ChangeMe-80211r-Passphrase"
    print(f"\n[*] Provisioning OpenWrt settings at {target_ip}...")
    ssh_opts = [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "LogLevel=ERROR",
        "-o", "ConnectTimeout=10"
    ]

    pubkey_path = os.path.expanduser("~/.ssh/id_ed25519.pub")
    if os.path.isfile(pubkey_path):
        with open(pubkey_path, "rb") as f:
            pubkey_bytes = f.read()
        key_cmd = ["ssh"] + ssh_opts + [
            f"root@{target_ip}",
            "mkdir -p /etc/dropbear && cat > /etc/dropbear/authorized_keys && chmod 600 /etc/dropbear/authorized_keys"
        ]
        subprocess.run(key_cmd, input=pubkey_bytes, check=True)
        print("[+] Installed ~/.ssh/id_ed25519.pub into /etc/dropbear/authorized_keys.")

    commands = build_ap_uci_commands(final_ip=final_ip, ssid=ssid, key=resolved_key)
    full_script = "; ".join(commands)
    ssh_cmd = ["ssh"] + ssh_opts + [f"root@{target_ip}", full_script]
    subprocess.check_call(ssh_cmd)
    print(f"[+] UCI configuration applied! Deco IP transitioned to {final_ip}.")


def main():
    parser = argparse.ArgumentParser(description="TP-Link Deco M4R/P9 OpenWrt Flasher & Rework Engine")
    parser.add_argument("--interface", help="Ethernet device name (e.g. en5). Auto-detected if omitted.")
    parser.add_argument("--service", help="macOS Network Service name. Auto-detected if omitted.")
    parser.add_argument("--step", choices=["stage", "wait", "upload", "tftp", "sysupgrade", "provision", "all"], default="all")
    parser.add_argument("--target-host", default="192.168.0.1")
    parser.add_argument("--openwrt-ip", default="192.168.1.1")
    parser.add_argument("--final-ip", default="192.168.1.240")
    parser.add_argument("--ssid", default="OpenWrt-Mesh", help="802.11k/v/r wireless SSID")
    parser.add_argument("--wifi-key", default=os.environ.get("DECO_WIFI_KEY", "ChangeMe-80211r-Passphrase"), help="WPA2-PSK passphrase (or set DECO_WIFI_KEY)")
    parser.add_argument("--skip-provision", action="store_true", help="Keep OpenWrt at 192.168.1.1 after permanent sysupgrade verification")
    parser.add_argument("--timeout", type=int, default=0, help="Wait timeout in seconds (default: 0 = wait indefinitely)")
    args = parser.parse_args()

    print("=" * 64)
    print("TP-Link Deco M4R / P9 — OpenWrt 24.10.8 Transition Engine")
    print("=" * 64)

    service_name, dev = detect_usb_ethernet()
    if args.interface:
        dev = args.interface
    if args.service:
        service_name = args.service

    print(f"[*] Target USB-to-LAN Interface: {dev} (Service: '{service_name}')")

    if args.step in ["all", "stage", "wait", "upload", "tftp"]:
        stage_tftp_files()

    if args.step == "stage":
        return

    if args.step in ["all", "wait", "upload", "tftp"]:
        # Configure 192.168.0.2 on interface
        configure_macos_ip(service_name, "192.168.0.2", "255.255.255.0", "192.168.0.1")

        # Start TFTP daemon
        tftp_server, _ = start_tftp_server("0.0.0.0", 69, STAGE_DIR)

    if args.step in ["all", "wait", "upload"]:
        # Check carrier link
        if not check_carrier(dev):
            print("\n" + "!" * 64)
            print(f"[!] NOTICE: Physical Ethernet link on {dev} is currently INACTIVE.")
            print("To proceed:")
            print("1. Ensure Ethernet cable is connected between Mac adapter and Deco Port 1.")
            print("2. Put Deco in U-Boot WebFailsafe recovery mode:")
            print("   - Unplug Deco power adapter.")
            print("   - Hold recessed RESET button with pin.")
            print("   - Plug power adapter in while holding RESET.")
            print("   - Release RESET after 5-8 seconds (when top LED stays solid yellow).")
            print("!" * 64 + "\n")
            found_srv, found_dev = wait_for_carrier(dev, service_name=service_name, max_wait_sec=args.timeout)
            if found_srv and found_dev:
                service_name, dev = found_srv, found_dev

        # Poll for WebFailsafe
        if wait_for_failsafe(args.target_host, timeout_sec=args.timeout):
            upload_recovery_image(args.target_host)
            print("[*] Recovery image sent. Waiting for U-Boot to fetch initramfs-kernel.bin via TFTP...")
            if not wait_for_tftp_transfer(tftp_server, "initramfs-kernel.bin", timeout_sec=120):
                raise RuntimeError("TFTP transfer of initramfs-kernel.bin did not complete within 120s.")
        else:
            raise RuntimeError("Could not reach U-Boot WebFailsafe HTTP server.")

    if args.step in ["all", "sysupgrade"]:
        if args.step == "all":
            print("\n[*] Waiting 15 seconds for OpenWrt RAM kernel decompression and boot...")
            time.sleep(15)

        # Switch host IP to 192.168.1.2 to communicate with OpenWrt RAM environment
        configure_macos_ip(service_name, "192.168.1.2", "255.255.255.0", "192.168.1.1")

        if not wait_for_ssh(args.openwrt_ip, port=22, timeout_sec=120):
            raise RuntimeError(f"OpenWrt RAM initramfs SSH at {args.openwrt_ip}:22 did not become reachable.")
        flash_permanent_sysupgrade(args.openwrt_ip)
        print("\n[*] Waiting 65 seconds for SPI NOR flash write and system reboot...")
        time.sleep(65)
        if not wait_for_ssh(args.openwrt_ip, port=22, timeout_sec=150):
            raise RuntimeError(f"OpenWrt permanent image SSH at {args.openwrt_ip}:22 did not come up after sysupgrade.")
        verify_openwrt_release(args.openwrt_ip)
        if not wait_for_persistent_overlay(args.openwrt_ip, timeout_sec=120):
            raise RuntimeError(f"Persistent JFFS2 /overlay did not mount on {args.openwrt_ip} after sysupgrade.")

    if args.step == "provision" or (args.step == "all" and not args.skip_provision):
        print("[*] Applying OpenWrt AP bridge and 802.11k/v/r configuration...")
        if not wait_for_ssh(args.openwrt_ip, port=22, timeout_sec=90):
            raise RuntimeError(f"OpenWrt SSH at {args.openwrt_ip}:22 unreachable for provisioning.")
        provision_openwrt_ap(args.openwrt_ip, final_ip=args.final_ip, ssid=args.ssid, key=args.wifi_key)
        print("\n" + "=" * 64)
        print("[+] SUCCESS: Deco M4R is now permanently running OpenWrt 24.10.8!")
        print(f"[+] AP Bridge IP: {args.final_ip} (Gateway: 192.168.1.1)")
        print(f"[+] 802.11k/v/r Fast Roaming Active: SSID '{args.ssid}' (Domain 4F57)")
        print("=" * 64)


if __name__ == "__main__":
    main()
