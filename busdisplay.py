#!/usr/bin/env python3
import os, sys, logging, datetime, time, json, requests, pygame, io, cairosvg

# ────────── Logging ──────────
LOG_FILE = "busDisplay.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logging.captureWarnings(True)

def _excepthook(exc_type, exc_value, exc_tb):
    logging.critical("UNCAUGHT EXCEPTION", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook
log = logging.getLogger("busDisplay")

# ────────── Initial Defaults (pre-scaling) ──────────
DEFAULT_COLS               = 8
DEFAULT_ROWS               = 2
DEFAULT_CELL_W             = 140
DEFAULT_BAR_H              = 320
DEFAULT_BAR_MARGIN         = 30
DEFAULT_BAR_PADDING        = 25
DEFAULT_CARD_PADDING       = 15
DEFAULT_NUMBER_SIZE        = 64
DEFAULT_STOP_NAME_SIZE     = 48
DEFAULT_LINE_SIZE          = 36
DEFAULT_ICON_SIZE          = 40
DEFAULT_BORDER_RADIUS      = 16
DEFAULT_SHADOW_OFFSET      = 6

# ────────── Runtime Config ──────────
CFG_PATH = os.path.expanduser("~/.config/busdisplay/stops.json")
if not os.path.isfile(CFG_PATH):
    os.makedirs(os.path.dirname(CFG_PATH), exist_ok=True)
    with open(CFG_PATH, "w") as f:  # write minimal example
        json.dump(
            [
                {"ID": "8592791", "Lines": {"10": "8587061"}},
                {"ID": "8592855", "Lines": {"22": "8592843"}},
            ],
            f,
            indent=2,
        )
with open(CFG_PATH) as f:
    STOPS = json.load(f)

MAX_SHOW       = 10
POLL_INTERVAL  = 60
API_URL        = "https://search.ch/timetable/api/stationboard.fr.json"
API_LIMIT      = 100
FETCH_TIMEOUT  = 4
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

# ────────── Pygame init ──────────
if "DISPLAY" not in os.environ:
    os.environ["SDL_VIDEODRIVER"] = "fbcon"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

pygame.init()
pygame.display.init()
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.NOFRAME)
pygame.mouse.set_visible(False)

# ────────── Scaling ──────────
design_w = DEFAULT_COLS * DEFAULT_CELL_W
design_h = DEFAULT_ROWS * DEFAULT_BAR_H + (DEFAULT_ROWS - 1) * DEFAULT_BAR_MARGIN
scale    = min(info.current_w / design_w, info.current_h / design_h)

CELL_W        = int(DEFAULT_CELL_W * scale)
BAR_H         = int(DEFAULT_BAR_H * scale)
BAR_MARGIN    = int(DEFAULT_BAR_MARGIN * scale)
BAR_PADDING   = int(DEFAULT_BAR_PADDING * scale)
CARD_PADDING  = int(DEFAULT_CARD_PADDING * scale)
NUMBER_SIZE   = int(DEFAULT_NUMBER_SIZE * scale)
STOP_NAME_SIZE= int(DEFAULT_STOP_NAME_SIZE * scale)
LINE_SIZE     = int(DEFAULT_LINE_SIZE * scale)
ICON_SIZE     = int(DEFAULT_ICON_SIZE * scale)
BORDER_RADIUS = int(DEFAULT_BORDER_RADIUS * scale)
SHADOW_OFFSET = int(DEFAULT_SHADOW_OFFSET * scale)

font_num  = pygame.font.SysFont("DejaVuSans", NUMBER_SIZE, bold=True)
font_stop = pygame.font.SysFont("DejaVuSans", STOP_NAME_SIZE, bold=True)
font_line = pygame.font.SysFont("DejaVuSans", LINE_SIZE, bold=True)
icon_w = icon_h = ICON_SIZE

def _load_svg(path: str) -> pygame.Surface:
    with open(path, "r") as f:
        svg = f.read()
    png = cairosvg.svg2png(bytestring=svg.encode(),
                           output_width=icon_w, output_height=icon_h)
    return pygame.image.load(io.BytesIO(png)).convert_alpha()

clock_img = _load_svg(CLOCK_SVG_FILE)
tram_img  = _load_svg(TRAM_SVG_FILE)

rows       = len(STOPS)
results    = [None] * rows
next_poll  = [0]    * rows

