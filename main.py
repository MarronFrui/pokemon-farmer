from window_capture import find_window_by_title, run
from battle_detection import get_battle_state
from shiny_starter_farming import farm_shiny_starters
from random_shiny import random_shiny_hunt
from botmenu import show_menu
import threading
import time

#main.py

def main():
    choice = show_menu()

    # Find the game window
    HWND = find_window_by_title("mGBA")
    if HWND is None:
        print("[!] Could not find mGBA window.")
        return

    # Start the selected bot module
    if choice == "1":
        print("[INFO] Starting Shiny Starter Farming...")
        farm_shiny_starters(HWND)
    elif choice == "2":
        print("[INFO] Starting Random Shiny Hunting...")
        random_shiny_hunt(HWND)
    else:
        print("[!] Invalid choice.")
        return

    # Start preview loop with debug rectangles (from window_capture)
    # The run() function already has its own loop
    run(HWND)

    # Optional: Print battle state periodically
    def print_state_loop():
        while True:
            in_battle, shiny = get_battle_state()
            print(f"[MAIN] in_battle={in_battle}, shiny_detected={shiny}")
            time.sleep(5)

    threading.Thread(target=print_state_loop, daemon=True).start()

if __name__ == "__main__":
    main()
