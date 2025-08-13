import threading
import time
import win32api
import win32con
from battle_detection import start_battle_detection

VK = {
    'A': 0x58,  # X
    'B': 0x5A,  # Z
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
    'RESET': win32con.VK_F1
}

SEQUENCE = [
    ('UP', 0.5), ('UP', 0.5), ('A', 0.1), ('WAIT', 7.0),
    ('A', 0.1), ('WAIT', 1.0), ('A', 0.1), ('LEFT', 1.0),
    ('WAIT', 0.5), ('UP', 0.5), ('A', 0.5), ('A', 0.5),
    ('A', 0.5), ('WAIT', 6.0), ('A', 0.1)
]

def press_key(hwnd, key, duration=0.1):
    vk = VK.get(key.upper())
    if vk is None:
        raise ValueError(f"Unknown key {key}")
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(duration)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)

def press_sequence(hwnd, sequence):
    for key, dur in sequence:
        if key.upper() == "WAIT":
            time.sleep(dur)
        else:
            press_key(hwnd, key, dur)
        time.sleep(0.5)

def farm_shiny_starters(hwnd):
    if hasattr(farm_shiny_starters, "_started"):
        return
    farm_shiny_starters._started = True

    # Start battle detection in the starter zone
    start_battle_detection(hwnd, interval=1.0, shiny_zone="starter")
    def run_sequence():
        press_sequence(hwnd, SEQUENCE)

    threading.Thread(target=run_sequence, daemon=True).start()
