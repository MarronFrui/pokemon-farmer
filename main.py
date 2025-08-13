import time
import cv2
import numpy as np


from window_capture import find_window_by_title, capture_window, WINDOW_TITLE_SUBSTR

FRAME_INTERVAL_MS = 50        # Capture frame every 50 ms (~20 FPS)
SHOW_PREVIEW = True           # Show preview window of captured frames
SCALE_PREVIEW = 0.5           # Scale down preview for easier viewing


import win32con
import win32api
import time

def send_key(hwnd, key_code):
    """
    Sends a key press and release (key down and key up) message directly to the given window handle.
    """
    # WM_KEYDOWN and WM_KEYUP messages
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, key_code, 0)
    time.sleep(0.05)  # small delay to simulate key press duration
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, key_code, 0)
    

def send_circle(hwnd):
    # VK codes for arrow keys
    VK_RIGHT = 0x27
    VK_DOWN = 0x28
    VK_LEFT = 0x25
    VK_UP = 0x26
    
    send_key(hwnd, VK_RIGHT)
    time.sleep(0.3)
    send_key(hwnd, VK_DOWN)
    time.sleep(0.3)
    send_key(hwnd, VK_LEFT)
    time.sleep(0.3)
    send_key(hwnd, VK_UP)
    time.sleep(0.3)



def main():
    # Find emulator window handle by title substring
    hwnd = find_window_by_title(WINDOW_TITLE_SUBSTR)
    if not hwnd:
        print(f"[!] Could not find a window with title containing: '{WINDOW_TITLE_SUBSTR}'")
        return

    print(f"[*] Capturing window with HWND: {hwnd}")

    prev = time.perf_counter()
    interval = FRAME_INTERVAL_MS / 1000.0

    try:
        while True:
            now = time.perf_counter()
            if now - prev < interval:
                # Sleep to maintain target FPS and reduce CPU usage
                time.sleep(max(0.0, interval - (now - prev)))
            prev = time.perf_counter()

            # Capture the window's current frame as BGRA image
            frame_bgra = capture_window(hwnd)
            if frame_bgra is None:
                print("[!] Capture failed, retrying...")
                time.sleep(1)
                continue

            # Convert BGRA to BGR for OpenCV display
            frame_bgr = cv2.cvtColor(frame_bgra, cv2.COLOR_BGRA2BGR)

            # Show the preview window if enabled
            if SHOW_PREVIEW:
                height, width = frame_bgr.shape[:2]
                scaled = cv2.resize(frame_bgr, (int(width * SCALE_PREVIEW), int(height * SCALE_PREVIEW)), interpolation=cv2.INTER_NEAREST)
                cv2.imshow("mGBA Capture (debug)", scaled)

                # Press 'q' to quit preview and exit loop
                if cv2.waitKey(5) & 0xFF == ord('q'):
                    break

            # Call the function to send inputs and move character in circle
            send_circle(hwnd)

    finally:
        # Cleanup OpenCV windows on exit
        cv2.destroyAllWindows()
        print("[+] Clean exit.")


if __name__ == "__main__":
    main()
