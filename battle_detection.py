import cv2
import numpy as np
import threading
import time
import os
from window_capture import capture_window

# === CONFIG ===
BATTLE_TEMPLATES_FOLDER = os.path.join("data", "battle_templates")
DATABASE_FOLDER = os.path.join("data", "pokemon_database")
SHINY_MATCH_THRESHOLD = 0.5
BATTLE_MATCH_THRESHOLD = 0.45
SHAPE_MATCH_THRESHOLD = 0.6
ANIMATION_DELAY = 8.0
MAX_SCREENSHOTS_PER_SHAPE = 500
BATTLE_GRACE_TIME = 3.0

# === STATE ===
_lock = threading.Lock()
in_battle = False
shiny_detected = False
_last_battle_state = False
_battle_start_time = None
_detection_complete = False
_stop_thread = False

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

def ensure_folder(*paths):
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)

def save_frame(path, frame, debug=None):
    cv2.imwrite(path, frame)
    if debug:
        print(f"[DEBUG] Saved frame -> {path}")

battle_templates = load_templates(BATTLE_TEMPLATES_FOLDER)

# === SHAPE DETECTION ===
def detect_shape(gray_frame, color_frame, debug=True):
    """Return shape folder path for the given grayscale frame."""
    # Compute a simple hash of the grayscale image
    shape_hash = hash(gray_frame.tobytes())
    shape_folder = os.path.join(DATABASE_FOLDER, f"shape_{shape_hash}")
    greyscale_folder = os.path.join(shape_folder, "greyscale")
    color_folder = os.path.join(shape_folder, "color")

    ensure_folder(greyscale_folder)
    ensure_folder(color_folder)

    # First time seeing this shape
    if not os.listdir(greyscale_folder):
        save_frame(os.path.join(greyscale_folder, "ref.png"), gray_frame, debug)
        save_frame(os.path.join(color_folder, "1.png"), color_frame, debug)
        if debug:
            print(f"[DEBUG] New shape detected -> {shape_folder}")
        return shape_folder


    ref_path = os.path.join(greyscale_folder, "ref.png")
    if os.path.exists(ref_path):
        ref_img = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        if ref_img is not None:
            res = cv2.matchTemplate(gray_frame, ref_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if debug:
                print(f"[DEBUG] Shape match score: {max_val:.3f} against {ref_path}")
            if max_val >= SHAPE_MATCH_THRESHOLD:
                existing_colors = sorted(os.listdir(color_folder))
                new_index = len(existing_colors) + 1
                save_frame(os.path.join(color_folder, f"{new_index}.png"), color_frame, debug)
                is_shiny(color_frame, color_folder, debug=True)
                return shape_folder
      
    # No match found, treat as new shape
    new_index = len(os.listdir(DATABASE_FOLDER))
    shape_folder = os.path.join(DATABASE_FOLDER, f"shape_{new_index}")
    greyscale_folder = os.path.join(shape_folder, "greyscale")
    color_folder = os.path.join(shape_folder, "color")
    ensure_folder(greyscale_folder)
    ensure_folder(color_folder)
    save_frame(os.path.join(greyscale_folder, "ref.png"), gray_frame, debug)
    save_frame(os.path.join(color_folder, "1.png"), color_frame, debug)
    if debug:
        print(f"[DEBUG] Detected new unique shape -> {shape_folder}")

    return shape_folder

# === SHINY DETECTION ===
def is_shiny(new_frame, color_folder, debug=True):
    """
    Compare the new color frame against existing color frames in the folder.
    Return True if the new frame differs significantly -> shiny detected.
    """
    existing_files = sorted(os.listdir(color_folder))
    if not existing_files:
        if debug:
            print(f"[DEBUG] No existing frames in {color_folder} to compare")
        return False

    for f in existing_files:
        db_img_path = os.path.join(color_folder, f)
        db_img = cv2.imread(db_img_path)
        if db_img is None:
            if debug:
                print(f"[WARN] Could not read {db_img_path}")
            continue
        diff = cv2.absdiff(db_img, new_frame)
        mean_diff = np.mean(diff)
        if debug:
            print(f"[DEBUG] Comparing with {f} -> mean diff {mean_diff:.2f}")
        if mean_diff > SHINY_MATCH_THRESHOLD * 255:
            if debug:
                print(f"[ALERT] Shiny detected! Difference with {f} -> {mean_diff:.2f}")
            return True

    # If no frame differs enough, not shiny
    if debug:
        print(f"[DEBUG] No significant differences found -> not shiny")
    return False

# === Manage overhaul detection ===
def detector(frame, zone="starter", debug=True):
    """Detect shape and determine if the Pokémon is shiny by comparing color frames."""
    zones = {
        "starter": (60, frame.shape[0] - 320, 300, 165),
        "enemy":   (450, frame.shape[0] - 430, 200, 150)
    }
    if zone not in zones:
        raise ValueError(f"[!] Unknown detection zone '{zone}'")

    x, y, w, h = zones[zone]
    detection_frame = np.ascontiguousarray(frame[y:y+h, x:x+w])
    gray_frame = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2GRAY)

    shape_folder = detect_shape(gray_frame, detection_frame, debug)

    greyscale_folder = os.path.join(shape_folder, "greyscale")
    color_folder = os.path.join(shape_folder, "color")
    ensure_folder(color_folder)

    # First time seeing this shape -> not shiny
    if len(os.listdir(greyscale_folder)) == 1:
        if debug:
            print(f"[DEBUG] First time seeing this shape -> not shiny")
        save_frame(os.path.join(color_folder, "1.png"), detection_frame, debug)
        return False

    # Compare with existing color frames
    existing_files = sorted(os.listdir(color_folder))
    for f in existing_files:
        db_img = cv2.imread(os.path.join(color_folder, f))
        if db_img is None:
            continue
        diff = cv2.absdiff(db_img, detection_frame)
        mean_diff = np.mean(diff)
        if debug:
            print(f"[DEBUG] Comparing with {f} -> mean diff {mean_diff:.2f}")
        if mean_diff > SHINY_MATCH_THRESHOLD * 255:
            if debug:
                print(f"[DEBUG] Possible shiny detected with {f}")
            return True

    # Save new frame if under limit
    if len(existing_files) < MAX_SCREENSHOTS_PER_SHAPE:
        save_frame(os.path.join(color_folder, f"{len(existing_files)+1}.png"), detection_frame, debug)

    return False

