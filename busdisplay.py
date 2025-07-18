import os, sys, logging, datetime, time, json, requests, pygame, io, cairosvg, threading, subprocess, socket

# ────────── Logging ──────────
LOG_FILE = os.path.expanduser("~/busdisplay/busDisplay.log")
handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
if os.isatty(sys.stdout.fileno()):
    handlers.append(logging.StreamHandler(sys.stdout))
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=handlers,
)
logging.captureWarnings(True)

def _excepthook(exc_type, exc_value, exc_tb):
    logging.critical("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook
log = logging.getLogger("busDisplay")

log.info("Starting Bus Display application")

# ────────── Initial Defaults (pre-scaling) ──────────
DEFAULT_SCALE_MULTIPLIER   = 1.0
DEFAULT_COLS               = 8
DEFAULT_ROWS               = 2
DEFAULT_CELL_W             = 140
DEFAULT_BAR_H              = 320
DEFAULT_BAR_MARGIN         = 30
DEFAULT_BAR_PADDING        = 25
DEFAULT_CARD_PADDING       = 15
DEFAULT_MINUTE_SIZE        = 48
DEFAULT_NOW_SIZE           = 30
DEFAULT_STOP_NAME_SIZE     = 48
DEFAULT_LINE_SIZE          = 40
DEFAULT_ICON_SIZE          = 60
DEFAULT_BORDER_RADIUS      = 16
DEFAULT_SHADOW_OFFSET      = 6
DEFAULT_GRID_SHRINK        = 0.7
DEFAULT_ICON_LINE_MULTIPLIER = 1.0
DEFAULT_HTTP_TIMEOUT       = 10
DEFAULT_FETCH_INTERVAL     = 60
DEFAULT_WIDGET_SIZE = 320
DEFAULT_WIDGET_TEXT_SIZE = 36
DEFAULT_WIDGET_ICON_SIZE = 48
DEFAULT_CLOCK_TEXT_SIZE = 36
DEFAULT_TEMP_TEXT_SIZE = 36
DEFAULT_WEATHER_TEXT_SIZE = 28

# Grid mode (3/4 stops) specific settings - configurable in config.json
DEFAULT_GRID_WIDGET_WIDTH = 280   # Thinner widgets for grid mode
DEFAULT_GRID_WIDGET_HEIGHT = 100  # Widget height for grid mode
DEFAULT_GRID_SCALE = 1.00         # Unified scale for all grid mode elements (cards, widgets, etc.)

# Display options - configurable at top of script
USE_MINMAX_TEMP_ICONS = True  # Set to True to use separate min/max temp icons instead of thermometer

# ────────── Runtime Config ──────────
CONFIG_PATH = os.path.expanduser("~/.config/busdisplay/config.json")

if not os.path.isfile(CONFIG_PATH):
    log.error(f"Config file not found: {CONFIG_PATH}")
    log.error("Starting setup mode - will display setup instructions")
    # Don't exit, continue to setup mode
    config = {}
    SETUP_MODE = True
else:
    SETUP_MODE = False

if not SETUP_MODE:
    with open(CONFIG_PATH) as f:
        config = json.load(f)

STOPS = config.get("stops", []) if not SETUP_MODE else []
if not STOPS and not SETUP_MODE:
    log.error("No stops configured in config.json")
    SETUP_MODE = True

# Apply all overrides from config (use defaults in setup mode)
COLS = config.get("cols", DEFAULT_COLS) if not SETUP_MODE else DEFAULT_COLS
ROWS = config.get("rows", DEFAULT_ROWS) if not SETUP_MODE else DEFAULT_ROWS
CELL_W_BASE = config.get("cell_w", DEFAULT_CELL_W) if not SETUP_MODE else DEFAULT_CELL_W
BAR_H_BASE = config.get("bar_h", DEFAULT_BAR_H) if not SETUP_MODE else DEFAULT_BAR_H
BAR_MARGIN_BASE = config.get("bar_margin", DEFAULT_BAR_MARGIN) if not SETUP_MODE else DEFAULT_BAR_MARGIN
BAR_PADDING_BASE = config.get("bar_padding", DEFAULT_BAR_PADDING) if not SETUP_MODE else DEFAULT_BAR_PADDING
CARD_PADDING_BASE = config.get("card_padding", DEFAULT_CARD_PADDING) if not SETUP_MODE else DEFAULT_CARD_PADDING
MINUTE_SIZE_BASE = config.get("minute_size", DEFAULT_MINUTE_SIZE) if not SETUP_MODE else DEFAULT_MINUTE_SIZE
NOW_SIZE_BASE = config.get("now_size", DEFAULT_NOW_SIZE) if not SETUP_MODE else DEFAULT_NOW_SIZE
STOP_NAME_SIZE_BASE = config.get("stop_name_size", DEFAULT_STOP_NAME_SIZE) if not SETUP_MODE else DEFAULT_STOP_NAME_SIZE
LINE_SIZE_BASE = config.get("line_size", DEFAULT_LINE_SIZE) if not SETUP_MODE else DEFAULT_LINE_SIZE
ICON_SIZE_BASE = config.get("icon_size", DEFAULT_ICON_SIZE) if not SETUP_MODE else DEFAULT_ICON_SIZE
ICON_LINE_MULTIPLIER = config.get("icon_line_multiplier", DEFAULT_ICON_LINE_MULTIPLIER) if not SETUP_MODE else DEFAULT_ICON_LINE_MULTIPLIER
BORDER_RADIUS_BASE = config.get("border_radius", DEFAULT_BORDER_RADIUS) if not SETUP_MODE else DEFAULT_BORDER_RADIUS
SHADOW_OFFSET_BASE = config.get("shadow_offset", DEFAULT_SHADOW_OFFSET) if not SETUP_MODE else DEFAULT_SHADOW_OFFSET
GRID_SHRINK = config.get("grid_shrink", DEFAULT_GRID_SHRINK) if not SETUP_MODE else DEFAULT_GRID_SHRINK
WIDGET_SIZE_BASE = config.get("widget_size", DEFAULT_WIDGET_SIZE) if not SETUP_MODE else DEFAULT_WIDGET_SIZE
WIDGET_TEXT_SIZE_BASE = DEFAULT_WIDGET_TEXT_SIZE  # Not configurable in config.json
WIDGET_ICON_SIZE_BASE = config.get("widget_icon_size", DEFAULT_WIDGET_ICON_SIZE) if not SETUP_MODE else DEFAULT_WIDGET_ICON_SIZE
CLOCK_TEXT_SIZE_BASE = DEFAULT_CLOCK_TEXT_SIZE    # Fine-tune at top of script
TEMP_TEXT_SIZE_BASE = DEFAULT_TEMP_TEXT_SIZE      # Fine-tune at top of script  
WEATHER_TEXT_SIZE_BASE = DEFAULT_WEATHER_TEXT_SIZE # Fine-tune at top of script

# Grid mode settings - use config.json values if available, otherwise defaults
GRID_WIDGET_WIDTH_BASE = config.get("grid_widget_width", DEFAULT_GRID_WIDGET_WIDTH) if not SETUP_MODE else DEFAULT_GRID_WIDGET_WIDTH
GRID_WIDGET_HEIGHT_BASE = config.get("grid_widget_height", DEFAULT_GRID_WIDGET_HEIGHT) if not SETUP_MODE else DEFAULT_GRID_WIDGET_HEIGHT
GRID_SCALE_FINAL = config.get("grid_scale", DEFAULT_GRID_SCALE) if not SETUP_MODE else DEFAULT_GRID_SCALE  # Unified scale for all grid mode elements

SCALE_MULTIPLIER = DEFAULT_SCALE_MULTIPLIER

MAX_SHOW       = config.get("max_departures", 8) if not SETUP_MODE else 8
FETCH_INTERVAL = config.get("fetch_interval", DEFAULT_FETCH_INTERVAL) if not SETUP_MODE else DEFAULT_FETCH_INTERVAL
MAX_MINUTES    = config.get("max_minutes", 120) if not SETUP_MODE else 120
SHOW_CLOCK     = config.get("show_clock", True) if not SETUP_MODE else True
SHOW_WEATHER   = config.get("show_weather", True) if not SETUP_MODE else True
FETCH_TIMEOUT  = config.get("http_timeout", DEFAULT_HTTP_TIMEOUT) if not SETUP_MODE else DEFAULT_HTTP_TIMEOUT

# Grid mode options (available in config.json)
GRID_SCALE_CONFIG = config.get("grid_scale", DEFAULT_GRID_SCALE)
GRID_WIDGET_WIDTH_CONFIG = config.get("grid_widget_width", DEFAULT_GRID_WIDGET_WIDTH)
GRID_WIDGET_HEIGHT_CONFIG = config.get("grid_widget_height", DEFAULT_GRID_WIDGET_HEIGHT)
API_URL        = "https://search.ch/timetable/api/stationboard.fr.json"
API_LIMIT      = 100
SPINNER        = "|/-\\"

CLOCK_SVG_FILE = os.path.join(os.path.dirname(__file__), "svgs", "clock.svg")
TRAM_SVG_FILE  = os.path.join(os.path.dirname(__file__), "svgs", "tram.svg")
SUN_SVG_FILE   = os.path.join(os.path.dirname(__file__), "svgs", "sun.svg")
RAIN_SVG_FILE  = os.path.join(os.path.dirname(__file__), "svgs", "rain.svg")
THERMOMETER_SVG_FILE = os.path.join(os.path.dirname(__file__), "svgs", "thermometer.svg")
MINTEMP_SVG_FILE = os.path.join(os.path.dirname(__file__), "svgs", "mintemp.svg")
MAXTEMP_SVG_FILE = os.path.join(os.path.dirname(__file__), "svgs", "maxtemp.svg")

BLACK, WHITE   = (0, 0, 0), (255, 255, 255)
ORANGE, RED    = (255, 140, 0), (255, 69, 58)
BLUE           = (0, 122, 255)
DARK_BG        = (18, 18, 20)
CARD_BG        = (44, 44, 46)
CARD_SHADOW    = (0, 0, 0, 60)
TEXT_PRIMARY   = (255, 255, 255)
TEXT_SECONDARY = (174, 174, 178)
ACCENT_COLOR   = ORANGE

# Pygame will be initialized in main() after X11 is ready

# Scaling will be done in main() after pygame is initialized

# Fonts and images will be initialized in main()

def _load_svg(path: str, w: int, h: int) -> pygame.Surface:
    with open(path, "r") as f:
        svg = f.read()
    png = cairosvg.svg2png(bytestring=svg.encode(),
                           output_width=w, output_height=h)
    return pygame.image.load(io.BytesIO(png)).convert_alpha()

rows       = len(STOPS) if not SETUP_MODE else 0
results    = [None] * rows if not SETUP_MODE else []
weather_data = None

def get_network_info():
    """Get WiFi network name and IP address for setup instructions"""
    try:
        # Get WiFi network name (SSID)
        wifi_name = "Unknown Network"
        try:
            result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                wifi_name = result.stdout.strip()
        except:
            pass
        
        # Get IP address
        ip_address = "Unknown IP"
        try:
            # Get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
            s.close()
        except:
            pass
        
        return wifi_name, ip_address
    except:
        return "Unknown Network", "Unknown IP"

def start_webui_background():
    """Start the web UI directly as a Python process"""
    try:
        # Check if webui is already running on port 5000
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 5000))
            sock.close()
            if result == 0:
                log.info("Web UI is already running on port 5000")
                return
        except:
            pass
        
        # Start web UI directly as a subprocess
        webui_path = os.path.join(os.path.dirname(__file__), "webui.py")
        venv_python = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
        
        # Use venv python if available, otherwise system python
        python_cmd = venv_python if os.path.exists(venv_python) else sys.executable
        
        if os.path.exists(webui_path):
            log.info("Starting web UI directly in background...")
            
            # Start web UI as background process
            process = subprocess.Popen([python_cmd, webui_path], 
                                     cwd=os.path.dirname(__file__),
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            log.info(f"Web UI started with PID {process.pid}")
            
            # Give it a moment to start
            time.sleep(3)
            
            # Verify it's running
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', 5000))
                sock.close()
                if result == 0:
                    log.info("Web UI confirmed running on port 5000")
                else:
                    log.warning("Web UI may not have started properly")
            except:
                log.warning("Could not verify web UI status")
        else:
            log.warning(f"Web UI not found at expected path: {webui_path}")
            
    except Exception as e:
        log.error(f"Failed to start web UI: {e}")

def draw_setup_screen(screen, info, font_stop, font_minute):
    """Draw the setup instructions screen"""
    screen.fill(DARK_BG)
    
    wifi_name, ip_address = get_network_info()
    port = "5000"
    
    # Create smaller fonts for setup screen - use default font to avoid fc-list timeout
    try:
        title_font = pygame.font.Font(None, int(font_stop.get_height() * 0.7))
        instruction_font = pygame.font.Font(None, int(font_minute.get_height() * 0.6))
        footer_font = pygame.font.Font(None, int(font_minute.get_height() * 0.5))
    except:
        # Fallback to existing fonts if font creation fails
        title_font = font_stop
        instruction_font = font_minute
        footer_font = font_minute
    
    # Title
    title_text = "Config not found. Please follow these steps to make config:"
    title_surf = title_font.render(title_text, True, ACCENT_COLOR)
    title_x = (info.current_w - title_surf.get_width()) // 2
    title_y = int(info.current_h * 0.15)
    screen.blit(title_surf, (title_x, title_y))
    
    # Instructions
    instructions = [
        f"1. Connect to the {wifi_name} network if you aren't already connected",
        f"2. Go to {ip_address}:{port} from a web browser (Laptop is easier but phone works too)",
        "3. Click the stops tab",
        "4. Click the \"Add Stop\" button and add a stop", 
        "5. Click the \"Restart Display\" button",
        "",
        "If you want, you can configure more things at the \"Display\" tab"
    ]
    
    y_offset = title_y + title_surf.get_height() + 40
    line_height = int(instruction_font.get_height() * 1.4)
    
    for instruction in instructions:
        if instruction.strip():  # Skip empty lines for spacing
            instr_surf = instruction_font.render(instruction, True, TEXT_PRIMARY)
            instr_x = (info.current_w - instr_surf.get_width()) // 2
            screen.blit(instr_surf, (instr_x, y_offset))
        y_offset += line_height
    
    # Footer note
    footer_text = "The web interface is starting in the background..."
    footer_surf = footer_font.render(footer_text, True, TEXT_SECONDARY)
    footer_x = (info.current_w - footer_surf.get_width()) // 2
    footer_y = int(info.current_h * 0.85)
    screen.blit(footer_surf, (footer_x, footer_y))

def fetch(stop):
    limit = stop.get("Limit", API_LIMIT)
    log.info(f"Fetching stop {stop['ID']} with limit {limit}")
    try:
        response = requests.get(
            API_URL,
            params={
                "stop": stop["ID"],
                "transportation_types": "bus,tram",
                "limit": limit,
                "show_delays": "1",
                "mode": "depart",
            },
            timeout=FETCH_TIMEOUT,
        )
        log.info(f"HTTP {response.status_code} for stop {stop['ID']} ({len(response.content)} bytes)")
        if response.status_code == 429:
            log.warning(f"Rate limited (HTTP 429). Consider increasing fetch_interval in config.")
            log.warning(f"Rate limit response: {response.text}")
            return "?", []
        elif response.status_code != 200:
            log.error(f"API returned status {response.status_code}: {response.text}")
            return "?", []
        if len(response.content) == 0:
            log.error("API returned empty response")
            return "?", []
        data = response.json()
    except Exception:
        log.error("Fetch error", exc_info=True)
        return "?", []

    name = data.get("stop", {}).get("name", "?")
    now  = datetime.datetime.now()
    deps = []
    for c in data.get("connections", []):
        line = c.get("*L") or c.get("line")
        term = c.get("terminal", {}).get("id")
        
        # Filter logic
        if "LinesInclude" in stop:
            include = stop["LinesInclude"]
            if line not in include:
                continue
            if isinstance(include[line], str) and term != include[line]:
                continue
        elif "LinesExclude" in stop:
            exclude = stop["LinesExclude"]
            if line in exclude:
                if isinstance(exclude[line], str) and term == exclude[line]:
                    continue
                elif exclude[line] is None:
                    continue
        # No filtering if neither LinesInclude nor LinesExclude
        try:
            ts = datetime.datetime.strptime(c["time"], "%Y-%m-%d %H:%M:%S")
            delay_minutes = 0
            
            # Add departure delay if present
            dep_delay = c.get("dep_delay", "+0")
            if dep_delay and dep_delay != "X":
                try:
                    # Handle delays like "+10", "+4", etc.
                    if dep_delay.startswith("+"):
                        delay_minutes = int(dep_delay[1:])
                    elif dep_delay.startswith("-"):
                        delay_minutes = -int(dep_delay[1:])
                    else:
                        delay_minutes = int(dep_delay)
                    ts += datetime.timedelta(minutes=delay_minutes)
                except ValueError:
                    pass  # Ignore invalid delay formats
        except (ValueError, TypeError):
            continue
        delta = round((ts - now).total_seconds() / 60)
        if delta < 0 or delta > MAX_MINUTES:
            continue
        
        # Store departure info (ts already includes delay)
        deps.append((ts, line, max(delta, 0), c["terminal"]["name"], delay_minutes))
    deps.sort(key=lambda x: x[0])
    
    # Hide municipality from stop name if configured per stop
    hide_municipality = stop.get("hide_municipality", False)
    if hide_municipality and ", " in name:
        name = name.split(", ", 1)[1]  # Remove "Municipality, " prefix
    
    return name, deps[:MAX_SHOW]

def fetch_weather():
    """Fetch weather data from Open-Meteo API"""
    try:
        LAT = 46.1925  # Geneva coordinates from weather.py
        LON = 6.17017
        URL = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "timezone": "Europe/Zurich"
        }
        
        response = requests.get(URL, params=params, timeout=FETCH_TIMEOUT)
        log.info(f"Weather HTTP {response.status_code} ({len(response.content)} bytes)")
        
        if response.status_code != 200:
            log.error(f"Weather API returned status {response.status_code}: {response.text}")
            return None
            
        data = response.json()
        today = data["daily"]
        min_temp = today["temperature_2m_min"][0]
        max_temp = today["temperature_2m_max"][0]
        rain_sum = today["precipitation_sum"][0]
        
        return {
            "min_temp": int(min_temp),
            "max_temp": int(max_temp),
            "will_rain": rain_sum > 0,
            "rain_sum": rain_sum
        }
    except Exception:
        log.error("Weather fetch error", exc_info=True)
        return None

