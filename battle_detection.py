import cv2
import numpy as np
import threading
import time
import os
from skimage.metrics import structural_similarity as ssim
from ctypes import windll
import win32gui
import win32ui
from PIL import Image

#battle_detection.py

# === CONFIG ===
BATTLE_TEMPLATES_FOLDER = os.path.join("data", "battle_templates")
DATABASE_FOLDER = os.path.join("data", "pokemon_database")
SHINY_MATCH_THRESHOLD = 0.8
BATTLE_MATCH_THRESHOLD = 0.5
SHAPE_MATCH_THRESHOLD = 0.9
ANIMATION_DELAY = 10.0
MAX_SCREENSHOTS_PER_SHAPE = 10
BATTLE_GRACE_TIME = 3.0
WINDOW_NAME = "mGBA - Pokemon"

# === STATE ===
_lock = threading.Lock()
in_battle = False
shiny_detected = False
_last_battle_state = False
_battle_start_time = 0
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

# === WIN32 SCREENSHOT ===
def screenshot(window_ref):
    # If window_ref is an int, treat as hwnd
    if isinstance(window_ref, int):
        hwnd = window_ref
    else:
        hwnd = win32gui.FindWindow(None, window_ref)

    if not hwnd:
        return None
    
    left, top, right, bot = win32gui.GetWindowRect(hwnd)
    w, h = right - left, bot - top
    if w <= 0 or h <= 0:
        return None

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 1)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                          bmpstr, 'raw', 'BGRX', 0, 1)

    # Cleanup
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    if result != 1:
        return None
    return im

def _save_battle_frame(frame, limit=200, folder=BATTLE_TEMPLATES_FOLDER):
    ensure_folder(folder)

    # Get numeric suffixes of existing battle files
    existing_files = sorted(os.listdir(folder))
    existing_indices = []
    for f in existing_files:
        if f.startswith("battle_") and f.endswith(".png"):
            try:
                idx = int(f.split("_")[1].split(".")[0])
                existing_indices.append(idx)
            except ValueError:
                continue

    # Find the first unused index
    new_index = 1
    while new_index in existing_indices:
        new_index += 1

    if new_index > limit:
        return  # don't save if limit exceeded

    filename = os.path.join(folder, f"battle_{new_index:03d}.png")
    cv2.imwrite(filename, frame)
    print(f"[DEBUG] Saved new battle template -> {filename}")

def capture_window(window_name: str):
    im = screenshot(window_name)
    if im is None:
        return None
    frame = np.array(im)[:, :, ::-1].copy()  # Convert RGB → BGR
    return frame

