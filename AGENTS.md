You are writing a small “OTA-updating bus-display” project for Raspberry Pi OS
(Bookworm, Wayland disabled).  
The repo URL will be **rohanod/busDisplay**.  Everything lives at the repo root
except a user-editable JSON config in `~/.config/busdisplay/stops.json`.

# Files & their roles  (⚠️  do *not* output the file bodies here)

1. **busdisplay.py**  
   * Reads `~/.config/busdisplay/stops.json` (same schema the user has been
     using: list of dicts with `"ID"` and inner `"Lines"` mapping).  
   * Full-screen Pygame display on HDMI 0.  
   * Auto-scales fonts, icons and bar sizes to any resolution; shows a loading
     spinner until first API reply.  
   * Fetches departures (tram&bus) every minute from the Search.ch stationboard
     API (limit 100).  
   * Highlights “due” departures (Δ ≤ 0 min) with orange background, otherwise
     orange text on dark cell.  
   * ESC quits; unhandled exceptions log to `busDisplay.log`.  
   * Uses two external SVGs (`clock.svg`, `tram.svg`) loaded and rasterised
     with CairoSVG, *preserving their native colours*.  
   * All sizing defaults (cols, bar height, icon size, gaps, etc.) are defined
     at the top so they can be tuned easily.

2. **clock.svg / tram.svg** – small vector icons.

3. **requirements.txt** – `pygame`, `requests`, `cairosvg`.

4. **setup_env.sh** – make a venv in `${HOME}/busdisplay/venv`, pip-install
   from requirements.

5. **update.sh** – `git -C ${HOME}/busdisplay pull --rebase --quiet`,
   then `exit 0` (so failure doesn’t kill the service).

6. **busdisplay.service** – Systemd unit **template** (contains `__HOME__`
   placeholder).  
```

\[Unit]  Description=Bus Display + on-boot update
\[Service]
User=**USER**
WorkingDirectory=**HOME**/busdisplay
ExecStartPre=/usr/bin/env bash **HOME**/busdisplay/update.sh
ExecStart=/usr/bin/startx **HOME**/.xinitrc -- :0 vt0 -keeptty -quiet
Restart=on-failure
TTYPath=/dev/tty0
TTYReset=yes
\[Install] WantedBy=multi-user.target

```

7. **xinitrc.example** – disables DPMS / screen blanking then
```

exec **HOME**/busdisplay/venv/bin/python **HOME**/busdisplay/busdisplay.py

````

8. **install.sh**  
* Installs `git`, `xserver-xorg`, `xinit` if absent.  
* Clones/updates the repo into `${HOME}/busdisplay`.  
* Runs `setup_env.sh`.  
* Masks `getty@tty0.service`.  
* Copies `xinitrc.example` to `~/.xinitrc`.  
* Expands placeholders in `busdisplay.service`, writes to
  `/etc/systemd/system/`, reloads, enables & starts the service.  
* Adds safe-directory to global git config to silence “dubious ownership”.  

9. **uninstall.sh** – reverses everything:
* Stops & disables busdisplay.service.  
* Unmasks & re-enables `getty@tty0.service`.  
* Removes `/etc/systemd/system/busdisplay.service`, `~/.xinitrc`,
  `${HOME}/busdisplay` and venv.

10. **README.md** – quick-start:
 ```
 curl -fsSL https://raw.githubusercontent.com/rohanod/busDisplay/main/install.sh | bash
 ```
 plus how to edit `~/.config/busdisplay/stops.json`, how OTA works, and a
 note that AI helped generate parts of the project.

# Provide the actual busdisplay.py implementation

```python
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
DEFAULT_COLS               = 11
DEFAULT_ROWS               = 2
DEFAULT_CELL_W             = 200
DEFAULT_BAR_H              = 200
DEFAULT_BAR_MARGIN         = 12
DEFAULT_BAR_PADDING_TOP    = 8
DEFAULT_BAR_PADDING_BOTTOM = 18
DEFAULT_NUMBER_SIZE        = 48
DEFAULT_STOP_NAME_SIZE     = 40
DEFAULT_ICON_SIZE          = 60
DEFAULT_MINUTE_LINE_GAP    = 20  # extra gap between minutes & line rows

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

BLACK, ORANGE  = (0, 0, 0), (255, 102, 0)
BG_CELL, BG_HL = (22, 22, 22), ORANGE
FG_TXT, FG_HL  = ORANGE, BLACK

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
PAD_TOP       = int(DEFAULT_BAR_PADDING_TOP * scale)
PAD_BOT       = int(DEFAULT_BAR_PADDING_BOTTOM * scale)
NUMBER_SIZE   = int(DEFAULT_NUMBER_SIZE * scale)
STOP_NAME_SIZE= int(DEFAULT_STOP_NAME_SIZE * scale)
ICON_SIZE     = int(DEFAULT_ICON_SIZE * scale)
MINUTE_GAP    = int(DEFAULT_MINUTE_LINE_GAP * scale)

font     = pygame.font.SysFont("DejaVuSansMono", NUMBER_SIZE,  bold=True)
lab_font = pygame.font.SysFont("DejaVuSansMono", STOP_NAME_SIZE, bold=True)
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

# ────────── Drawing ──────────
def draw_bar(y, name, deps):
 cols     = max(1, len(deps)) + 1
 total_w  = CELL_W * cols
 x0       = (info.current_w - total_w) // 2

 pygame.draw.rect(screen, BG_CELL, (x0, y, total_w, BAR_H))

 # stop name
 label = lab_font.render(name, True, ORANGE)
 screen.blit(label, ((info.current_w - label.get_width()) // 2, y + PAD_TOP))

 # row anchors
 minutes_y = y + PAD_TOP + STOP_NAME_SIZE + PAD_TOP
 line_y    = minutes_y + NUMBER_SIZE + MINUTE_GAP

 # icons (vertically centered against their row)
 screen.blit(clock_img, (x0 + PAD_TOP, minutes_y + (NUMBER_SIZE - icon_h) // 2))
 screen.blit(tram_img,  (x0 + PAD_TOP, line_y    + (NUMBER_SIZE - icon_h) // 2))

 for i, (_, ln, mn) in enumerate(deps, 1):
     cx   = x0 + i * CELL_W
     col  = FG_HL if mn == 0 else FG_TXT
     if mn == 0:
         pygame.draw.rect(screen, BG_HL, (cx, y, CELL_W, BAR_H))

     # minutes
     m_txt = str(mn)
     w_m, _ = font.size(m_txt)
     screen.blit(font.render(m_txt, True, col),
                 (cx + (CELL_W - w_m)//2, minutes_y))

     # line id
     w_ln, _ = font.size(ln)
     screen.blit(font.render(ln, True, col),
                 (cx + (CELL_W - w_ln)//2, line_y))

# ────────── Main loop ──────────
def main():
 clk = pygame.time.Clock()
 while True:
     frame = (pygame.time.get_ticks()//250) % len(SPINNER)
     screen.fill(BLACK)

     if any(r is None for r in results):
         msg  = f"Loading {SPINNER[frame]}"
         surf = font.render(msg, True, ORANGE)
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


Do not test it yourself, just give me the install command for me to test on the actual pi zero machine. Use startx to do it and make it run on tty0 so you will have to kill processes. I want a systemd daemon that can be started at startup or run through an ssh session and show the bus timings on the rpi zero 2 w's hdmi output

Make it so install.sh sets up everything and starts the systemd service automatically and sets up everything to work on tty0 with rpi zero's hdmi output. do a bunch of research on everything needed to create this project and fully create the project.