def draw_rounded_rect(surf, color, rect, radius):
    pygame.draw.rect(surf, color, rect, border_radius=radius)

def draw_shadow(surf, rect, offset, color, border_radius):
    shadow_rect = (rect[0] + offset, rect[1] + offset, rect[2], rect[3])
    shadow_surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, color, (0, 0, rect[2], rect[3]), border_radius=border_radius)
    surf.blit(shadow_surf, (shadow_rect[0], shadow_rect[1]))

# ────────── Drawing ──────────
def draw_bar_at_pos(x, y, name, deps, screen, COLS, FIXED_CARD_W, BAR_PADDING, ICON_SIZE, CARD_PADDING, BAR_H, SHADOW_OFFSET, BORDER_RADIUS, STOP_NAME_SIZE, clock_img, tram_img, font_stop, font_minute, font_now, font_line):
    if not deps:
        return
    
    cols = min(len(deps), COLS - 1)
    total_w = FIXED_CARD_W
    
    # Calculate available width for departure cards
    available_w = total_w - (BAR_PADDING * 2) - ICON_SIZE - CARD_PADDING
    card_w = available_w // max(1, cols) if cols > 0 else 100
    x0 = x
    
    # Draw shadow
    card_rect = (x0, y, total_w, BAR_H)
    draw_shadow(screen, card_rect, SHADOW_OFFSET, CARD_SHADOW, BORDER_RADIUS)
    
    # Draw main card
    draw_rounded_rect(screen, CARD_BG, card_rect, BORDER_RADIUS)
    
    # Stop name header
    stop_surf = font_stop.render(name, True, TEXT_PRIMARY)
    stop_x = x0 + (total_w - stop_surf.get_width()) // 2
    screen.blit(stop_surf, (stop_x, y + BAR_PADDING))
    
    # Content area
    content_y = y + BAR_PADDING + STOP_NAME_SIZE + BAR_PADDING
    content_h = BAR_H - (BAR_PADDING * 3 + STOP_NAME_SIZE)
    
    # Icons
    icon_x = x0 + BAR_PADDING
    clock_y = content_y + (content_h // 4) - (ICON_SIZE // 2)
    tram_y = content_y + (3 * content_h // 4) - (ICON_SIZE // 2)
    screen.blit(clock_img, (icon_x, clock_y))
    screen.blit(tram_img, (icon_x, tram_y))
    
    # Departure cards
    card_start_x = icon_x + ICON_SIZE + CARD_PADDING
    
    for i, dep_info in enumerate(deps[:cols]):
        if len(dep_info) == 5:
            ts, ln, _, terminal_name, delay_minutes = dep_info
        elif len(dep_info) == 4:
            ts, ln, _, terminal_name = dep_info
            delay_minutes = 0
        else:
            ts, ln, _ = dep_info
            terminal_name = ""
            delay_minutes = 0
        card_x = card_start_x + i * card_w
        
        # Recalculate minutes at display time
        now = datetime.datetime.now()
        mn = max(0, round((ts - now).total_seconds() / 60))
        
        # Departure card background
        if mn == 0:
            card_color = RED
            text_color = WHITE
        elif mn <= 2:
            card_color = ORANGE
            text_color = WHITE
        else:
            card_color = (60, 60, 65)
            text_color = TEXT_PRIMARY
            
        dep_rect = (card_x + 2, content_y + 5, card_w - 4, content_h - 10)
        draw_rounded_rect(screen, card_color, dep_rect, 8)
        
        # Minutes (already includes delay since ts was adjusted in fetch())
        if mn > 0:
            min_text = str(mn)
            if delay_minutes > 0:
                min_text += " ⚠︎"
            min_surf = font_minute.render(min_text, True, text_color)
        else:
            min_text = "NOW"
            if delay_minutes > 0:
                min_text += " ⚠︎"
            min_surf = font_now.render(min_text, True, text_color)
        min_x = card_x + (card_w - min_surf.get_width()) // 2
        min_y = content_y + (content_h // 4) - (min_surf.get_height() // 2)
        screen.blit(min_surf, (min_x, min_y))
        
        # Line number
        line_surf = font_line.render(ln, True, text_color)
        line_x = card_x + (card_w - line_surf.get_width()) // 2
        line_y = content_y + (3 * content_h // 4) - (line_surf.get_height() // 2)
        screen.blit(line_surf, (line_x, line_y))
        

def draw_temperature_widget(x, y, weather_data, screen, WIDGET_SIZE, WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_temp, thermometer_img, mintemp_img, maxtemp_img):
    """Draw temperature widget"""
    if not weather_data:
        return
    
    # Draw shadow
    temp_rect = (x, y, WIDGET_SIZE, WIDGET_HEIGHT)
    draw_shadow(screen, temp_rect, SHADOW_OFFSET, CARD_SHADOW, BORDER_RADIUS)
    
    # Draw main card
    draw_rounded_rect(screen, CARD_BG, temp_rect, BORDER_RADIUS)
    
    if USE_MINMAX_TEMP_ICONS:
        # Use separate min/max temperature icons
        min_text = f"{weather_data['min_temp']}°"
        max_text = f"{weather_data['max_temp']}°"
        min_surf = font_temp.render(min_text, True, BLUE)  # Blue for min temp
        max_surf = font_temp.render(max_text, True, RED)   # Red for max temp
        
        # Calculate layout for min and max temps side by side
        min_content_width = mintemp_img.get_width() + CARD_PADDING//2 + min_surf.get_width()
        max_content_width = maxtemp_img.get_width() + CARD_PADDING//2 + max_surf.get_width()
        total_content_width = min_content_width + CARD_PADDING + max_content_width
        
        # Center the combined content
        content_start_x = x + (WIDGET_SIZE - total_content_width) // 2
        
        # Draw min temperature
        min_icon_x = content_start_x
        min_icon_y = y + (WIDGET_HEIGHT - mintemp_img.get_height()) // 2
        screen.blit(mintemp_img, (min_icon_x, min_icon_y))
        
        min_text_x = min_icon_x + mintemp_img.get_width() + CARD_PADDING//2
        min_text_y = y + (WIDGET_HEIGHT - min_surf.get_height()) // 2
        screen.blit(min_surf, (min_text_x, min_text_y))
        
        # Draw max temperature
        max_icon_x = min_text_x + min_surf.get_width() + CARD_PADDING
        max_icon_y = y + (WIDGET_HEIGHT - maxtemp_img.get_height()) // 2
        screen.blit(maxtemp_img, (max_icon_x, max_icon_y))
        
        max_text_x = max_icon_x + maxtemp_img.get_width() + CARD_PADDING//2
        max_text_y = y + (WIDGET_HEIGHT - max_surf.get_height()) // 2
        screen.blit(max_surf, (max_text_x, max_text_y))
        
    else:
        # Use single thermometer icon with range
        temp_text = f"{weather_data['min_temp']}°-{weather_data['max_temp']}°C"
        temp_surf = font_temp.render(temp_text, True, TEXT_PRIMARY)
        
        # Calculate total width of icon + padding + text
        total_content_width = thermometer_img.get_width() + CARD_PADDING + temp_surf.get_width()
        
        # Center the combined content
        content_start_x = x + (WIDGET_SIZE - total_content_width) // 2
        
        # Draw thermometer icon
        icon_x = content_start_x
        icon_y = y + (WIDGET_HEIGHT - thermometer_img.get_height()) // 2
        screen.blit(thermometer_img, (icon_x, icon_y))
        
        # Draw temperature text
        text_x = icon_x + thermometer_img.get_width() + CARD_PADDING
        text_y = y + (WIDGET_HEIGHT - temp_surf.get_height()) // 2
        screen.blit(temp_surf, (text_x, text_y))

def draw_weather_condition_widget(x, y, weather_data, screen, WIDGET_SIZE, WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_weather_text, sun_img, rain_img):
    """Draw weather condition widget"""
    if not weather_data:
        return
    
    # Draw shadow
    weather_rect = (x, y, WIDGET_SIZE, WIDGET_HEIGHT)
    draw_shadow(screen, weather_rect, SHADOW_OFFSET, CARD_SHADOW, BORDER_RADIUS)
    
    # Draw main card
    draw_rounded_rect(screen, CARD_BG, weather_rect, BORDER_RADIUS)
    
    # Weather icon and text - centered together
    weather_icon = rain_img if weather_data['will_rain'] else sun_img
    weather_text = "Rain" if weather_data['will_rain'] else "Sunny"
    weather_color = BLUE if weather_data['will_rain'] else ORANGE
    weather_surf = font_weather_text.render(weather_text, True, weather_color)
    
    # Calculate total width of icon + padding + text
    total_content_width = weather_icon.get_width() + CARD_PADDING + weather_surf.get_width()
    
    # Center the combined content
    content_start_x = x + (WIDGET_SIZE - total_content_width) // 2
    
    # Draw icon
    icon_x = content_start_x
    icon_y = y + (WIDGET_HEIGHT - weather_icon.get_height()) // 2
    screen.blit(weather_icon, (icon_x, icon_y))
    
    # Draw text
    text_x = icon_x + weather_icon.get_width() + CARD_PADDING
    text_y = y + (WIDGET_HEIGHT - weather_surf.get_height()) // 2
    screen.blit(weather_surf, (text_x, text_y))

def get_layout_positions(num_stops, info, BAR_H, BAR_MARGIN, FIXED_CARD_W):
    positions = []
    if num_stops == 1:
        # Single stop at top center (widgets will be at bottom)
        padding = int(info.current_h * 0.1)  # 10% padding from top
        x = (info.current_w - FIXED_CARD_W) // 2
        y = padding
        positions.append((x, y))
    elif num_stops == 2:
        # Two stops at top (widgets will be at bottom)
        total_h = num_stops * BAR_H + (num_stops - 1) * BAR_MARGIN
        start_y = int(info.current_h * 0.1)  # Start higher to leave room for widgets
        start_x = (info.current_w - FIXED_CARD_W) // 2
        for i in range(num_stops):
            x = start_x
            y = start_y + i * (BAR_H + BAR_MARGIN)
            positions.append((x, y))
    elif num_stops == 3:
        # 3 stops: stop cards at top center (2 on top, 1 centered below)
        # Use grid mode card scaling for 3 stops
        card_w = int(FIXED_CARD_W * GRID_SCALE_FINAL)
        card_h = int(BAR_H * GRID_SCALE_FINAL)
        margin = int(BAR_MARGIN * 0.7)     # Smaller margins
        
        # Center the grid at top
        grid_w = 2 * card_w + margin
        start_x = (info.current_w - grid_w) // 2
        start_y = int(info.current_h * 0.1)  # Top of screen
        
        # Two on top row
        positions.append((start_x, start_y))
        positions.append((start_x + card_w + margin, start_y))
        # One centered below the top two
        bottom_x = start_x + (card_w + margin) // 2
        positions.append((bottom_x, start_y + card_h + margin))
    else:
        # 4+ stops: stop cards at top center in 2x2 grid
        # Use grid mode card scaling for 4+ stops
        card_w = int(FIXED_CARD_W * GRID_SCALE_FINAL)
        card_h = int(BAR_H * GRID_SCALE_FINAL)
        margin = int(BAR_MARGIN * 0.6)     # Smaller margins
        
        # Center the 2x2 grid at top
        grid_w = 2 * card_w + margin
        grid_h = 2 * card_h + margin
        start_x = (info.current_w - grid_w) // 2
        start_y = int(info.current_h * 0.1)  # Top of screen
        
        # 2x2 grid
        for i in range(min(4, num_stops)):
            row, col = i // 2, i % 2
            x = start_x + col * (card_w + margin)
            y = start_y + row * (card_h + margin)
            positions.append((x, y))
    return positions

# ────────── Main loop ──────────

def main():
    global screen, info, font_now, font_stop, font_line, font_clock, font_digital, font_widget, font_clock_widget, font_temp, font_weather_text, clock_img, tram_img, sun_img, rain_img, thermometer_img, mintemp_img, maxtemp_img
    
    # ────────── Pygame init ──────────
    log.info(f"DISPLAY environment: {os.environ.get('DISPLAY', 'Not set')}")
    if "DISPLAY" not in os.environ:
        log.info("No DISPLAY found, using fbcon")
        os.environ["SDL_VIDEODRIVER"] = "fbcon"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    else:
        log.info("DISPLAY found, using X11")
    
    log.info("Initializing pygame")
    pygame.init()
    log.info("Initializing pygame display")
    pygame.display.init()
    log.info("Pygame initialized successfully")
    info = pygame.display.Info()
    screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.NOFRAME)
    pygame.mouse.set_visible(False)
    
    # ────────── Scaling ──────────
    design_w = COLS * CELL_W_BASE * SCALE_MULTIPLIER
    design_h = ROWS * BAR_H_BASE * SCALE_MULTIPLIER + (ROWS - 1) * BAR_MARGIN_BASE * SCALE_MULTIPLIER
    scale = min(info.current_w / design_w, info.current_h / design_h)
    
    # Apply grid shrink for 3+ stops, slight shrink for 2 stops
    if rows > 2:
        grid_scale = GRID_SHRINK * GRID_SCALE_FINAL  # Apply additional grid mode scaling
    elif rows == 2:
        grid_scale = 0.9  # Slightly smaller for 2 stops
    else:
        grid_scale = 1.0
    
    CELL_W        = int(CELL_W_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    BAR_H         = int(BAR_H_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    BAR_MARGIN    = int(BAR_MARGIN_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    BAR_PADDING   = int(BAR_PADDING_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    CARD_PADDING  = int(CARD_PADDING_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    MINUTE_SIZE   = int(MINUTE_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    NOW_SIZE      = int(NOW_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    STOP_NAME_SIZE= int(STOP_NAME_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    LINE_SIZE     = int(LINE_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    ICON_SIZE     = int(ICON_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    BORDER_RADIUS = int(BORDER_RADIUS_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    SHADOW_OFFSET = int(SHADOW_OFFSET_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    
    # Widget dimensions
    WIDGET_SIZE = int(WIDGET_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    WIDGET_HEIGHT = int(WIDGET_SIZE * 0.4)  # Normal widget height
    WIDGET_TEXT_SIZE = int(WIDGET_TEXT_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    WIDGET_ICON_SIZE = int(WIDGET_ICON_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    CLOCK_TEXT_SIZE = int(CLOCK_TEXT_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    TEMP_TEXT_SIZE = int(TEMP_TEXT_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    WEATHER_TEXT_SIZE = int(WEATHER_TEXT_SIZE_BASE * SCALE_MULTIPLIER * scale * grid_scale)
    
    # Grid mode widget dimensions (for 3/4 stops) - apply additional scaling
    if rows >= 3:
        grid_widget_scale = grid_scale * GRID_SCALE_FINAL
    else:
        grid_widget_scale = grid_scale
    GRID_WIDGET_WIDTH = int(GRID_WIDGET_WIDTH_BASE * SCALE_MULTIPLIER * scale * grid_widget_scale)
    GRID_WIDGET_HEIGHT = int(GRID_WIDGET_HEIGHT_BASE * SCALE_MULTIPLIER * scale * grid_widget_scale)

    
    # Initialize fonts and images after scaling is calculated
    # Use pygame.font.Font(None, size) to avoid fc-list timeout issues
    font_minute = pygame.font.Font(None, MINUTE_SIZE)
    font_now  = pygame.font.Font(None, NOW_SIZE)
    font_stop = pygame.font.Font(None, STOP_NAME_SIZE)
    font_line = pygame.font.Font(None, LINE_SIZE)
    font_clock = pygame.font.Font(None, int(STOP_NAME_SIZE * 0.8))
    font_digital = pygame.font.Font(None, int(STOP_NAME_SIZE * 0.6))  # Digital clock font
    font_widget = pygame.font.Font(None, WIDGET_TEXT_SIZE)
    font_clock_widget = pygame.font.Font(None, CLOCK_TEXT_SIZE)
    font_temp = pygame.font.Font(None, TEMP_TEXT_SIZE)
    font_weather_text = pygame.font.Font(None, WEATHER_TEXT_SIZE)
    
    # Fixed card dimensions
    global FIXED_CARD_W
    FIXED_CARD_W = int(800 * SCALE_MULTIPLIER * scale * grid_scale)
    
    clock_img = _load_svg(CLOCK_SVG_FILE, ICON_SIZE, ICON_SIZE)
    tram_img  = _load_svg(TRAM_SVG_FILE, ICON_SIZE, ICON_SIZE)
    sun_img   = _load_svg(SUN_SVG_FILE, WIDGET_ICON_SIZE, WIDGET_ICON_SIZE)
    rain_img  = _load_svg(RAIN_SVG_FILE, WIDGET_ICON_SIZE, WIDGET_ICON_SIZE)
    thermometer_img = _load_svg(THERMOMETER_SVG_FILE, WIDGET_ICON_SIZE, WIDGET_ICON_SIZE)
    mintemp_img = _load_svg(MINTEMP_SVG_FILE, WIDGET_ICON_SIZE, WIDGET_ICON_SIZE)
    maxtemp_img = _load_svg(MAXTEMP_SVG_FILE, WIDGET_ICON_SIZE, WIDGET_ICON_SIZE)
    
    frame_count = 0
    last_fetch = 0
    loading_start_time = time.time()  # Start loading immediately
    webui_started = False
    
    while True:
        # Get fresh time each iteration for precise timing
        loop_start = time.time()
        now = datetime.datetime.now()
        current_time = loop_start
        # Force loading state for at least 3 seconds to show spinner
        data_loading = any(r is None for r in results)
        loading = data_loading or (current_time - loading_start_time < 3)
        if not data_loading and current_time - loading_start_time >= 3:
            loading_start_time = 0
        
        # Draw frame
        if loading:
            frame = frame_count % len(SPINNER)
            frame_count += 1
        else:
            frame = int(current_time) % len(SPINNER)
            
        screen.fill(DARK_BG)
        
        # Handle setup mode
        if SETUP_MODE:
            if not webui_started:
                start_webui_background()
                webui_started = True
            draw_setup_screen(screen, info, font_stop, font_minute)
        elif loading:
            msg  = f"Loading {SPINNER[frame]}"
            surf = font_minute.render(msg, True, ACCENT_COLOR)
            screen.blit(surf, ((info.current_w - surf.get_width())//2,
                               (info.current_h - surf.get_height())//2))
        else:
            # Show clock based on stop count
            if rows == 1:
                # Single stop: widgets at bottom next to each other
                widgets_y = int(info.current_h * 0.8)
                
                # Calculate total width needed for all widgets
                widget_count = 0
                if SHOW_CLOCK:
                    widget_count += 1
                if SHOW_WEATHER and weather_data:
                    widget_count += 2  # Temperature + weather condition
                
                total_widget_width = widget_count * WIDGET_SIZE + (widget_count - 1) * BAR_MARGIN
                start_x = (info.current_w - total_widget_width) // 2
                current_x = start_x
                
                if SHOW_CLOCK:
                    # Draw clock widget
                    clock_rect = (current_x, widgets_y, WIDGET_SIZE, WIDGET_HEIGHT)
                    draw_shadow(screen, clock_rect, SHADOW_OFFSET, CARD_SHADOW, BORDER_RADIUS)
                    draw_rounded_rect(screen, CARD_BG, clock_rect, BORDER_RADIUS)
                    
                    # Clock content
                    icon_x = current_x + BAR_PADDING
                    icon_y = widgets_y + (WIDGET_HEIGHT - ICON_SIZE) // 2
                    screen.blit(clock_img, (icon_x, icon_y))
                    
                    current_time_str = now.strftime("%H:%M:%S")
                    time_surf = font_digital.render(current_time_str, True, ACCENT_COLOR)
                    time_x = icon_x + ICON_SIZE + CARD_PADDING
                    time_y = widgets_y + (WIDGET_HEIGHT - time_surf.get_height()) // 2
                    screen.blit(time_surf, (time_x, time_y))
                    
                    current_x += WIDGET_SIZE + BAR_MARGIN
                
                # Weather widgets next to clock
                if SHOW_WEATHER and weather_data:
                    # Temperature widget
                    draw_temperature_widget(current_x, widgets_y, weather_data, screen, WIDGET_SIZE, WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_temp, thermometer_img, mintemp_img, maxtemp_img)
                    current_x += WIDGET_SIZE + BAR_MARGIN
                    
                    # Weather condition widget
                    draw_weather_condition_widget(current_x, widgets_y, weather_data, screen, WIDGET_SIZE, WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_weather_text, sun_img, rain_img)
                    
            elif rows == 2:
                # Two stops: widgets at bottom next to each other
                widgets_y = int(info.current_h * 0.8)
                
                # Calculate total width needed for all widgets
                widget_count = 0
                if SHOW_CLOCK:
                    widget_count += 1
                if SHOW_WEATHER and weather_data:
                    widget_count += 2  # Temperature + weather condition
                
                total_widget_width = widget_count * WIDGET_SIZE + (widget_count - 1) * BAR_MARGIN
                start_x = (info.current_w - total_widget_width) // 2
                current_x = start_x
                
                if SHOW_CLOCK:
                    # Draw clock widget
                    clock_rect = (current_x, widgets_y, WIDGET_SIZE, WIDGET_HEIGHT)
                    draw_shadow(screen, clock_rect, SHADOW_OFFSET, CARD_SHADOW, BORDER_RADIUS)
                    draw_rounded_rect(screen, CARD_BG, clock_rect, BORDER_RADIUS)
                    
                    # Clock content
                    icon_x = current_x + BAR_PADDING
                    icon_y = widgets_y + (WIDGET_HEIGHT - ICON_SIZE) // 2
                    screen.blit(clock_img, (icon_x, icon_y))
                    
                    current_time_str = now.strftime("%H:%M:%S")
                    time_surf = font_digital.render(current_time_str, True, ACCENT_COLOR)
                    time_x = icon_x + ICON_SIZE + CARD_PADDING
                    time_y = widgets_y + (WIDGET_HEIGHT - time_surf.get_height()) // 2
                    screen.blit(time_surf, (time_x, time_y))
                    
                    current_x += WIDGET_SIZE + BAR_MARGIN
                
                # Weather widgets next to clock
                if SHOW_WEATHER and weather_data:
                    # Temperature widget
                    draw_temperature_widget(current_x, widgets_y, weather_data, screen, WIDGET_SIZE, WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_temp, thermometer_img, mintemp_img, maxtemp_img)
                    current_x += WIDGET_SIZE + BAR_MARGIN
                    
                    # Weather condition widget
                    draw_weather_condition_widget(current_x, widgets_y, weather_data, screen, WIDGET_SIZE, WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_weather_text, sun_img, rain_img)
            else:
                # 3+ stops: stop cards at top center, widgets side by side at bottom (grid mode)
                widgets_y = int(info.current_h * 0.8)  # Bottom of screen
                
                # Calculate total width needed for all widgets
                widget_count = 0
                if SHOW_CLOCK:
                    widget_count += 1
                if SHOW_WEATHER and weather_data:
                    widget_count += 2  # Temperature + weather condition
                
                total_widget_width = widget_count * GRID_WIDGET_WIDTH + (widget_count - 1) * BAR_MARGIN
                start_x = (info.current_w - total_widget_width) // 2
                current_x = start_x
                
                if SHOW_CLOCK:
                    # Draw clock widget (using grid dimensions)
                    clock_rect = (current_x, widgets_y, GRID_WIDGET_WIDTH, GRID_WIDGET_HEIGHT)
                    draw_shadow(screen, clock_rect, SHADOW_OFFSET, CARD_SHADOW, BORDER_RADIUS)
                    draw_rounded_rect(screen, CARD_BG, clock_rect, BORDER_RADIUS)
                    
                    # Clock content - centered
                    current_time_str = now.strftime("%H:%M:%S")
                    time_surf = font_clock_widget.render(current_time_str, True, ACCENT_COLOR)
                    
                    # Center clock icon and text together
                    total_content_width = ICON_SIZE + CARD_PADDING + time_surf.get_width()
                    content_start_x = current_x + (GRID_WIDGET_WIDTH - total_content_width) // 2
                    
                    # Draw icon and text centered
                    icon_x = content_start_x
                    icon_y = widgets_y + (GRID_WIDGET_HEIGHT - ICON_SIZE) // 2
                    screen.blit(clock_img, (icon_x, icon_y))
                    
                    time_x = icon_x + ICON_SIZE + CARD_PADDING
                    time_y = widgets_y + (GRID_WIDGET_HEIGHT - time_surf.get_height()) // 2
                    screen.blit(time_surf, (time_x, time_y))
                    
                    current_x += GRID_WIDGET_WIDTH + BAR_MARGIN
                
                # Weather widgets side by side with clock at bottom (using grid dimensions)
                if SHOW_WEATHER and weather_data:
                    # Temperature widget
                    draw_temperature_widget(current_x, widgets_y, weather_data, screen, GRID_WIDGET_WIDTH, GRID_WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_temp, thermometer_img, mintemp_img, maxtemp_img)
                    current_x += GRID_WIDGET_WIDTH + BAR_MARGIN
                    
                    # Weather condition widget
                    draw_weather_condition_widget(current_x, widgets_y, weather_data, screen, GRID_WIDGET_WIDTH, GRID_WIDGET_HEIGHT, SHADOW_OFFSET, BORDER_RADIUS, BAR_PADDING, CARD_PADDING, font_weather_text, sun_img, rain_img)
            
            positions = get_layout_positions(rows, info, BAR_H, BAR_MARGIN, FIXED_CARD_W)
            for idx, (x, y) in enumerate(positions[:rows]):
                # Use grid mode card scaling for 3+ stops
                if rows >= 3:
                    card_w = int(FIXED_CARD_W * GRID_SCALE_FINAL)
                    card_h = int(BAR_H * GRID_SCALE_FINAL)
                else:
                    card_w = FIXED_CARD_W
                    card_h = BAR_H
                    
                draw_bar_at_pos(x, y, *results[idx], screen, COLS, card_w, BAR_PADDING, ICON_SIZE, CARD_PADDING, card_h, SHADOW_OFFSET, BORDER_RADIUS, STOP_NAME_SIZE, clock_img, tram_img, font_stop, font_minute, font_now, font_line)
        pygame.display.flip()
        
        # Fetch based on interval (skip in setup mode)
        if not SETUP_MODE and current_time >= last_fetch + FETCH_INTERVAL:
            last_fetch = current_time
            log.info(f"Fetch interval reached, fetching all {len(STOPS)} stops")
            for i, stop in enumerate(STOPS):
                results[i] = fetch(stop)
            # Fetch weather data
            if SHOW_WEATHER:
                weather_data = fetch_weather()
        
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit(0)
        
        # Precise timing for smooth clock updates
        if loading:
            time.sleep(0.1)
        else:
            # Sleep until next second boundary for smooth clock
            now_time = time.time()
            sleep_time = max(0.01, 1.0 - (now_time % 1.0))  # Minimum 10ms sleep
            time.sleep(sleep_time)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.critical("Fatal error", exc_info=True)
        sys.exit(1)