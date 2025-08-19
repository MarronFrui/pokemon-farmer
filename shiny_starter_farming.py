# shiny_starter_farming_fixed.py
import time
import win32api
import win32con
from battle_detection import start_battle_detection, stop_detection
import random
import time


# === KEY MAPPING ===
VK = {
    'A': 0x58,        # X
    'B': 0x5A,        # Z
    'SELECT': 0x56,   # V
    'START': 0x42,    # B
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
}

min_interval = 0
max_interval = 15
wait = random.uniform(min_interval, max_interval)


# === MOVEMENT SEQUENCES ===
SEQUENCE_STARTER = [
    # ('UP', 0.5), ('UP', 0.5), ('A', 0.1), ('WAIT', 7.0),
    # ('A', 0.1), ('WAIT', 1.0), ('A', 0.1), ('LEFT', 0.9),
    # ('WAIT', 0.05), ('UP', 0.2) 
    ('A', 0.5), ('A', 0.5), ('A', 0.5),
    ('A', 0.5), ('WAIT', 7.0), ('A', 0.5), ('WAIT', 4.0)
]

RESTART_FIRST = ['A', 'B', 'START', 'SELECT']
RESTART_REST = [
    ('WAIT', 3.0), ('A', 0.5), ('WAIT', 1.0),
    ('A', 0.5), ('A', 0.5), ('WAIT', 1.0), ('A', 0.5), ('WAIT', 1.0)
]

# === INPUT HELPERS ===
def press_key(hwnd, key, duration=0.1):
    vk = VK.get(key.upper())
    if vk is None:
        raise ValueError(f"Unknown key {key}")
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(duration)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)

def press_sequence(hwnd, sequence):
    for item in sequence:
        if isinstance(item, tuple):
            key, dur = item
            if key.upper() == "WAIT":
                time.sleep(dur)
            else:
                press_key(hwnd, key, dur)
            time.sleep(0.2)

def press_multiple(hwnd, keys, duration=0.2):
    for k in keys:
        vk = VK.get(k.upper())
        if vk is None:
            continue
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(duration)
    for k in keys:
        vk = VK.get(k.upper())
        if vk is None:
            continue
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)

# === MAIN FARMING LOOP ===
def farm_shiny_starters(hwnd, shiny_event, not_shiny_event):
    print("[INFO] Starting shiny starter farming...")

    while True:

        # Trigger starter encounter
        time.sleep(wait)
        press_sequence(hwnd, SEQUENCE_STARTER)

        # Start battle detection thread
        shiny_event.clear()
        not_shiny_event.clear()
        thread = start_battle_detection(hwnd, interval=2.0, shiny_zone="starter", shiny_event=shiny_event, not_shiny_event=not_shiny_event)

        # Monitor detection
        while thread.is_alive():
            
            if not_shiny_event.is_set():
                stop_detection()
                thread.join()
                print("[INFO] Normal encounter ended. Restarting...")
                break
            time.sleep(0.5)
        
            if shiny_event.is_set():
                stop_detection() 
                thread.join()
                print("[ALERT] Shiny detected! Exiting farming loop.")
                return
        
        # Restart combo for next attempt
        press_multiple(hwnd, RESTART_FIRST, duration=2.0)
        press_sequence(hwnd, RESTART_REST)
        time.sleep(0.5)

