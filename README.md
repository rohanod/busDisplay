# Bus Display for Raspberry Pi

A full-screen bus/tram departure display for Raspberry Pi with OTA updates, designed for HDMI output on RPi Zero 2 W.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/rohanod/busDisplay/main/install.sh | bash
```

## Features

- Full-screen Pygame display optimized for any HDMI resolution
- Auto-scaling fonts and UI elements
- Real-time departures from Search.ch API
- Highlights due departures (≤0 min) with orange background
- OTA updates via git pull on every service restart
- Systemd service for automatic startup
- Runs on tty0 without desktop environment

## Configuration

Edit `~/.config/busdisplay/stops.json` to configure your stops:

```json
[
  {"ID": "8592791", "Lines": {"10": "8587061"}},
  {"ID": "8592855", "Lines": {"22": "8592843"}}
]
```

- `ID`: Stop ID from Search.ch
- `Lines`: Map of line numbers to terminal IDs you want to display

## Service Management

```bash
# Check status
sudo systemctl status busdisplay

# Restart (triggers OTA update)
sudo systemctl restart busdisplay

# View logs
journalctl -u busdisplay -f

# Stop
sudo systemctl stop busdisplay
```

## Manual Testing

```bash
cd ~/busdisplay
source venv/bin/activate
python busdisplay.py
```

Press ESC to quit.

## Uninstall

```bash
bash ~/busdisplay/uninstall.sh
```

## Hardware Requirements

- Raspberry Pi Zero 2 W (or any RPi with HDMI)
- Raspberry Pi OS Bookworm (Wayland disabled)
- HDMI display
- Internet connection

## Notes

- The display automatically scales to your screen resolution
- Updates are pulled from GitHub on every service restart
- Logs are written to `~/busdisplay/busDisplay.log` and systemd journal
- AI assisted in generating parts of this project