# ────────── Networking ──────────
def fetch(stop):
    try:
        data = requests.get(
            API_URL,
            params={
                "stop": stop["ID"],
                "transportation_types": "bus,tram",
                "limit": API_LIMIT,
            },
            timeout=FETCH_TIMEOUT,
        ).json()
    except Exception:
        log.error("Fetch error", exc_info=True)
        return "?", []

    name = data.get("stop", {}).get("name", "?")
    now  = datetime.datetime.now()
    deps = []
    for c in data.get("connections", []):
        line = c.get("*L") or c.get("line")
        term = c.get("terminal", {}).get("id")
        if line not in stop["Lines"] or term != stop["Lines"][line]:
            continue
        try:
            ts = datetime.datetime.strptime(c["time"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        delta = round((ts - now).total_seconds() / 60)
        if delta < -1:
            continue
        deps.append((ts, line, max(delta, 0)))
    deps.sort(key=lambda x: x[0])
    return name, deps[:MAX_SHOW]

def draw_rounded_rect(surf, color, rect, radius):
    pygame.draw.rect(surf, color, rect, border_radius=radius)

def draw_shadow(surf, rect, offset, color):
    shadow_rect = (rect[0] + offset, rect[1] + offset, rect[2], rect[3])
    shadow_surf = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surf, color, (0, 0, rect[2], rect[3]), border_radius=BORDER_RADIUS)
    surf.blit(shadow_surf, (shadow_rect[0], shadow_rect[1]))

# ────────── Drawing ──────────
def draw_bar(y, name, deps):
    if not deps:
        return
    
    cols = min(len(deps), DEFAULT_COLS - 1)
    total_w = cols * CELL_W + BAR_PADDING * 2
    x0 = (info.current_w - total_w) // 2
    
    # Draw shadow
    card_rect = (x0, y, total_w, BAR_H)
    draw_shadow(screen, card_rect, SHADOW_OFFSET, CARD_SHADOW)
    
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
    clock_y = content_y + (content_h // 4) - (icon_h // 2)
    tram_y = content_y + (3 * content_h // 4) - (icon_h // 2)
    screen.blit(clock_img, (icon_x, clock_y))
    screen.blit(tram_img, (icon_x, tram_y))
    
    # Departure cards
    card_start_x = icon_x + ICON_SIZE + CARD_PADDING
    card_w = (total_w - card_start_x - BAR_PADDING) // cols
    
    for i, (_, ln, mn) in enumerate(deps[:cols]):
        card_x = card_start_x + i * card_w
        
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
        min_text = str(mn) if mn > 0 else "NOW"
        min_surf = font_num.render(min_text, True, text_color)
        min_x = card_x + (card_w - min_surf.get_width()) // 2
        min_y = content_y + (content_h // 4) - (min_surf.get_height() // 2)
        screen.blit(min_surf, (min_x, min_y))
        
        # Line number
        line_surf = font_line.render(ln, True, text_color)
        line_x = card_x + (card_w - line_surf.get_width()) // 2
        line_y = content_y + (3 * content_h // 4) - (line_surf.get_height() // 2)
        screen.blit(line_surf, (line_x, line_y))

# ────────── Main loop ──────────
def main():
    clk = pygame.time.Clock()
    while True:
        frame = (pygame.time.get_ticks()//250) % len(SPINNER)
        screen.fill(DARK_BG)

        if any(r is None for r in results):
            msg  = f"Loading {SPINNER[frame]}"
            surf = font_num.render(msg, True, ACCENT_COLOR)
            screen.blit(surf, ((info.current_w - surf.get_width())//2,
                               (info.current_h - surf.get_height())//2))
        else:
            y0 = (info.current_h - (rows*BAR_H + (rows-1)*BAR_MARGIN))//2
            for idx, _ in enumerate(STOPS):
                draw_bar(y0 + idx*(BAR_H+BAR_MARGIN), *results[idx])

        pygame.display.flip()

        # fetch one stop per frame
        for i, stop in enumerate(STOPS):
            if time.time() >= next_poll[i]:
                next_poll[i] = time.time() + POLL_INTERVAL
                results[i]   = fetch(stop)
                break

        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit(0)

        clk.tick(30)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.critical("Fatal error", exc_info=True)
        sys.exit(1)