#!/bin/bash
set -e

USER_HOME="${HOME}"
USER_NAME="$(whoami)"
REPO_URL="https://github.com/rohanod/busDisplay.git"
INSTALL_DIR="${USER_HOME}/busdisplay"
CONFIG_DIR="${USER_HOME}/.config/busdisplay"
CONFIG_FILE="${CONFIG_DIR}/config.json"

echo "Installing Bus Display for Raspberry Pi..."

# Install required packages
echo "Installing system packages..."
sudo apt update
sudo apt install -y git xserver-xorg xinit python3-venv python3-pip python3-dev \
    x11-xserver-utils libcairo2-dev libcairo2 libgirepository1.0-dev pkg-config \
    build-essential libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev \
    libsdl2-ttf-dev libfreetype6-dev libportmidi-dev libjpeg-dev \
    python3-setuptools python3-wheel curl libglib2.0-dev libpango1.0-dev \
    libgdk-pixbuf2.0-dev libffi-dev shared-mime-info

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

# Install web UI dependencies
echo "Installing web UI dependencies..."
source venv/bin/activate
pip install -q -r webui_requirements.txt

# Create log files with proper permissions
echo "Setting up log files..."
touch "${USER_HOME}/busdisplay/webui.log"
chmod 664 "${USER_HOME}/busdisplay/webui.log"
chown "${USER_NAME}:${USER_NAME}" "${USER_HOME}/busdisplay/webui.log"

# Create config directory and default config file
echo "Creating configuration directory..."
mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default configuration file..."
    cat > "$CONFIG_FILE" << 'EOF'
{
  "stops": [],
  "max_departures": 8,
  "fetch_interval": 60,
  "max_minutes": 120,
  "show_clock": true
}
EOF
    echo "Default config created at $CONFIG_FILE"
    echo "You MUST configure your stops before the display will work!"
fi

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

# Install and enable systemd services
echo "Installing systemd services..."
sed -e "s|__USER__|${USER_NAME}|g" -e "s|__HOME__|${USER_HOME}|g" busdisplay.service | sudo tee /etc/systemd/system/busdisplay.service > /dev/null
sed -e "s|__USER__|${USER_NAME}|g" -e "s|__HOME__|${USER_HOME}|g" webui.service | sudo tee /etc/systemd/system/webui.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable busdisplay.service
# Don't enable webui.service - busdisplay.py will control it

echo "Installation complete!"
echo ""
echo "IMPORTANT: You must configure your stops before starting the service!"
echo "Run the interactive configurator:"
echo "  cd ~/busdisplay"
echo "  source venv/bin/activate"
echo "  python configurator.py"
echo ""
echo "Or manually edit: $CONFIG_FILE"
echo ""
echo "After configuration, start the service with:"
echo "  sudo systemctl start busdisplay.service"
echo ""
echo "Check service status: sudo systemctl status busdisplay"
echo "View logs: journalctl -u busdisplay -f"