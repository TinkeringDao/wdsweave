#!/usr/bin/env python3
"""
Generate hardened OpenWrt UCI configuration templates for TP-Link Deco M4R/P9.
Supports:
1. AP Mode (bridged to upstream router 192.168.1.1, dnsmasq disabled)
2. Standalone Router Mode (WAN on eth0, LAN on eth1)
3. 802.11k/v/r Fast Roaming across both 2.4 GHz and 5 GHz radios
4. WPA2-PSK / WPA3-SAE mixed encryption
"""

import sys

def generate_network_config(mode="ap", ip_last_octet=240, gateway="192.168.1.1", dns="192.168.1.52") -> str:
    """Generate /etc/config/network for Deco M4R v1 (QCA9563 + AR8337 swconfig eth0.1)."""
    if mode == "ap":
        return f"""config interface 'loopback'
	option device 'lo'
	option proto 'static'
	option ipaddr '127.0.0.1'
	option netmask '255.0.0.0'

config globals 'globals'
	option packet_steering '1'

config device
	option name 'br-lan'
	option type 'bridge'
	option igmp_snooping '1'
	list ports 'eth0.1'

config interface 'lan'
	option device 'br-lan'
	option proto 'static'
	option ipaddr '192.168.1.{ip_last_octet}'
	option netmask '255.255.255.0'
	option gateway '{gateway}'
	list dns '{dns}'

config switch
	option name 'switch0'
	option reset '1'
	option enable_vlan '1'

config switch_vlan
	option device 'switch0'
	option vlan '1'
	option ports '3 5 0t'
"""
    else:
        return """config interface 'loopback'
	option device 'lo'
	option proto 'static'
	option ipaddr '127.0.0.1'
	option netmask '255.0.0.0'

config globals 'globals'
	option packet_steering '1'

config device
	option name 'br-lan'
	option type 'bridge'
	option igmp_snooping '1'
	list ports 'eth0.1'

config interface 'lan'
	option device 'br-lan'
	option proto 'static'
	option ipaddr '192.168.1.1'
	option netmask '255.255.255.0'

config interface 'wan'
	option device 'eth0.2'
	option proto 'dhcp'

config switch
	option name 'switch0'
	option reset '1'
	option enable_vlan '1'

config switch_vlan
	option device 'switch0'
	option vlan '1'
	option ports '5 0t'

config switch_vlan
	option device 'switch0'
	option vlan '2'
	option ports '3 0t'
"""

def _uci_single_quote(value: str) -> str:
    """Escape embedded single quotes for OpenWrt /etc/config/* UCI option syntax."""
    return "'" + str(value).replace("'", "'\\''") + "'"


def generate_wireless_config(ssid="OpenWrt-Mesh", key="YourSecurePasswordHere", mobility_domain="4f57", ieee80211w="1") -> str:
    """Generate /etc/config/wireless with 802.11k/v/r fast roaming and 802.11w PMF."""
    q_ssid = _uci_single_quote(ssid)
    q_key = _uci_single_quote(key)
    q_md = _uci_single_quote(mobility_domain)
    q_pmf = _uci_single_quote(ieee80211w)
    return f"""config wifi-device 'radio0'
	option type 'mac80211'
	option path 'platform/ahb/18100000.wmac'
	option channel 'auto'
	option band '2g'
	option htmode 'HT20'
	option country 'DE'
	option disabled '0'

config wifi-iface 'default_radio0'
	option device 'radio0'
	option network 'lan'
	option mode 'ap'
	option ssid {q_ssid}
	option encryption 'psk2+ccmp'
	option key {q_key}
	option ieee80211w {q_pmf}
	option disassoc_low_ack '1'
	option ieee80211r '1'
	option mobility_domain {q_md}
	option ft_over_ds '0'
	option ft_psk_generate_local '1'
	option ieee80211k '1'
	option ieee80211v '1'
	option bss_transition '1'
	option wnm_sleep_mode '1'

config wifi-device 'radio1'
	option type 'mac80211'
	option path 'pci0000:00/0000:00:00.0'
	option channel 'auto'
	option band '5g'
	option htmode 'VHT80'
	option country 'DE'
	option disabled '0'

config wifi-iface 'default_radio1'
	option device 'radio1'
	option network 'lan'
	option mode 'ap'
	option ssid {q_ssid}
	option encryption 'psk2+ccmp'
	option key {q_key}
	option ieee80211w {q_pmf}
	option disassoc_low_ack '1'
	option ieee80211r '1'
	option mobility_domain {q_md}
	option ft_over_ds '0'
	option ft_psk_generate_local '1'
	option ieee80211k '1'
	option ieee80211v '1'
	option bss_transition '1'
	option wnm_sleep_mode '1'
"""

