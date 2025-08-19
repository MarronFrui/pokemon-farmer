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
SHINY_MATCH_THRESHOLD = 0.81
BATTLE_MATCH_THRESHOLD = 0.75
SHAPE_MATCH_THRESHOLD = 0.9
ANIMATION_DELAY = 2.0
MAX_SCREENSHOTS_PER_SHAPE = 10
WINDOW_NAME = "mGBA - Pokemon"

# === STATE ===
_lock = threading.Lock()
in_battle = False
shiny_detected = False
_battle_start_time = None
_detection_complete = False
_stop_thread = False
_thread_counter = 0 

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

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    if result != 1:
        return None
    return im

def _save_battle_frame(frame, limit=200, folder=BATTLE_TEMPLATES_FOLDER):
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
    cv2.imwrite(filename, frame)
    print(f"[DEBUG] Saved new battle template -> {filename}")

def capture_window(window_name: str):
    im = screenshot(window_name)
    if im is None:
        return None
    frame = np.array(im)[:, :, ::-1].copy()  # RGB → BGR
    return frame

# === DETECT SHAPE ===
def detect_shape(mask_frame, detection_frame, zone="starter", debug=False, shiny_event=None, not_shiny_event=None):
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

            res = cv2.matchTemplate(alpha_mask, ref_img, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if debug:
                print(f"[DEBUG] Comparing with {ref_path} -> match score {max_val:.3f}")

            if max_val >= SHAPE_MATCH_THRESHOLD:
                if is_shiny(detection_frame, color_folder, debug, shiny_event=shiny_event, not_shiny_event=not_shiny_event):
                    existing_shinies = sorted(os.listdir(shiny_folder))
                    if len(existing_shinies) < MAX_SCREENSHOTS_PER_SHAPE:
                        new_index = len(existing_shinies) + 1
                        save_frame(os.path.join(shiny_folder, f"{new_index}.png"), detection_frame, debug)
                else:
                    existing_colors = sorted(os.listdir(color_folder))
                    not_shiny_event.set()
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
        print(f"[DEBUG] Detected new unique shape -> {shape_folder}")

    return shape_folder

# === SHINY DETECTION ===
def is_shiny(detection_frame, color_folder, debug, shiny_event, not_shiny_event):
    if not os.path.exists(color_folder) or len(os.listdir(color_folder)) == 0:
        if debug:
            print(f"[WARN] No reference images found in {color_folder}")
        return False

    ref_images = []
    for ref_file in os.listdir(color_folder):
        ref_path = os.path.join(color_folder, ref_file)
        ref_img = cv2.imread(ref_path)
        if ref_img is not None:
            ref_images.append((ref_file, ref_img))

    if len(ref_images) == 0:
        if debug:
            print(f"[WARN] No valid reference images loaded from {color_folder}")
        return False

    shiny_found = False
    for ref_file, ref_img in ref_images:
        score = ssim(detection_frame, ref_img, channel_axis=-1)
        if debug:
            print(f"[DEBUG] Comparing with {ref_file} -> SSIM: {score:.3f}")
        if score < SHINY_MATCH_THRESHOLD:
            shiny_event.set()
            shiny_found = True
        else:
            not_shiny_event.set()

    return shiny_found

# === DETECTOR ===
def detector(frame, zone="starter", debug=True, shiny_event=None, not_shiny_event=None):
    zones = {
        "starter": (60, frame.shape[0] - 335, 300, 165),
        "enemy":   (450, frame.shape[0] - 450, 200, 150)
    }
    
    if zone not in zones:
        raise ValueError(f"[!] Unknown detection zone '{zone}'")

    x, y, w, h = zones[zone]
    detection_frame = np.ascontiguousarray(frame[y:y+h, x:x+w])
    # print(f"[DEBUG] Using rectangle for zone '{zone}': x={x}, y={y}, w={w}, h={h}")
    
    mask_frame = cv2.cvtColor(detection_frame, cv2.COLOR_BGR2GRAY)

    shape_folder = detect_shape(mask_frame, detection_frame, zone=zone, debug=True, shiny_event=shiny_event, not_shiny_event=not_shiny_event)


    color_folder = os.path.join(shape_folder, "color")
    ensure_folder(color_folder)

    return

# === BATTLE CHECK ===
def _check_battle(window_name, shiny_zone="starter", shiny_event=None, not_shiny_event=None):
    global in_battle, _battle_start_time, _detection_complete

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
  
    
    if battle and _battle_start_time is None:
        with _lock:
            _battle_start_time = now
            
    if not battle and _battle_start_time is not None:
        _battle_start_time = None

    if battle and _battle_start_time and not _detection_complete:
        if now - _battle_start_time >= ANIMATION_DELAY:
            with _lock:
                _detection_complete = True
                _save_battle_frame(frame)
                detector(frame, zone=shiny_zone, debug=True, shiny_event=shiny_event, not_shiny_event=not_shiny_event)

    with _lock:
        in_battle = battle

    print(f"[STATUS] in_battle={in_battle}")
    return _detection_complete

# === THREAD CONTROL ===
def start_battle_detection(hwnd, interval=1.0, shiny_zone=None, shiny_event=None, not_shiny_event=None):
    global _stop_thread, _detection_complete, _thread_counter 
    _stop_thread = False
    _detection_complete = False


    def worker():
        while not _stop_thread:
            if _check_battle(hwnd, shiny_zone=shiny_zone, shiny_event=shiny_event, not_shiny_event=not_shiny_event):
                break
            time.sleep(interval)

    t = threading.Thread(
        target=worker,
        daemon=True,
        name=f"battle-detector-{_thread_counter}"
    )
    t.start()
    _thread_counter += 1
    print(f"Thread object created: {t}, alive={t.is_alive()}")
    return t

def get_battle_state():
    with _lock:
        return in_battle
    
def reset_battle_state():
    global in_battle, _detection_complete
    with _lock:
        in_battle = False
        _detection_complete = False
    
def stop_detection():
    global _stop_thread
    _stop_thread = True
    time.sleep(0.1)
