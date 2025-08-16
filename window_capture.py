import threading
import numpy as np
import mss
import win32gui


#window_capture.py

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
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return None
    with mss.mss() as sct:
        monitor = {"top": top, "left": left, "width": width, "height": height}
        img = np.array(sct.grab(monitor))[:, :, :3]
        return img

def run(hwnd):
    """
    Main loop for window capture and preview.
    """
    stop_event = threading.Event()
    interval = FRAME_INTERVAL_MS / 1000
    frame_lock = threading.Lock()
    shared_frame = {"frame": None}

    # Worker thread for capturing frames
    def capture_worker():
        while not stop_event.is_set():
            frame = capture_window(hwnd)
            if frame is not None:
                with frame_lock:
                    shared_frame["frame"] = frame
            if stop_event.wait(interval):
                break

    capture_thread = threading.Thread(target=capture_worker, daemon=True)
    capture_thread.start()