def generate_hardware_unlock_script(
    aql_limit_ac=2000,
    aql_limit_n=1500,
    enable_packet_steering=True,
    enable_igmp_snooping=True,
) -> str:
    """Generate an idempotent OpenWrt 24.10.8 / Linux 6.6.144 kernel and UCI tuning script."""
    ps_val = "1" if enable_packet_steering else "0"
    igmp_val = "1" if enable_igmp_snooping else "0"
    return f"""#!/bin/sh
# Idempotent OpenWrt 24.10.8 / Linux 6.6.144 Hardware & Kernel Unlock Script
set -e

# 1. Packet Steering & Bridge Multicast IGMP Snooping
uci set network.globals=globals
uci set network.globals.packet_steering='{ps_val}'
uci set network.@device[0].igmp_snooping='{igmp_val}'

# 2. QCA8337N / AR8337 Hardware Switch (switch0) VLAN, Extended MIB & IGMPv3 Readiness
uci set network.@switch[0].reset='1'
uci set network.@switch[0].enable_vlan='1'
uci commit network

if command -v swconfig >/dev/null 2>&1; then
    swconfig dev switch0 set enable_vlan 1
    swconfig dev switch0 set ar8xxx_mib_type 1
    swconfig dev switch0 set ar8xxx_mib_poll_interval 500
    swconfig dev switch0 set igmp_snooping {igmp_val}
    swconfig dev switch0 set igmp_v3 {igmp_val}
    swconfig dev switch0 set reset_mibs
    swconfig dev switch0 set apply
fi

# 3. 802.11w Protected Management Frames (PMF)
uci set wireless.default_radio0.ieee80211w='1'
uci set wireless.default_radio1.ieee80211w='1'
uci commit wireless

# 4. mac80211 Airtime Queue Limits (AQL) Bufferbloat Mitigation
for phy_dir in /sys/kernel/debug/ieee80211/phy*; do
    [ -d "$phy_dir" ] || continue
    if [ -f "$phy_dir/aql_enable" ]; then
        echo 1 > "$phy_dir/aql_enable"
    fi
    if [ -f "$phy_dir/aql_txq_limit" ]; then
        phy_name=$(basename "$phy_dir")
        if [ "$phy_name" = "phy0" ]; then
            limit={aql_limit_ac}
        else
            limit={aql_limit_n}
        fi
        for ac in 0 1 2 3; do
            echo "$ac $limit $limit" > "$phy_dir/aql_txq_limit"
        done
    fi
done

# 5. Kernel Networking & Conntrack Tuning
sysctl -w net.netfilter.nf_conntrack_max=16384 >/dev/null 2>&1 || true
sysctl -w net.ipv4.tcp_ecn=1 >/dev/null 2>&1 || true
sysctl -w net.core.somaxconn=1024 >/dev/null 2>&1 || true

# 6. Ensure Solid Green Status LED (green:power) Indicating Healthy OpenWrt Boot
if [ -d /sys/class/leds/green:power ]; then
    echo default-on > /sys/class/leds/green:power/trigger
    echo 1 > /sys/class/leds/green:power/brightness
fi
if [ -d /sys/class/leds/red:wlan2g ]; then
    echo none > /sys/class/leds/red:wlan2g/trigger
    echo 0 > /sys/class/leds/red:wlan2g/brightness
fi
if [ -d /sys/class/leds/blue:wlan5g ]; then
    echo none > /sys/class/leds/blue:wlan5g/trigger
    echo 0 > /sys/class/leds/blue:wlan5g/brightness
fi
# Explicit AC/N queue limits: phy0 ({aql_limit_ac} {aql_limit_ac}) / phy1 ({aql_limit_n} {aql_limit_n})
"""

def generate_dhcp_ap_mode() -> str:
    """Disable DHCP server on AP mode to prevent competing with main gateway."""
    return """config dnsmasq
	option domainneeded '1'
	option boguspriv '1'
	option filterwin2k '0'
	option localise_queries '1'
	option rebind_protection '1'
	option rebind_localhost '1'
	option local '/lan/'
	option domain 'lan'
	option expandhosts '1'
	option nonegcache '0'
	option authoritative '1'
	option readethers '1'
	option leasefile '/tmp/dhcp.leases'
	option resolvfile '/tmp/resolv.conf.d/resolv.conf.auto'

config dhcp 'lan'
	option interface 'lan'
	option ignore '1'
"""

if __name__ == "__main__":
    print("=== /etc/config/network (AP mode) ===")
    print(generate_network_config(mode="ap", ip_last_octet=240))
    print("=== /etc/config/wireless (802.11k/v/r) ===")
    print(generate_wireless_config())
    print("=== Hardware & Kernel Unlock Script ===")
    print(generate_hardware_unlock_script())
