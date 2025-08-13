from window_capture import find_window_by_title, run
from battle_detection import get_battle_state, start_battle_detection
from shiny_starter_farming import farm_shiny_starters
from botmenu import show_menu
import threading
import time

def main():
    show_menu()
    # Find the game window
    HWND = find_window_by_title("mGBA")
    if HWND is None:
        print("[!] Could not find mGBA window.")
        return

    # Start battle detection in background
    start_battle_detection(HWND, interval=2.0)

    # Start shiny starter farming in background
    farm_shiny_starters(HWND)

    # Start preview loop with debug rectangles
    # The run() function already has its own loop, so we run it in the main thread
    run(HWND)

    # Optional: Main loop to print state every few seconds (runs alongside preview)
    def print_state_loop():
        while True:
            in_battle, shiny = get_battle_state()
            print(f"[MAIN] in_battle={in_battle}, shiny_detected={shiny}")
            time.sleep(5)

    threading.Thread(target=print_state_loop, daemon=True).start()

if __name__ == "__main__":
    main()
