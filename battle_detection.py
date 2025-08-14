import cv2
import numpy as np
import threading
import time
import os
from window_capture import capture_window

# === CONFIG ===
BATTLE_TEMPLATES_FOLDER = os.path.join("data", "battle_templates")
SHINY_TEMPLATES_FOLDER = os.path.join("data", "pokemon_shiny")
ANIMATION_DELAY = 8.0  # seconds
SHINY_MATCH_THRESHOLD = 0.5
BATTLE_MATCH_THRESHOLD = 0.3

# === STATE ===
_lock = threading.Lock()
in_battle = False
shiny_detected = False
_last_battle_state = False
_battle_start_time = None
_detection_complete = False  

# === CLASSES ===
class Template:
    def __init__(self, img, filename):
        self.img = img
        self.filename = filename

# === HELPERS ===
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

# === LOAD DATA ===
battle_templates = load_templates(BATTLE_TEMPLATES_FOLDER)
shiny_templates = load_templates(SHINY_TEMPLATES_FOLDER)

# === DETECTION ===
def is_shiny(frame, zone="starter", debug=True):
    """
    Check if any shiny template matches the given frame in the selected zone.
    Zones are defined as (x, y, w, h).
    """
    zones = {
        "starter": (60, frame.shape[0] - 320, 300, 173),
        "enemy":   (400, frame.shape[0] - 450, 300, 180)
    }

    if zone not in zones:
        raise ValueError(f"[!] Unknown detection zone '{zone}'")

    x, y, w, h = zones[zone]
    detection_frame = frame[y:y+h, x:x+w].copy()
    detection_frame = np.ascontiguousarray(detection_frame)

    for template in shiny_templates:
        t_h, t_w = template.img.shape[:2]
        scale = min(w / t_w, h / t_h)  # keep aspect ratio
        new_w, new_h = int(t_w * scale), int(t_h * scale)
        t_resized = cv2.resize(template.img, (new_w, new_h))

        res = cv2.matchTemplate(detection_frame, t_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)

        if debug:
            print(f"[DEBUG] Checking template {template.filename} in zone '{zone}' -> score: {max_val:.3f}")

        if max_val > SHINY_MATCH_THRESHOLD:
            if debug:
                print(f"[DEBUG] Shiny detected with template {template.filename} in zone '{zone}'")
            return True

        # # Special live preview for poussifeu
        # if debug and template.filename.lower() == "poussifeu.png":
        #     preview_live = detection_frame.copy()
        #     preview_template = template.img.copy()

        #     if preview_live.shape[0] != preview_template.shape[0]:
        #         scale_factor = preview_live.shape[0] / preview_template.shape[0]
        #         preview_template = cv2.resize(
        #             preview_template,
        #             (int(preview_template.shape[1] * scale_factor), preview_live.shape[0])
        #         )

        #     stacked = np.hstack((preview_live, preview_template))
        #     cv2.imshow("DEBUG: Live Zone (left) vs Template (right)", stacked)
        #     cv2.waitKey(1)

    return False

def _check_battle(hwnd, shiny_zone="starter"):
    global in_battle, shiny_detected, _last_battle_state, _battle_start_time, _detection_complete

    frame = capture_window(hwnd)
    if frame is None:
        return

    # === Check battle state ===
    battle = False
    for template in battle_templates:
        t_resized = cv2.resize(template.img, (frame.shape[1], frame.shape[0]))
        res = cv2.matchTemplate(frame, t_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > BATTLE_MATCH_THRESHOLD:
            battle = True
            break

    # === Battle just started ===
    if battle and not _last_battle_state:
        print("[DEBUG] Battle detected, starting animation delay timer...")
        _battle_start_time = time.time()
        shiny_detected = False
        _detection_complete = False

    # === Shiny check after delay ===
    if battle and _battle_start_time and not _detection_complete:
        if time.time() - _battle_start_time >= ANIMATION_DELAY:
            shiny_detected = is_shiny(frame, zone=shiny_zone, debug=True)
            _detection_complete = True
            
    # === Battle just ended ===
    if not battle and _last_battle_state:
        shiny_detected = False
        _battle_start_time = None
        _detection_complete = False
               
    # === Update state ===
    with _lock:
        in_battle = battle
        _last_battle_state = battle

    print(f"[TICK] in_battle={in_battle}, shiny_detected={shiny_detected}")

# === THREAD LOOP ===
def start_battle_detection(hwnd, interval=2.0, shiny_zone="starter"):
    """Start a background thread that continuously checks for battles."""
    def worker():
        while True:
            _check_battle(hwnd, shiny_zone=shiny_zone)
            time.sleep(interval)
    threading.Thread(target=worker, daemon=True).start()

# === API ===
def get_battle_state():
    with _lock:
        return in_battle, shiny_detected
