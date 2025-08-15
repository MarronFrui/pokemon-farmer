import threading
import time
import win32api
import win32con
from battle_detection import start_battle_detection, stop_detection, get_battle_state

#shiny_starter_farming.py

# Virtual key mapping (keyboard scancodes / VK codes)
VK = {
    'A': 0x58,        # X key
    'B': 0x5A,        # Z key
    'SELECT': 0x56,   # V key
    'START': 0x42,    # B key
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
}

# Main sequence to trigger starter encounter
SEQUENCE = [
    ('UP', 0.5), ('UP', 0.5), ('A', 0.1), ('WAIT', 7.0),
    ('A', 0.1), ('WAIT', 1.0), ('A', 0.1), ('LEFT', 1.0),
    ('WAIT', 0.5), ('UP', 0.5), ('A', 0.5), ('A', 0.5),
    ('A', 0.5), ('WAIT', 10.0), ('A', 0.5), ('WAIT', 5.0)
]

# Restart combo keys
RESTART_SEQUENCE_FIRST = ['A', 'B', 'START', 'SELECT']
RESTART_SEQUENCE_REST = [
    ('WAIT', 4.0), ('A', 0.5), ('WAIT', 2.0),
    ('A', 0.5), ('A', 0.5), ('WAIT', 1.0), ('A', 0.5), ('WAIT', 2.0)
]

# Global lock for shared battle state
battle_lock = threading.Lock()
shiny_detected = False


def press_key(hwnd, key, duration=0.1):
    vk = VK.get(key.upper())
    if vk is None:
        raise ValueError(f"Unknown key: {key}")
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    print(f"[INPUT] Key down: {key}")
    time.sleep(duration)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)


def press_sequence(hwnd, sequence):
    for item in sequence:
        if isinstance(item, tuple):
            key, dur = item
            if key.upper() == "WAIT":
                print(f"[INPUT] Waiting {dur} seconds")
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
        print(f"[INPUT] Multiple key down: {k}")
    time.sleep(duration)
    for k in keys:
        vk = VK.get(k.upper())
        if vk is None:
            continue
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)


def farm_shiny_starters(hwnd):
    global shiny_detected
    print("[INFO] Starting shiny starter farming loop")

    while True:
        # Start battle detection
        thread = start_battle_detection(hwnd, interval=2.0, shiny_zone="starter")

        # Run initial sequence to trigger encounter
        press_sequence(hwnd, SEQUENCE)

        # Wait for battle result
        while thread.is_alive():
            in_battle, shiny_detected = get_battle_state()  # get fresh values from detection
            if not in_battle:
                stop_detection()
                thread.join()
                time.sleep(0.5)
                print("[INFO] Normal encounter ended, restarting...")
                break
            if shiny_detected:
                stop_detection()
                thread.join()
                time.sleep(0.5)
                print("[ALERT] Shiny detected! Stopping farming loop.")
                return
            time.sleep(0.5)

        # Restart combo
        press_multiple(hwnd, RESTART_SEQUENCE_FIRST, duration=2.0)
        press_sequence(hwnd, RESTART_SEQUENCE_REST)



