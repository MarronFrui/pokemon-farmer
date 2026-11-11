import cv2
import numpy as np
import threading
import time
import os
import sys
import traceback
import win32gui
import win32ui
import config
from skimage.metrics import structural_similarity as ssim
from ctypes import windll
from PIL import Image

#battle_detection.py

# === CONFIG ===
# Detect base folder (normal Python vs PyInstaller EXE)
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS  # PyInstaller unpack folder
else:
    BASE_DIR = os.path.dirname(__file__)

# Use BASE_DIR for all data paths
DATABASE_FOLDER = os.path.join(BASE_DIR, "data", "pokemon_database")
BATTLE_TEMPLATES_FOLDER = os.path.join(BASE_DIR, "data", "battle_templates")
IMG_DIR = os.path.join(BASE_DIR, "data", "bin")
SHINY_MATCH_THRESHOLD = 1
# Calibrated on real captures with the canonical pipeline: a live battle frame
# scores >= 0.665 against any battle template, the overworld <= 0.2.
BATTLE_MATCH_THRESHOLD = 0.40
SHAPE_MATCH_THRESHOLD = 0.95
ANIMATION_DELAY = 2.0
MAX_SCREENSHOTS_PER_SHAPE = 10
WINDOW_NAME = "mGBA - Pokemon"

# === CANONICAL GAME GEOMETRY ===
# The mGBA window chrome (OS title bar, menu bar, game viewport scale) changes
# across emulator versions, UI languages, window sizes and Windows themes,
# which breaks any comparison done on raw window captures. Everything is
# therefore compared in CANONICAL GAME COORDINATES: the game screen area the
# shape database was captured at (736x516 game pixels).
#
#   - Captures use the CLIENT AREA only (no OS title bar), so the geometry no
#     longer depends on the window decoration.
#   - The mGBA menu bar height is measured once per session and cached; the
#     game area is whatever sits below it (letterbox bars trimmed).
#   - The game area is resized to 736x516 before any comparison, so battle
#     templates, live frames and the shiny zone crops always line up with the
#     database content regardless of the current window geometry.
CANONICAL_GAME_SIZE = (736, 516)
LEGACY_CHROME = 24         # menu-only chrome height of the legacy captures
MENU_ROW_MEAN = 240        # rows brighter than this are mGBA menu bar
MENU_H_MAX = 60            # safety cap for the menu bar measurement
BLACK_BAR_MEAN = 12        # rows/columns darker than this are letterbox bars
ANIMATION_DELAY = 2.0
MAX_SCREENSHOTS_PER_SHAPE = 10
WINDOW_NAME = "mGBA - Pokemon"

# === STATE ===
_lock = threading.Lock()
shiny_detected = False
_stop_thread = False
_menu_height = None   # measured once per session (mGBA layout is constant)

# === CLASSES ===
class Template:
    def __init__(self, img, filename):
        self.img = img
        self.filename = filename
        self.game = to_canonical_game(img)

# === HELPERS ===
def _trim_black_bars(game):
    """Remove letterbox bars (pure black rows/columns) mGBA may add when it
    keeps the GBA aspect ratio inside a larger viewport."""
    h, w = game.shape[:2]
    top = 0
    while top < h // 3 and game[top].mean() < BLACK_BAR_MEAN:
        top += 1
    bottom = h
    while bottom > h * 2 // 3 and game[bottom - 1].mean() < BLACK_BAR_MEAN:
        bottom -= 1
    left = 0
    while left < w // 3 and game[:, left].mean() < BLACK_BAR_MEAN:
        left += 1
    right = w
    while right > w * 2 // 3 and game[:, right - 1].mean() < BLACK_BAR_MEAN:
        right -= 1
    if (bottom - top) < 50 or (right - left) < 50:
        return game  # trimming would eat real content (e.g. dark scene): keep as-is
    return game[top:bottom, left:right]

def measure_menu_height(client_img):
    """Height of the mGBA menu bar inside a client-area capture: rows from the
    top that are still bright menu bar. Called once per session."""
    gray = cv2.cvtColor(client_img, cv2.COLOR_BGR2GRAY)
    means = gray.mean(axis=1)
    y = 0
    while y < min(MENU_H_MAX, client_img.shape[0]) and means[y] > MENU_ROW_MEAN:
        y += 1
    if y >= MENU_H_MAX:
        y = LEGACY_CHROME  # measurement failed (bright game scene): sane default
    return y

