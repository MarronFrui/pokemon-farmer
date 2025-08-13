import time
import cv2
import numpy as np
import mss
import win32gui
import threading

FRAME_INTERVAL_MS = 50

def find_window_by_title(substr: str):
    hwnd = None
    substr_low = substr.lower()
    def enum_handler(h, _):
        nonlocal hwnd
        if hwnd is not None or not win32gui.IsWindowVisible(h):
            return
        title = win32gui.GetWindowText(h)
        if substr_low in title.lower():
            hwnd = h
    win32gui.EnumWindows(enum_handler, None)
    return hwnd

def get_client_rect(hwnd):
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
    left_s, top_s = client_origin
    width = right - left
    height = bottom - top
    return left_s, top_s, left_s + width, top_s + height

def capture_window(hwnd):
    left, top, right, bottom = get_client_rect(hwnd)
    width, height = right-left, bottom-top
    if width <= 0 or height <= 0:
        return None
    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}
        img = np.array(sct.grab(monitor))[:, :, :3]
        return img

def run(hwnd, callback=None):
    """
    Main loop for mGBA window capture and preview.
    - callback(frame) will be called every frame if provided.
    """
    interval = FRAME_INTERVAL_MS / 1000
    stop_event = threading.Event()

    # Worker thread for callback processing
    def bot_worker():
        while not stop_event.is_set():
            frame = capture_window(hwnd)
            if frame is None:
                break
            if callback:
                callback(frame)
            if stop_event.wait(interval):
                break

    bot_thread = threading.Thread(target=bot_worker, daemon=True)
    bot_thread.start()

    # Preview loop in main thread
    try:
        while not stop_event.is_set():
            frame = capture_window(hwnd)
            if frame is None:
                break
            cv2.imshow("Preview", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                stop_event.set()
                break
            if stop_event.wait(interval):
                break
    finally:
        stop_event.set()
        bot_thread.join()
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        print("[+] Capture loop exited cleanly")
