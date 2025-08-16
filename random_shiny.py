import time
import win32api
import win32con
from battle_detection import start_battle_detection, get_battle_state
VK = {
    'A': 0x58,  # X
    'B': 0x5A,  # Z
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
    'RESET': win32con.VK_F1
}

# movement sequences
SEQUENCE_ENCOUNTER = [
    ('UP', 0.1), ('LEFT', 0.1), ('DOWN', 0.1), ('RIGHT', 0.1)
]

SEQUENCE_FLEE = [
    ('RIGHT', 0.1), ('DOWN', 0.1), ('A', 0.1)
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

def random_shiny_hunt(hwnd):
    global shiny_detected
    print("[INFO] Starting random shiny hunt loop")

    while True:
        shiny_detected = False  # reset per encounter

        # Start battle detection for this encounter
        thread = start_battle_detection(hwnd, interval=2.0, shiny_zone="enemy")

        # Trigger the encounter
        press_sequence(hwnd, SEQUENCE_ENCOUNTER)

        # Wait until the battle ends (thread completes)
        thread.join()

        # Check battle result
        in_battle, shiny_detected = get_battle_state()

        if shiny_detected:
            print("[ALERT] Shiny detected! Stopping hunt.")
            return
        else:
            print("[INFO] No shiny detected, fleeing...")
            press_sequence(hwnd, SEQUENCE_FLEE)

        # Optional delay before next encounter
        time.sleep(1.0)
