import cv2
import numpy as np
import threading
import time
from window_capture import capture_window
import os

BATTLE_TEMPLATES_FOLDER = os.path.join("data", "battle_templates")
SHINY_TEMPLATES_FOLDER = os.path.join("data", "pokemon_shiny")

_lock = threading.Lock()
in_battle = False
shiny_detected = False
_last_battle_state = False
ANIMATION_DELAY = 3.0  # seconds

class Template:
    def __init__(self, img, filename):
        self.img = img
        self.filename = filename

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

battle_templates = load_templates(BATTLE_TEMPLATES_FOLDER)
shiny_templates = load_templates(SHINY_TEMPLATES_FOLDER)

def is_shiny(frame, zone="starter", debug=True):
    """Check if any shiny template matches the given frame, in the selected zone."""
    zones = {
        "starter": (60, frame.shape[0] - 320, 300, 175),
        "enemy":   (400, frame.shape[0] - 450, 300, 180)
    }

    if zone not in zones:
        raise ValueError(f"[!] Unknown detection zone '{zone}'")

    x, y, w, h = zones[zone]
    detection_frame = frame[y:y+h, x:x+w].copy()
    detection_frame = np.ascontiguousarray(detection_frame)

    for template in shiny_templates:
        t_resized = cv2.resize(template.img, (w, h))
        res = cv2.matchTemplate(detection_frame, t_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if debug:
            print(f"[DEBUG] Checking template {template.filename} in zone '{zone}' -> score: {max_val:.3f}")
        if max_val > 0.2:
            if debug:
                print(f"[DEBUG] Shiny detected with template {template.filename} in zone '{zone}'")
            return True
    return False

def _check_battle(hwnd, shiny_zone="starter"):
    global in_battle, shiny_detected, _last_battle_state

    frame = capture_window(hwnd)
    if frame is None:
        return

    battle = False
    for template in battle_templates:
        t_resized = cv2.resize(template.img, (frame.shape[1], frame.shape[0]))
        res = cv2.matchTemplate(frame, t_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > 0.3:
            battle = True
            break

    shiny = False
    # Only check for shiny when battle just started
    if battle and not _last_battle_state:
        if True:  # keep debug prints
            print("[DEBUG] Battle detected, waiting for animation before checking shiny...")
        time.sleep(ANIMATION_DELAY)  # wait for the battle animation to play
        shiny = is_shiny(frame, zone=shiny_zone, debug=True)  # use the passed zone

    with _lock:
        in_battle = battle
        if shiny:
            shiny_detected = True  # persist until battle ends
        if not battle:
            shiny_detected = False  # reset after battle ends
        _last_battle_state = battle

    print(f"[TICK] in_battle={in_battle}, shiny_detected={shiny_detected}")

    # Reset shiny when battle ends
    if not battle and _last_battle_state:
        with _lock:
            shiny_detected = False
        _last_battle_start_time = None
        _shiny_checked = False

    with _lock:
        in_battle = battle
        _last_battle_state = battle

    print(f"[TICK] in_battle={in_battle}, shiny_detected={shiny_detected}")

def start_battle_detection(hwnd, interval=2.0, shiny_zone="starter"):
    """Start a background thread that continuously checks for battles."""
    def worker():
        while True:
            _check_battle(hwnd, shiny_zone=shiny_zone)
            time.sleep(interval)
    threading.Thread(target=worker, daemon=True).start()

def get_battle_state():
    with _lock:
        return in_battle, shiny_detected
