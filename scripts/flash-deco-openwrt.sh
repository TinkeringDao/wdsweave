#!/usr/bin/env bash
#
# Automated OpenWrt Flasher Wrapper for TP-Link Deco M4R/P9
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "================================================================"
echo "TP-Link Deco M4R / P9 — OpenWrt 24.10.8 Transition Engine"
echo "================================================================"

# 1. Run Seam Tests
echo "[*] Step 1: Running TDD Seam Verification Suite..."
python3 -m unittest "${REPO_ROOT}/tests/test_deco_openwrt_seams.py"

# 2. Stage TFTP files
echo "[*] Step 2: Staging TFTP binaries..."
python3 "${SCRIPT_DIR}/flash_deco_openwrt.py" --step stage

# 3. Launch flasher orchestrator (auto-detects USB-to-LAN interface)
echo "[*] Step 3: Launching flasher orchestrator..."
python3 "${SCRIPT_DIR}/flash_deco_openwrt.py" --step all
