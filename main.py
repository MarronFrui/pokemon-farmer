# main.py
from window_capture import find_window_by_title, run, WINDOW_TITLE_SUBSTR

# Import your farming logic (to be created)
# Example: from shiny_starter_farming import handle_frame

def main():
    # Find emulator window handle
    hwnd = find_window_by_title(WINDOW_TITLE_SUBSTR)
    if not hwnd:
        print(f"[!] Could not find a window with title containing '{WINDOW_TITLE_SUBSTR}'")
        return

    print(f"[*] Capturing window with HWND: {hwnd}")

    # Define callback for captured frames
    def frame_callback(frame):
        # Pass the frame to your farming logic
        # handle_frame(frame)
        # For now, just print frame shape
        print(f"[+] Captured frame: {frame.shape}")

    # Run the capture loop (blocks, feeds frames to callback)
    run(hwnd, frame_callback)

if __name__ == "__main__":
    main()
