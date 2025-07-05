import os, sys, logging, datetime, time, json, requests, pygame, io, cairosvg

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

# ────────── Runtime Config ──────────
CONFIG_PATH = os.path.expanduser("~/.config/busdisplay/config.json")

if not os.path.isfile(CONFIG_PATH):
    log.error(f"Config file not found: {CONFIG_PATH}")
    log.error("Please create config.json with your configuration")
    sys.exit(1)

with open(CONFIG_PATH) as f:
    config = json.load(f)

STOPS = config.get("stops", [])
if not STOPS:
    log.error("No stops configured in config.json")
    sys.exit(1)

# Apply all overrides from config
COLS = config.get("cols", DEFAULT_COLS)
ROWS = config.get("rows", DEFAULT_ROWS)
CELL_W_BASE = config.get("cell_w", DEFAULT_CELL_W)
BAR_H_BASE = config.get("bar_h", DEFAULT_BAR_H)
BAR_MARGIN_BASE = config.get("bar_margin", DEFAULT_BAR_MARGIN)
BAR_PADDING_BASE = config.get("bar_padding", DEFAULT_BAR_PADDING)
CARD_PADDING_BASE = config.get("card_padding", DEFAULT_CARD_PADDING)
MINUTE_SIZE_BASE = config.get("minute_size", DEFAULT_MINUTE_SIZE)
NOW_SIZE_BASE = config.get("now_size", DEFAULT_NOW_SIZE)
STOP_NAME_SIZE_BASE = config.get("stop_name_size", DEFAULT_STOP_NAME_SIZE)
LINE_SIZE_BASE = config.get("line_size", DEFAULT_LINE_SIZE)
ICON_SIZE_BASE = config.get("icon_size", DEFAULT_ICON_SIZE)
ICON_LINE_MULTIPLIER = config.get("icon_line_multiplier", DEFAULT_ICON_LINE_MULTIPLIER)
BORDER_RADIUS_BASE = config.get("border_radius", DEFAULT_BORDER_RADIUS)
SHADOW_OFFSET_BASE = config.get("shadow_offset", DEFAULT_SHADOW_OFFSET)
GRID_SHRINK = config.get("grid_shrink", DEFAULT_GRID_SHRINK)
SCALE_MULTIPLIER = DEFAULT_SCALE_MULTIPLIER

MAX_SHOW       = config.get("max_departures", 8)
FETCH_INTERVAL = config.get("fetch_interval", DEFAULT_FETCH_INTERVAL)
MAX_MINUTES    = config.get("max_minutes", 120)
SHOW_CLOCK     = config.get("show_clock", True)
FETCH_TIMEOUT  = config.get("http_timeout", DEFAULT_HTTP_TIMEOUT)
API_URL        = "https://search.ch/timetable/api/stationboard.fr.json"
API_LIMIT      = 100
SPINNER        = "|/-\\"

CLOCK_SVG_FILE = os.path.join(os.path.dirname(__file__), "clock.svg")
TRAM_SVG_FILE  = os.path.join(os.path.dirname(__file__), "tram.svg")

BLACK, WHITE   = (0, 0, 0), (255, 255, 255)
ORANGE, RED    = (255, 140, 0), (255, 69, 58)
BLUE, GREEN    = (0, 122, 255), (52, 199, 89)
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

rows       = len(STOPS)
results    = [None] * rows