# === DETECT SHAPE ===
def detect_shape(mask_frame, color_frame, debug=True):
    """Return shape folder path for the given frame using an alpha mask."""

    # Convert mask_frame to alpha mask
    _, alpha_mask = cv2.threshold(mask_frame, 240, 255, cv2.THRESH_BINARY_INV)

    # Scan existing shapes
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

            # Ensure types match
            if alpha_mask.dtype != ref_img.dtype:
                alpha_mask = alpha_mask.astype(ref_img.dtype)

            res = cv2.matchTemplate(alpha_mask, ref_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if debug:
                print(f"[DEBUG] Comparing with {ref_path} -> match score {max_val:.3f}")

            if max_val >= SHAPE_MATCH_THRESHOLD:
                # Shape matched -> check if shiny
                if is_shiny(color_frame, color_folder, debug):
                    existing_shinies = sorted(os.listdir(shiny_folder))
                    if len(existing_shinies) < MAX_SCREENSHOTS_PER_SHAPE:
                        new_index = len(existing_shinies) + 1
                        save_frame(os.path.join(shiny_folder, f"{new_index}.png"), color_frame, debug)
                else:
                    existing_colors = sorted(os.listdir(color_folder))
                    if len(existing_colors) < MAX_SCREENSHOTS_PER_SHAPE:
                        new_index = len(existing_colors) + 1
                        save_frame(os.path.join(color_folder, f"{new_index}.png"), color_frame, debug)

                return shape_folder

   # No match found -> create new unique shape folder
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
    save_frame(os.path.join(color_folder, "1.png"), color_frame, debug)
    if debug:
        print(f"[DEBUG] Detected new unique shape -> {shape_folder}")

    return shape_folder

# === SHINY DETECTION ===
def is_shiny(new_frame, color_folder, debug=True):
    """
    Compare the new color frame against existing color frames in the folder using SSIM.
    Allows for small vertical alignment offsets to reduce false shiny detections.
    """
    existing_files = sorted(os.listdir(color_folder))
    gray_new_base = cv2.cvtColor(new_frame, cv2.COLOR_BGR2GRAY)

    shiny_found = False
    best_overall_score = -1.0
    max_offset = 3  # pixels to shift up/down

    for f in existing_files:
        db_img_path = os.path.join(color_folder, f)
        db_img = cv2.imread(db_img_path)
        if db_img is None:
            if debug:
                print(f"[WARN] Could not read {db_img_path}")
            continue

        gray_db = cv2.cvtColor(db_img, cv2.COLOR_BGR2GRAY)

        # Match sizes
        if gray_db.shape != gray_new_base.shape:
            min_h = min(gray_db.shape[0], gray_new_base.shape[0])
            min_w = min(gray_db.shape[1], gray_new_base.shape[1])
            gray_db = gray_db[:min_h, :min_w]
            gray_new_base = gray_new_base[:min_h, :min_w]

        # Try vertical offsets
        best_score_for_file = -1.0
        for dy in range(-max_offset, max_offset + 1):
            shifted = np.roll(gray_new_base, dy, axis=0)

            # Zero out wrapped-around rows to avoid false matches
            if dy > 0:
                shifted[:dy, :] = 0
            elif dy < 0:
                shifted[dy:, :] = 0

            score, _ = ssim(shifted, gray_db, full=True)
            best_score_for_file = max(best_score_for_file, score)

        if debug:
            print(f"[DEBUG] Best SSIM vs {f} -> {best_score_for_file:.3f}")

        best_overall_score = max(best_overall_score, best_score_for_file)

        if best_score_for_file < SHINY_MATCH_THRESHOLD:
            shiny_found = True
            if debug:
                print(f"[ALERT] Shiny detected! Best score vs {f} -> {best_score_for_file:.3f}")
            break

    return shiny_found

# === DETECTOR ===
def detector(frame, zone="starter", debug=True):
    """Detect shape and determine if the Pokémon is shiny by comparing color frames."""

    zones = {
        "starter": (60, frame.shape[0] - 335, 300, 165),
        "enemy":   (450, frame.shape[0] - 430, 200, 150)
    }
    
    if zone not in zones:
        raise ValueError(f"[!] Unknown detection zone '{zone}'")

    x, y, w, h = zones[zone]
    detection_frame = np.ascontiguousarray(frame[y:y+h, x:x+w])

    # Create mask for shape detection (grayscale)
    mask_frame = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2GRAY)

    # Detect the shape and get its folder
    shape_folder = detect_shape(mask_frame, detection_frame, debug)

    # Ensure color folder exists
    color_folder = os.path.join(shape_folder, "color")
    ensure_folder(color_folder)

    # Check for shiny
    return is_shiny(detection_frame, color_folder, debug)

# === BATTLE CHECK ===
def _check_battle(window_name, shiny_zone="starter"):
    global in_battle, shiny_detected, _last_battle_state, _battle_start_time, _detection_complete

    
    now = time.time()
    frame = capture_window(window_name)
    if frame is None:
        return False

    battle = False
    for template in battle_templates:
        target_h, target_w = frame.shape[:2]
        template_resized = cv2.resize(template.img, (target_w, target_h), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(frame, template_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > BATTLE_MATCH_THRESHOLD:
            battle = True
            break

    if battle and not _last_battle_state:
        print("[DEBUG] Battle detected, starting animation delay...")
        with _lock:
            _battle_start_time = now
            shiny_detected = False
            _detection_complete = False
        print("[INFO] Battle started")

    if battle and _battle_start_time and not _detection_complete:
        if now - _battle_start_time >= ANIMATION_DELAY:
            with _lock:
                _save_battle_frame(frame)
                shiny_detected = detector(frame, zone=shiny_zone)
                _detection_complete = True

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
def start_battle_detection(window_name=WINDOW_NAME, interval=1.0, shiny_zone="starter"):
    global _stop_thread, _detection_complete
    _stop_thread = False
    _detection_complete = False

    def worker():
        global _stop_thread
        while not _stop_thread and not _detection_complete:
            _check_battle(window_name, shiny_zone=shiny_zone)
            time.sleep(interval)

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
    # Wait a short moment for thread to exit
    time.sleep(0.1)