def canonical_game(client_img):
    """Reduce a client-area capture to the canonical 736x516 game area."""
    global _menu_height
    if _menu_height is None:
        _menu_height = measure_menu_height(client_img)
        config.log_print(f"[INFO] mGBA menu bar height measured: {_menu_height}px")
    game = client_img[_menu_height:, :, :]
    game = _trim_black_bars(game)
    return cv2.resize(game, CANONICAL_GAME_SIZE, interpolation=cv2.INTER_AREA)

def to_canonical_game(img):
    """Convert any library image (canonical capture or legacy full-window
    capture) to the canonical 736x516 game area."""
    h, w = img.shape[:2]
    if (h, w) == CANONICAL_GAME_SIZE:
        return img
    if h == 540 and w == 736:
        # legacy client-area capture: menu-only chrome of LEGACY_CHROME rows,
        # and the old mGBA rendered the game letterboxed/pillarboxed inside it
        game = img[LEGACY_CHROME:, :, :]
        game = _trim_black_bars(game)
        return cv2.resize(game, CANONICAL_GAME_SIZE, interpolation=cv2.INTER_AREA)
    # unknown geometry: strip what bright chrome we can find, best effort
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    means = gray.mean(axis=1)
    y = 0
    limit = min(150, h)
    while y < limit and means[y] > MENU_ROW_MEAN:
        y += 1
    return cv2.resize(img[y:, :, :], CANONICAL_GAME_SIZE, interpolation=cv2.INTER_AREA)

def load_templates(folder):
    templates = []
    if not os.path.exists(folder):
        return templates
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        img = cv2.imread(path)
        if img is not None:
            templates.append(Template(img, f))
    return templates

def ensure_folder(*paths):
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)

def save_frame(path, frame, debug=None):
    cv2.imwrite(path, frame)
    if debug:
        config.log_print(f"[DEBUG] Saved frame -> {path}")

battle_templates = load_templates(BATTLE_TEMPLATES_FOLDER)

# === WIN32 SCREENSHOT ===
def screenshot(window_ref):
    """Capture the window CLIENT AREA only (menu + game, no OS title bar).
    PW_RENDERFULLCONTENT is required to grab mGBA's hardware-rendered game
    surface; without it the client area comes back blank."""
    if isinstance(window_ref, int):
        hwnd = window_ref
    else:
        hwnd = win32gui.FindWindow(None, window_ref)

    if not hwnd:
        return None

    cl, ct, cr, cb = win32gui.GetClientRect(hwnd)
    w, h = cr - cl, cb - ct
    if w <= 0 or h <= 0:
        return None

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)  # PW_CLIENTONLY | PW_RENDERFULLCONTENT

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                          bmpstr, 'raw', 'BGRX', 0, 1)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    if result != 1:
        return None
    return im

def save_battle_frame(frame, limit=50, folder=BATTLE_TEMPLATES_FOLDER):
    ensure_folder(folder)

    existing_files = sorted(os.listdir(folder))
    existing_indices = []
    for f in existing_files:
        if f.startswith("battle_") and f.endswith(".png"):
            try:
                idx = int(f.split("_")[1].split(".")[0])
                existing_indices.append(idx)
            except ValueError:
                continue

    new_index = 1
    while new_index in existing_indices:
        new_index += 1

    if new_index > limit:
        return

    filename = os.path.join(folder, f"battle_{new_index:03d}.png")
    cv2.imwrite(filename, canonical_game(frame))
    config.log_print(f"[DEBUG] Saved new battle template -> {filename}")

def capture_window(window_name: str):
    im = screenshot(window_name)
    if im is None:
        return None
    frame = np.array(im)[:, :, ::-1].copy()  # RGB → BGR
    return frame

# === THREAD CONTROL ===
def start_battle_detection(hwnd, interval, shiny_zone=None, shiny_event=None, not_shiny_event=None):
    global _stop_thread
    _stop_thread = False

    def worker():
        while not _stop_thread:
            try:
                if check_battle(hwnd, shiny_zone=shiny_zone, shiny_event=shiny_event, not_shiny_event=not_shiny_event):
                    break
            except Exception:
                # The detection thread must never die silently: a crash here
                # looks exactly like "battle ended" while the battle is still
                # on screen.
                config.log_print("[ERROR] Battle detection error:\n" + traceback.format_exc())
            time.sleep(interval)

    t = threading.Thread(
        target=worker,
        daemon=True,
        name=f"battle-detector-{config.thread_counter}"
    )
    t.start()
    config.thread_counter += 1
    config.log_print(f"Thread object created: {t}, alive={t.is_alive()}")
    return t