# ────────── Networking ──────────
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
            },
            timeout=FETCH_TIMEOUT,
        )
        log.info(f"HTTP {response.status_code} for stop {stop['ID']} ({len(response.content)} bytes)")
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
            # Add delay if present
            delay_minutes = c.get("delay", 0)
            if delay_minutes:
                ts += datetime.timedelta(minutes=delay_minutes)
        except ValueError:
            continue
        delta = round((ts - now).total_seconds() / 60)
        if delta < 0 or delta > MAX_MINUTES:
            continue
        deps.append((ts, line, max(delta, 0)))
    deps.sort(key=lambda x: x[0])
    return name, deps[:MAX_SHOW]

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
    
    for i, (ts, ln, _) in enumerate(deps[:cols]):
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
        
        # Minutes
        if mn > 0:
            min_text = str(mn)
            min_surf = font_minute.render(min_text, True, text_color)
        else:
            min_text = "NOW"
            min_surf = font_now.render(min_text, True, text_color)
        min_x = card_x + (card_w - min_surf.get_width()) // 2
        min_y = content_y + (content_h // 4) - (min_surf.get_height() // 2)
        screen.blit(min_surf, (min_x, min_y))
        
        # Line number
        line_surf = font_line.render(ln, True, text_color)
        line_x = card_x + (card_w - line_surf.get_width()) // 2
        line_y = content_y + (3 * content_h // 4) - (line_surf.get_height() // 2)
        screen.blit(line_surf, (line_x, line_y))

def get_layout_positions(num_stops, info, BAR_H, BAR_MARGIN, FIXED_CARD_W):
    positions = []
    if num_stops <= 2:
        # Vertical stack
        total_h = num_stops * BAR_H + (num_stops - 1) * BAR_MARGIN
        start_y = (info.current_h - total_h) // 2
        for i in range(num_stops):
            x = (info.current_w - FIXED_CARD_W) // 2
            y = start_y + i * (BAR_H + BAR_MARGIN)
            positions.append((x, y))
    elif num_stops == 3:
        # Two on top, one centered below
        top_y = (info.current_h - (2 * BAR_H + BAR_MARGIN)) // 2
        # Top two
        positions.append(((info.current_w - 2 * FIXED_CARD_W - BAR_MARGIN) // 2, top_y))
        positions.append(((info.current_w - 2 * FIXED_CARD_W - BAR_MARGIN) // 2 + FIXED_CARD_W + BAR_MARGIN, top_y))
        # Bottom center
        positions.append(((info.current_w - FIXED_CARD_W) // 2, top_y + BAR_H + BAR_MARGIN))
    else:
        # 2x2 grid
        grid_w = 2 * FIXED_CARD_W + BAR_MARGIN
        grid_h = 2 * BAR_H + BAR_MARGIN
        start_x = (info.current_w - grid_w) // 2
        start_y = (info.current_h - grid_h) // 2
        for i in range(min(4, num_stops)):
            row, col = i // 2, i % 2
            x = start_x + col * (FIXED_CARD_W + BAR_MARGIN)
            y = start_y + row * (BAR_H + BAR_MARGIN)
            positions.append((x, y))
    return positions

# ────────── Main loop ──────────
def main():
    global screen, info, font_num, font_now, font_stop, font_line, font_clock, clock_img, tram_img
    
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
    scale    = min(info.current_w / design_w, info.current_h / design_h)
    
    # Apply grid shrink for 3+ stops
    grid_scale = GRID_SHRINK if rows > 2 else 1.0
    
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
    
    # Initialize fonts and images after scaling is calculated
    font_minute = pygame.font.SysFont("DejaVuSans", MINUTE_SIZE, bold=True)
    font_now  = pygame.font.SysFont("DejaVuSans", NOW_SIZE, bold=True)
    font_stop = pygame.font.SysFont("DejaVuSans", STOP_NAME_SIZE, bold=True)
    font_line = pygame.font.SysFont("DejaVuSans", LINE_SIZE, bold=True)
    font_clock = pygame.font.SysFont("DejaVuSans", int(STOP_NAME_SIZE * 0.8), bold=True)
    
    # Fixed card dimensions
    global FIXED_CARD_W, FIXED_CELL_W
    FIXED_CARD_W = int(800 * SCALE_MULTIPLIER * scale * grid_scale)
    FIXED_CELL_W = int(100 * SCALE_MULTIPLIER * scale * grid_scale)
    
    clock_img = _load_svg(CLOCK_SVG_FILE, ICON_SIZE, ICON_SIZE)
    tram_img  = _load_svg(TRAM_SVG_FILE, ICON_SIZE, ICON_SIZE)
    
    frame_count = 0
    last_fetch = 0
    
    while True:
        now = datetime.datetime.now()
        current_time = time.time()
        loading = any(r is None for r in results)
        
        # Draw frame
        if loading:
            frame = frame_count % len(SPINNER)
            frame_count += 1
        else:
            frame = int(current_time) % len(SPINNER)
            
        screen.fill(DARK_BG)
        if loading:
            msg  = f"Loading {SPINNER[frame]}"
            surf = font_minute.render(msg, True, ACCENT_COLOR)
            screen.blit(surf, ((info.current_w - surf.get_width())//2,
                               (info.current_h - surf.get_height())//2))
        else:
            # Show clock if enabled
            if SHOW_CLOCK:
                current_time_str = now.strftime("%H:%M:%S")
                clock_surf = font_clock.render(current_time_str, True, TEXT_SECONDARY)
                screen.blit(clock_surf, (20, 20))
            
            positions = get_layout_positions(rows, info, BAR_H, BAR_MARGIN, FIXED_CARD_W)
            for idx, (x, y) in enumerate(positions[:rows]):
                draw_bar_at_pos(x, y, *results[idx], screen, COLS, FIXED_CARD_W, BAR_PADDING, ICON_SIZE, CARD_PADDING, BAR_H, SHADOW_OFFSET, BORDER_RADIUS, STOP_NAME_SIZE, clock_img, tram_img, font_stop, font_minute, font_now, font_line)
        pygame.display.flip()
        
        # Fetch based on interval
        if current_time >= last_fetch + FETCH_INTERVAL:
            last_fetch = current_time
            log.info(f"Fetch interval reached, fetching all {len(STOPS)} stops")
            for i, stop in enumerate(STOPS):
                results[i] = fetch(stop)
        
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit(0)
        
        time.sleep(0.1 if loading else 0.5)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.critical("Fatal error", exc_info=True)
        sys.exit(1)