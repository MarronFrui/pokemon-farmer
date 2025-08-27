import time
import win32api
import win32con
import config
from battle_detection import start_battle_detection, stop_detection


VK = {
    'A': 0x57,  # W
    'B': 0x58,  # X
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
    'RESET': win32con.VK_F1
}

SEQUENCE_ENCOUNTER = [
    ('UP', 0.05), ('WAIT', 0.1),
    ('DOWN', 0.05), ('WAIT', 0.1),
    ('RIGHT', 0.05), ('WAIT', 0.1),
    ('LEFT', 0.05), ('WAIT', 0.1)
]

SEQUENCE_A_BUTTON = [
    ('A', 0.5), ('WAIT', 4.0)
]

SEQUENCE_FLEE = [
    ('RIGHT', 0.1), ('DOWN', 0.1),
    ('A', 0.1), ('WAIT', 0.75), ('A', 0.1)
]


def press_key(hwnd, key, duration=0.1):
    vk = VK.get(key.upper())
    if vk is None:
        config.log_print(f"[WARN] Unknown key {key}")
        return
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
    time.sleep(duration)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)


def press_sequence(hwnd, sequence):
    for key, dur in sequence:
        if key.upper() == "WAIT":
            time.sleep(dur)
        else:
            press_key(hwnd, key, dur)


def random_shiny_hunt(hwnd, shiny_event, not_shiny_event):

    config.log_print("[INFO] Starting random shiny hunt loop")

    while not config.stop_program:
        shiny_event.clear()
        not_shiny_event.clear()

        # Start battle detection
        thread = start_battle_detection(
            hwnd, interval=1.0, shiny_zone="enemy",
            shiny_event=shiny_event, not_shiny_event=not_shiny_event
        )

        config.log_print("[LOOP] Searching for battle...")
        while not config.in_battle:
            press_sequence(hwnd, SEQUENCE_ENCOUNTER)

        while thread.is_alive():
            time.sleep(0.1)

            if shiny_event.is_set():
                config.log_print("[ALERT] Shiny detected! Exiting farming loop.")
                stop_detection()
                thread.join()
                config.stop_program = True
                break

            if not_shiny_event.is_set():
                config.log_print("[INFO] No shiny detected, fleeing...")
                press_sequence(hwnd, SEQUENCE_A_BUTTON)
                while config.in_battle:
                    press_sequence(hwnd, SEQUENCE_FLEE)
                    time.sleep(3.0)

                stop_detection()
                thread.join()
                config.log_print("[INFO] Normal encounter ended. Restarting...")
                break

        config.log_print("[LOOP] Battle ended. Preparing next encounter...")
        config.in_battle = False

    config.running_mode = None
    stop_detection()
    config.log_print("[INFO] Farming loop fully stopped.")
