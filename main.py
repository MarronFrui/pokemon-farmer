from window_capture import find_window_by_title  # hwnd for inputs
from battle_detection import screenshot          # frames for vision
from shiny_starter_farming import farm_shiny_starters
from random_shiny import random_shiny_hunt
from botmenu import show_menu
import threading
import time

def main():
    choice = show_menu()

    # hwnd for inputs
    hwnd = find_window_by_title("mGBA")
    if hwnd is None:
        print("[!] Could not find mGBA window.")
        return

    # start module
    if choice == "1":
        farm_shiny_starters(hwnd)
    elif choice == "2":
        random_shiny_hunt(hwnd)
    else:
        print("[!] Invalid choice.")
        return

    # Debug thread: print battle state from screenshots
    def print_state_loop():
        while True:
            frame = screenshot("mGBA")
            if frame is not None:
                # later you’ll call get_battle_state(frame)
                print("[DEBUG] Screenshot captured")
            time.sleep(5)

    threading.Thread(target=print_state_loop, daemon=True).start()

if __name__ == "__main__":
    main()
