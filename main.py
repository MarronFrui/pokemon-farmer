from window_capture import find_window_by_title  # hwnd for inputs
from battle_detection import screenshot          # frames for vision
from shiny_starter_farming import farm_shiny_starters
from random_shiny import random_shiny_hunt
from botmenu import show_menu
from shiny_starter_farming import farm_shiny_starters
import threading


def main():
    choice = show_menu()
    shiny_event = threading.Event()
    not_shiny_event = threading.Event()
    # hwnd for inputs
    hwnd = find_window_by_title("mGBA")
    if hwnd is None:
        print("[!] Could not find mGBA window.")
        return

    
    # start module
    if choice == "1":
        farm_shiny_starters(hwnd, shiny_event, not_shiny_event)
    elif choice == "2":
        random_shiny_hunt(hwnd, shiny_event, not_shiny_event)
    else:
        print("[!] Invalid choice.")
        return


if __name__ == "__main__":
    main()
