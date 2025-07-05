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

### Easy Configuration with the Interactive Tool

For a much easier setup experience, you can use the interactive configuration tool. It helps you search for stops and configure all display options from a simple menu.

To launch the tool, run:
```bash
cd ~/busdisplay
source venv/bin/activate
python configurator.py
```

### Manual Configuration

If you prefer to edit the file by hand, create `~/.config/busdisplay/config.json` to configure your display:

```json
{
  "stops": [
    {"ID": "8592791", "LinesInclude": {"10": "8587061"}},
    {"ID": "8592855", "LinesExclude": {"22": "8592843", "53": null}},
    {"ID": "8587061"}
  ],
  "max_departures": 8,
  "api_request_interval": 90,
  "max_minutes": 120,
  "show_clock": true
}
```

### Stop Filtering Options
- `{"ID": "8592791", "LinesInclude": {"10": "8587061"}}` - Only line 10 to terminal 8587061
- `{"ID": "8592791", "LinesInclude": {"10": null}}` - Only line 10 to any destination
- `{"ID": "8592855", "LinesExclude": {"22": "8592843", "53": null}}` - Exclude line 22 to 8592843 and all line 53
- `{"ID": "8587061"}` - All departures (no filtering)
- `{"ID": "8592791", "Limit": 300}` - Fetch up to 300 departures (default: 100) for busy stops

### Configuration Options

| Option | Description | Default | Example |
|--------|-------------|---------|----------|
| `stops` | Array of stop configurations | `[]` | `[{"ID": "8592791"}]` |
| `max_departures` | Maximum departures per stop | `8` | `6` |
| `fetch_interval` | Seconds between data fetches | `60` | `30` |
| `http_timeout` | HTTP request timeout in seconds | `10` | `15` |
| `max_minutes` | Hide departures beyond X minutes | `120` | `90` |
| `show_clock` | Show current time in corner | `true` | `false` |
| `cols` | Maximum departure columns | `8` | `6` |
| `rows` | Maximum stop rows | `2` | `3` |
| `cell_w` | Base cell width | `140` | `120` |
| `bar_h` | Stop card height | `320` | `280` |
| `bar_margin` | Margin between stop cards | `30` | `20` |
| `bar_padding` | Padding inside stop cards | `25` | `20` |
| `card_padding` | Padding between elements | `15` | `10` |
| `minute_size` | Departure time font size | `48` | `42` |
| `now_size` | "NOW" text font size | `28` | `24` |
| `stop_name_size` | Stop name font size | `48` | `44` |
| `line_size` | Line number font size | `36` | `32` |
| `icon_size` | Clock/tram icon size | `40` | `36` |
| `icon_line_multiplier` | Icon line thickness multiplier | `1.0` | `0.5` |
| `border_radius` | Card corner radius | `16` | `12` |
| `shadow_offset` | Card shadow offset | `6` | `4` |
| `grid_shrink` | Shrink multiplier for 3+ stops | `0.8` | `0.7` |

### Layout Behavior
- **1-2 stops**: Vertical stack
- **3 stops**: Two on top, one centered below
- **4+ stops**: 2x2 grid

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
- Raspberry Pi OS Lite
- HDMI display
- Internet connection

## Notes

- The display automatically scales to your screen resolution
- Updates are pulled from GitHub on every service restart
- Logs are written to `~/busdisplay/busDisplay.log` and systemd journal
- AI assisted in generating parts of this project