# === BATTLE CHECK ===
def _check_battle(hwnd, shiny_zone="starter"):
    global in_battle, shiny_detected, _last_battle_state, _battle_start_time, _detection_complete

    now = time.time()
    frame = capture_window(hwnd)
    if frame is None:
        return False

    battle = False
    for template in battle_templates:
        res = cv2.matchTemplate(frame, template.img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > BATTLE_MATCH_THRESHOLD:
            battle = True
            break

    if battle and not _last_battle_state:
        print("[DEBUG] Battle detected, starting animation delay...")
        _battle_start_time = now
        shiny_detected = False
        _detection_complete = False
        print("[INFO] Battle started")

    if battle and _battle_start_time and not _detection_complete:
        if now - _battle_start_time >= ANIMATION_DELAY:
            shiny_detected = detector(frame, zone=shiny_zone)
            _detection_complete = True

    #Prevent false negative to end the combat
    if not battle and _last_battle_state:
        if _battle_start_time and now - _battle_start_time < BATTLE_GRACE_TIME:
            battle = True
        else:
            print("[INFO] Battle ended")

    with _lock:
        in_battle = battle
        _last_battle_state = battle

    print(f"[STATUS] in_battle={in_battle}, shiny_detected={shiny_detected}")
    return _detection_complete

# === THREAD CONTROL ===
def start_battle_detection(hwnd, interval=1.0, shiny_zone="starter"):
    global _stop_thread, _detection_complete
    _stop_thread = False
    _detection_complete = False

    def worker():
        global _stop_thread
        print(f"[DEBUG] Thread started for shiny_zone='{shiny_zone}'")
        while not _stop_thread and not _detection_complete:
            print("[DEBUG] Worker loop iteration")
            _check_battle(hwnd, shiny_zone=shiny_zone)
            time.sleep(interval)
        print("[DEBUG] Thread exiting... stop_thread =", _stop_thread, "detection_complete =", _detection_complete)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    print(f"[DEBUG] Thread object created: {t}, alive={t.is_alive()}")
    return t


def get_battle_state():
    with _lock:
        return in_battle, shiny_detected
    
def stop_detection():
    global _stop_thread
    _stop_thread = True
    while threading.active_count() > 1 and not _detection_complete:
        time.sleep(0.05)