# === BATTLE CHECK ===
def check_battle(window_name, shiny_zone="starter", shiny_event=None, not_shiny_event=None):
    
    now = time.time()
    frame = capture_window(window_name)
    if frame is None:
        return False

    live_game = canonical_game(frame)
    for template in battle_templates:
        res = cv2.matchTemplate(live_game, template.game, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > BATTLE_MATCH_THRESHOLD:
            config.in_battle = True
            break
        if max_val < BATTLE_MATCH_THRESHOLD:
            config.in_battle = False
  
    
    if config.in_battle and not config.battle_start_time:
        config.battle_start_time = now
            
    if not config.in_battle:
        config.battle_start_time = None
        config.detection_complete = False
        
    if config.in_battle and config.battle_start_time and not config.detection_complete:
        
        idle_frame = wait_for_idle(window_name, debug=True)
        if idle_frame is not None:    
            with _lock:
                config.detection_complete = True
                save_battle_frame(idle_frame)
                try:
                    zone_handler(idle_frame, zone=shiny_zone, debug=True, shiny_event=shiny_event, not_shiny_event=not_shiny_event)
                except Exception as e:
                    # A bad mask/color image must never kill the detection thread:
                    # treat the pokemon as unknown -> flee and keep hunting.
                    config.log_print(f"[ERROR] Shape detection failed: {e}")
                    if not_shiny_event is not None:
                        not_shiny_event.set()
    config.log_print(f"[STATUS] in_battle={config.in_battle}")
    return 

# === ZONE_HANDLER ===
def zone_handler(frame, zone="starter", shiny_event=None, not_shiny_event=None, debug=False):
    # Zones in CANONICAL GAME coordinates: the original constants were tuned on
    # full-window captures whose chrome height was LEGACY_CHROME (24px), so the
    # game-relative values are the originals minus that chrome.
    zones = {
        "starter": (60, 205 - LEGACY_CHROME, 300, 165),
        "enemy":   (450, 90 - LEGACY_CHROME, 200, 150)
    }
    
    if zone not in zones:
        raise ValueError(f"[!] Unknown detection zone '{zone}'")

    x, y, w, h = zones[zone]
    game = canonical_game(frame)
    detection_frame = np.ascontiguousarray(game[y:y+h, x:x+w])
    # config.log_print(f"[DEBUG] Using rectangle for zone '{zone}': x={x}, y={y}, w={w}, h={h}")
    
    mask_frame = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2GRAY)
    shape_folder = detect_shape(mask_frame, detection_frame, debug=True, shiny_event=shiny_event, not_shiny_event=not_shiny_event)
    color_folder = os.path.join(shape_folder, "color")
    ensure_folder(color_folder)

    return

# === DETECT SHAPE ===
def detect_shape(mask_frame, detection_frame, shiny_event=None, not_shiny_event=None, debug=False):
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(mask_frame)
    _, alpha_mask = cv2.threshold(enhanced, 240, 255, cv2.THRESH_BINARY_INV)

    for shape_name in sorted(os.listdir(DATABASE_FOLDER)):
        shape_folder = os.path.join(DATABASE_FOLDER, shape_name)
        mask_folder = os.path.join(shape_folder, "mask")
        color_folder = os.path.join(shape_folder, "color")
        shiny_folder = os.path.join(shape_folder, "shiny")
        ensure_folder(shiny_folder)

        if not os.path.exists(mask_folder):
            continue

        for ref_file in sorted(os.listdir(mask_folder)):
            ref_path = os.path.join(mask_folder, ref_file)
            ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
            if ref_img is None:
                continue

            if alpha_mask.dtype != ref_img.dtype:
                alpha_mask = alpha_mask.astype(ref_img.dtype)

            try:
                res = cv2.matchTemplate(alpha_mask, ref_img, cv2.TM_CCOEFF_NORMED)
            except cv2.error as e:
                # Mask reference with unexpected size/content: skip it, keep hunting.
                config.log_print(f"[WARN] Skipping bad mask ref {ref_path}: {e}")
                continue
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if debug:
                config.log_print(f"[DEBUG] Comparing with {ref_path} -> match score {max_val:.3f}")

            if max_val >= SHAPE_MATCH_THRESHOLD:
                if is_shiny(detection_frame, color_folder, debug=True, shiny_event=shiny_event, not_shiny_event=not_shiny_event):
                    existing_shinies = sorted(os.listdir(shiny_folder))
                    if len(existing_shinies) < MAX_SCREENSHOTS_PER_SHAPE:
                        new_index = len(existing_shinies) + 1
                        save_frame(os.path.join(shiny_folder, f"{new_index}.png"), detection_frame, debug)
                else:
                    existing_colors = sorted(os.listdir(color_folder))
                    if len(existing_colors) < MAX_SCREENSHOTS_PER_SHAPE:
                        new_index = len(existing_colors) + 1
                        save_frame(os.path.join(color_folder, f"{new_index}.png"), detection_frame, debug)

                return shape_folder

    existing_indices = [
        int(f.split("_")[1])
        for f in os.listdir(DATABASE_FOLDER)
        if f.startswith("shape_") and f.split("_")[1].isdigit()
    ]
    new_index = max(existing_indices, default=-1) + 1
    shape_folder = os.path.join(DATABASE_FOLDER, f"shape_{new_index}")
    mask_folder = os.path.join(shape_folder, "mask")
    color_folder = os.path.join(shape_folder, "color")
    shiny_folder = os.path.join(shape_folder, "shiny")
    ensure_folder(mask_folder, color_folder, shiny_folder)

    save_frame(os.path.join(mask_folder, "ref.png"), alpha_mask, debug)
    save_frame(os.path.join(color_folder, "1.png"), detection_frame, debug)
    if debug:
        config.log_print(f"[DEBUG] Detected new unique shape -> {shape_folder}")
    not_shiny_event.set()

    return shape_folder

