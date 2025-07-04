#!/bin/bash
set -e

USER_HOME="${HOME}"
INSTALL_DIR="${USER_HOME}/busdisplay"

echo "Uninstalling Bus Display..."

# Stop and disable service
echo "Stopping service..."
sudo systemctl stop busdisplay.service || true
sudo systemctl disable busdisplay.service || true
sudo rm -f /etc/systemd/system/busdisplay.service
sudo systemctl daemon-reload

# Restore getty on tty0
echo "Restoring TTY..."
sudo systemctl unmask getty@tty0.service
sudo systemctl enable getty@tty0.service

# Remove files
echo "Removing files..."
rm -f "${USER_HOME}/.xinitrc"
rm -rf "$INSTALL_DIR"

echo "Uninstallation complete!"