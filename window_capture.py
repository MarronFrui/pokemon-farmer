# window_capture.py
import time
import cv2
import numpy as np
from typing import Optional, Tuple, Callable
import mss
import win32gui

WINDOW_TITLE_SUBSTR = "mGBA"
FRAME_INTERVAL_MS = 50
SHOW_PREVIEW = True
SCALE_PREVIEW = 0.5

def find_window_by_title(substr: str) -> Optional[int]:
    target_hwnd = None
    substr_low = substr.lower()
    def enum_handler(hwnd, _):
        nonlocal target_hwnd
        if target_hwnd is not None or not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if substr_low in title.lower():
            target_hwnd = hwnd
    win32gui.EnumWindows(enum_handler, None)
    return target_hwnd

def get_client_rect(hwnd: int) -> Tuple[int, int, int, int]:
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    client_origin = win32gui.ClientToScreen(hwnd, (0, 0))
    left_s, top_s = client_origin
    width = right - left
    height = bottom - top
    return left_s, top_s, left_s + width, top_s + height

def capture_window(hwnd: int) -> Optional[np.ndarray]:
    """Capture a BGR frame of the window."""
    try:
        # Update coordinates every frame
        left, top, right, bottom = get_client_rect(hwnd)
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return None

        with mss.mss() as sct:
            monitor = {"top": top, "left": left, "width": width, "height": height}
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)[:, :, :3]  # BGR

            if SHOW_PREVIEW:
                scaled = cv2.resize(
                    img,
                    (int(width * SCALE_PREVIEW), int(height * SCALE_PREVIEW)),
                    interpolation=cv2.INTER_NEAREST,
                )
                cv2.imshow("mGBA Capture (debug)", scaled)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    return None  # signal to stop capture loop
            return img
    except Exception:
        return None

def run(hwnd: int, callback: Callable[[np.ndarray], None]):
    """Main capture loop feeding frames to callback."""
    interval = FRAME_INTERVAL_MS / 1000.0
    prev = time.perf_counter()
    try:
        while True:
            now = time.perf_counter()
            if now - prev < interval:
                time.sleep(max(0.0, interval - (now - prev)))
            prev = time.perf_counter()

            frame = capture_window(hwnd)
            if frame is None:
                # If preview returned None (user pressed 'q'), stop the loop
                break

            # Feed the captured frame to the callback
            callback(frame)

    finally:
        cv2.destroyAllWindows()
        print("[+] Clean exit.")

