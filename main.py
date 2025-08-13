from botmenu import get_bot_choice
from window_capture import find_window_by_title, run
import shiny_starter_farming

def main():
    choice = get_bot_choice()
    if choice == "1":
        print("[+] Selected bot: shiny_starter_farming")
        bot_callback = shiny_starter_farming.shinystartermethod
    else:
        print("[-] Invalid selection")
        return

    hwnd = find_window_by_title("mGBA")
    if hwnd is None:
        print("[-] mGBA window not found.")
        return

    print(f"[*] Capturing window with HWND: {hwnd}")
    run(hwnd, bot_callback)

if __name__ == "__main__":
    main()
