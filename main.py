from window_capture import find_window_by_title, run
import shiny_starter_farming
import botmenu

if __name__ == "__main__":
    choice = botmenu.show_menu()
    if choice != "1":
        print("[-] Invalid selection. Exiting.")
        exit(1)
    print("[+] Selected bot: shiny_starter_farming")

    hwnd = find_window_by_title("mGBA")
    if not hwnd:
        print("[-] mGBA window not found.")
        exit(1)
    print(f"[+] Found mGBA HWND: {hwnd}")

    # Run the shinystarter sequence once
    shiny_starter_farming.shinystartermethod(hwnd)

    # Start preview loop (no bot logic in callback)
    run(hwnd, lambda frame: None)
