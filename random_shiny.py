import time
import win32api
import win32con
from battle_detection import start_battle_detection, stop_detection
import config


VK = {
    'A': 0x57,  # W
    'B': 0x58,  # X
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
    'RESET': win32con.VK_F1
}

# movement sequences
SEQUENCE_ENCOUNTER = [
    ('UP', 0.05), ('LEFT', 0.05), ('DOWN', 0.05), ('RIGHT', 0.05)
]

SEQUENCE_FLEE = [
    ('A', 0.1), ('WAIT', 4.0), ('RIGHT', 0.1), ('DOWN', 0.1),
    ('A', 0.1), ('WAIT', 1.0), ('A', 0.1)
]


def press_key(hwnd, key, duration=0.1):
    vk = VK.get(key.upper())
    if vk is None:
        raise ValueError(f"Unknown key {key}")
    # print(f"[INPUT] Pressing {key} for {duration}s")
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(duration)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)


def press_sequence(hwnd, sequence):
    # print(f"[SEQUENCE] Starting sequence: {sequence}")
    for key, dur in sequence:
        if key.upper() == "WAIT":
            print(f"[WAIT] {dur}s")
            time.sleep(dur)
        else:
            press_key(hwnd, key, dur)
    # print(f"[SEQUENCE] Finished sequence: {sequence}")


def random_shiny_hunt(hwnd, shiny_event, not_shiny_event):

    print("[INFO] Starting random shiny hunt loop")

    while True:
        # Clear events for this encounter
        shiny_event.clear()
        not_shiny_event.clear()

        # Start battle detection immediately
        thread = start_battle_detection(
            hwnd, interval=2.5, shiny_zone="enemy",
            shiny_event=shiny_event, not_shiny_event=not_shiny_event
        )
        # Move around until a battle starts
        print("[LOOP] Searching for battle...")
        while not config.in_battle:
            press_sequence(hwnd, SEQUENCE_ENCOUNTER)
 
        while thread.is_alive():
            time.sleep(0.1)
            if shiny_event.is_set() or not_shiny_event.is_set():
                stop_detection()
                thread.join()
                break

        # Handle the battle result
        if shiny_event.is_set():
            print("[ALERT] Shiny detected! Exiting farming loop.")
            return
        if not_shiny_event.is_set():
            print("[INFO] No shiny detected, fleeing...")
            press_sequence(hwnd, SEQUENCE_FLEE)
            config.in_battle = False

        # Small pause before next encounter loop
        print("[LOOP] Battle ended. Preparing next encounter...")
        time.sleep(4.0)
 