# === SHINY DETECTION ===
def is_shiny(detection_frame, color_folder, debug, shiny_event, not_shiny_event):
    shiny_found = False
    if not os.path.exists(color_folder) or len(os.listdir(color_folder)) == 0:
        if debug:
            config.log_print(f"[WARN] No reference images found in {color_folder}")
        return False

    ref_images = []
    for ref_file in os.listdir(color_folder):
        ref_path = os.path.join(color_folder, ref_file)
        ref_img = cv2.imread(ref_path)
        if ref_img is not None:
            ref_images.append((ref_file, ref_img))

    if len(ref_images) == 0:
        if debug:
            config.log_print(f"[WARN] No valid reference images loaded from {color_folder}")
        return False

    for ref_file, ref_img in ref_images:
        if ref_img.shape != detection_frame.shape:
            if debug:
                config.log_print(f"[WARN] Skipping {ref_file}: size {ref_img.shape[:2]} != detection zone {detection_frame.shape[:2]}")
            continue
        try:
            score = ssim(detection_frame, ref_img, channel_axis=-1)
        except Exception as e:
            config.log_print(f"[WARN] Skipping {ref_file}: SSIM failed ({e})")
            continue
        if debug:
            config.log_print(f"[DEBUG] Comparing with {ref_file} -> SSIM: {score:.3f}")
        if score < SHINY_MATCH_THRESHOLD:
            shiny_event.set()
            shiny_found = True
        else:
            not_shiny_event.set()

    return shiny_found

def wait_for_idle(hwnd, timeout=3.0, check_interval=0.3, threshold=0.999, debug=False):
    """
    Wait until two consecutive frames are visually stable (idle).
    Stability is checked on the battlefield region only (the rectangle above
    the battle menu): the menu / text box at the bottom keeps animating
    (blinking cursor, typing text) and would starve the stability check even
    though the battle scene itself is settled.
    Returns the last stable frame (BGR NumPy array), or None if timeout.
    """
    def stable_region(frame):
        # upper ~62% of the client frame: battlefield, above the menu strip
        return frame[: int(frame.shape[0] * 0.62), :]

    start = time.time()

    prev = screenshot(hwnd)
    if prev is None:
        return None
    prev_full = np.array(prev)[:, :, ::-1].copy()  # RGB → BGR
    prev_frame = stable_region(prev_full)

    consecutive_stable = 0

    while time.time() - start < timeout:
        time.sleep(check_interval)
        curr = screenshot(hwnd)
        if curr is None:
            continue
        curr_full = np.array(curr)[:, :, ::-1].copy()
        curr_frame = stable_region(curr_full)

        score = ssim(prev_frame, curr_frame, channel_axis=-1)
        score_rounded = round(score, 3)  # round to 3 decimals
        if debug:
            config.log_print(f"[DEBUG] Screen stability SSIM={score_rounded:.3f} (consecutive={consecutive_stable})")

        if score_rounded >= threshold:
            consecutive_stable += 1
            if consecutive_stable >= 2:  # require two consecutive stable frames
                return curr_full
        else:
            consecutive_stable = 0

        prev_frame = curr_frame

    if debug:
        config.log_print("[WARN] Timeout waiting for idle screen")
    return None

def reset_battle_state():
    with _lock:
        config.in_battle = False
    
def stop_detection():
    global _stop_thread
    _stop_thread = True
    time.sleep(0.1)
