#!/bin/bash
# setup_boot_service.sh — root only
# Adds user to dialout, disables serial-getty, writes mesh0, enables ip_forward,
# installs systemd unit, daemon-reload, enable.

echo "[BOOT] Running setup_boot_service.sh as root"

# User to dialout
usermod -a -G dialout $(whoami) || true

# Disable serial-getty
systemctl disable serial-getty@ttyTHS1.service 2>/dev/null || true

# Mesh interface config
mkdir -p /etc/network/interfaces.d
cat > /etc/network/interfaces.d/mesh0 << 'MESH'
auto mesh0
iface mesh0 inet static
    address 192.168.50.11
    netmask 255.255.255.0
    wireless-channel 1
    wireless-essid aeromesh_swarm
    wireless-mode mesh
MESH

# IPv4 forwarding
sysctl -w net.ipv4.ip_forward=1

# Systemd unit
cp deploy/systemd/aeromesh_swarm.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable aeromesh_swarm.service

echo "[BOOT] Setup complete. Debug: journalctl -u aeromesh_swarm.service -f"
echo "[BOOT] Stop/start: systemctl stop aeromesh_swarm.service / systemctl start aeromesh_swarm.service"
