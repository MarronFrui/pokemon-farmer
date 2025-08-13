import threading
import time
from battle_detection import start_battle_detection, get_battle_state
import win32api
import win32con

# Key mapping for mGBA
VK = {
    'A': 0x58,  # X
    'B': 0x5A,  # Z
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
    'RESET': win32con.VK_F1
}

# Startup sequence
SEQUENCE = [
    ('UP', 0.5),
    ('UP', 0.5),
    ('A', 0.1),
    ('WAIT', 7.0),
    ('A', 0.1),
    ('WAIT', 1.0),
    ('A', 0.1),
    ('LEFT', 1.0),
    ('WAIT', 0.5),
    ('UP', 0.5),
    ('A', 0.5),
    ('A', 0.5),
    ('A', 0.5),
    ('WAIT', 6.0),
    ('A', 0.1)
]

def press_key(hwnd, key, duration=0.1):
    vk = VK.get(key.upper())
    if vk is None:
        raise ValueError(f"Unknown key {key}")
    print(f"[DEBUG] Pressing key: {key} for {duration}s")  # restored debug
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(duration)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)

def press_sequence(hwnd, sequence):
    for key, dur in sequence:
        if key.upper() == "WAIT":
            print(f"[DEBUG] Waiting for {dur}s")  # restored debug
            time.sleep(dur)
        else:
            press_key(hwnd, key, dur)
        time.sleep(0.5)  # slight delay between inputs

def shinystartermethod(hwnd):
    """Kick off the startup input sequence once and start battle detection."""
    
    if hasattr(shinystartermethod, "_started"):
        # Already initialized
        return
    
    shinystartermethod._started = True

    # Start battle detection in background
    start_battle_detection(hwnd, interval=1.0)  # 1s is enough

    # Run startup sequence in a separate thread
    def run_sequence():
        print("[+] Running startup input sequence...")
        press_sequence(hwnd, SEQUENCE)
        print("[+] Startup sequence done.")

    threading.Thread(target=run_sequence, daemon=True).start()
