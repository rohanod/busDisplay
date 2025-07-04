#!/bin/bash
set -e

USER_HOME="${HOME}"
USER_NAME="$(whoami)"
REPO_URL="https://github.com/rohanod/busDisplay.git"
INSTALL_DIR="${USER_HOME}/busdisplay"

echo "Installing Bus Display for Raspberry Pi..."

# Install required packages
echo "Installing system packages..."
sudo apt update
sudo apt install -y git xserver-xorg xinit python3-venv python3-pip

# Add user to required groups for X11 and console access
echo "Configuring X11 permissions..."
sudo usermod -a -G video,tty "$USER_NAME"
echo "allowed_users=anybody" | sudo tee /etc/X11/Xwrapper.config
echo "needs_root_rights=yes" | sudo tee -a /etc/X11/Xwrapper.config

# Clone or update repository
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing repository..."
    git -C "$INSTALL_DIR" pull --rebase
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Set up Python environment
echo "Setting up Python environment..."
cd "$INSTALL_DIR"
bash setup_env.sh

# Configure git safe directory
echo "Configuring git..."
sudo git config --global --add safe.directory "$INSTALL_DIR"

# Mask getty on tty0 to prevent conflicts
echo "Configuring TTY..."
sudo systemctl mask getty@tty0.service

# Create xinitrc
echo "Creating xinitrc..."
sed "s|__HOME__|${USER_HOME}|g" xinitrc.example > "${USER_HOME}/.xinitrc"
chmod +x "${USER_HOME}/.xinitrc"

# Install and enable systemd service
echo "Installing systemd service..."
sed -e "s|__USER__|${USER_NAME}|g" -e "s|__HOME__|${USER_HOME}|g" busdisplay.service | sudo tee /etc/systemd/system/busdisplay.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable busdisplay.service
sudo systemctl start busdisplay.service

echo "Installation complete!"
echo "The bus display should now be running on your HDMI output."
echo "Edit ~/.config/busdisplay/stops.json to configure your stops."
echo "Use 'sudo systemctl status busdisplay' to check service status."