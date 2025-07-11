#!/bin/bash
set -e

USER_HOME="${HOME}"
INSTALL_DIR="${USER_HOME}/busdisplay"

echo "Uninstalling Bus Display..."

# Stop and disable services
echo "Stopping services..."
sudo systemctl stop busdisplay.service || true
sudo systemctl stop webui.service || true
sudo systemctl disable busdisplay.service || true
sudo systemctl disable webui.service || true
sudo rm -f /etc/systemd/system/busdisplay.service
sudo rm -f /etc/systemd/system/webui.service
sudo systemctl daemon-reload

# Restore getty on tty0
echo "Restoring TTY..."
sudo systemctl unmask getty@tty0.service
sudo systemctl enable getty@tty0.service

# Remove files
echo "Removing files..."
rm -f "${USER_HOME}/.xinitrc"
rm -rf "$INSTALL_DIR"

# Clean up any remaining log files
echo "Cleaning up log files..."
rm -f "${USER_HOME}/busdisplay/busDisplay.log"
rm -f "${USER_HOME}/busdisplay/webui.log"

echo "Uninstallation complete!"
echo "Note: Configuration files in ~/.config/busdisplay have been preserved."
echo "Remove them manually if desired: rm -rf ~/.config/busdisplay"