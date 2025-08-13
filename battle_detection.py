import cv2
import numpy as np
import threading
import time
from window_capture import capture_window
import os

BATTLE_TEMPLATES_FOLDER = os.path.join("data", "battle_templates")
SHINY_TEMPLATES_FOLDER = os.path.join("data", "pokemon_shiny")

battle_templates = []
shiny_templates = []

def load_templates(folder):
    templates = []
    if not os.path.exists(folder):
        return templates
    for f in os.listdir(folder):
        path = os.path.join(folder, f)
        img = cv2.imread(path)
        if img is not None:
            templates.append(img)
    return templates

battle_templates = load_templates(BATTLE_TEMPLATES_FOLDER)
shiny_templates = load_templates(SHINY_TEMPLATES_FOLDER)

in_battle = False
shiny_detected = False
_last_battle_state = False
_lock = threading.Lock()

def _check_battle(hwnd):
    global in_battle, shiny_detected, _last_battle_state

    frame = capture_window(hwnd)
    if frame is None:
        return

    battle = False
    for template in battle_templates:
        t_resized = cv2.resize(template, (frame.shape[1], frame.shape[0]))
        res = cv2.matchTemplate(frame, t_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > 0.3:
            battle = True
            break
    if battle != _last_battle_state:
        print(f"[DEBUG] Battle state changed: {battle}")

    shiny = False
    if battle and not _last_battle_state:  # new battle
        for template in shiny_templates:
            t_resized = cv2.resize(template, (frame.shape[1], frame.shape[0]))
            res = cv2.matchTemplate(frame, t_resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > 0.2:
                shiny = True
                print("[DEBUG] Shiny detected!")
                break

    with _lock:
        in_battle = battle
        shiny_detected = shiny
        _last_battle_state = battle

    # Always print status every tick
    print(f"[TICK] in_battle={in_battle}, shiny_detected={shiny_detected}")

def start_battle_detection(hwnd, interval=2.0):
    def worker():
        while True:
            _check_battle(hwnd)
            time.sleep(interval)
    threading.Thread(target=worker, daemon=True).start()

def get_battle_state():
    with _lock:
        return in_battle, shiny_detected
