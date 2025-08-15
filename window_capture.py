import time
import threading
import cv2
import numpy as np
import mss
import win32gui

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

def run(hwnd, callback=None):
    """
    Main loop for window capture and preview.
    - callback(frame) is called every frame if provided.
    """
    stop_event = threading.Event()
    interval = FRAME_INTERVAL_MS / 1000
    frame_lock = threading.Lock()
    shared_frame = {"frame": None}

    # Worker thread for capturing frames
    def capture_worker():
        while not stop_event.is_set():
            frame = capture_window(hwnd)
            if frame is None:
                break
            with frame_lock:
                shared_frame["frame"] = frame
            if stop_event.wait(interval):
                break

    capture_thread = threading.Thread(target=capture_worker, daemon=True)
    capture_thread.start()

    # try:
    #     while not stop_event.is_set():
    #         start_time = time.time()
    #         with frame_lock:
    #             frame = shared_frame["frame"]
    #         if frame is None:
    #             time.sleep(0.01)
    #             continue

    #         frame_copy = frame.copy()

    #         # --- DEBUG: starter detection zone (red) ---
    #         x_s, y_s, w_s, h_s = 60, frame_copy.shape[0] - 320, 300, 175
    #         cv2.rectangle(frame_copy, (x_s, y_s), (x_s + w_s, y_s + h_s), (0, 0, 255), 2)

    #         # --- DEBUG: enemy detection zone (blue) ---
    #         x_e, y_e, w_e, h_e = 400, frame_copy.shape[0] - 450, 300, 180
    #         cv2.rectangle(frame_copy, (x_e, y_e), (x_e + w_e, y_e + h_e), (255, 0, 0), 2)

    #         cv2.imshow("Preview", frame_copy)
    #         if cv2.waitKey(1) & 0xFF == ord("q"):
    #             stop_event.set()
    #             break

    #         # Maintain consistent interval
    #         elapsed = time.time() - start_time
    #         time.sleep(max(0, interval - elapsed))

    # finally:
    #     stop_event.set()
    #     capture_thread.join()
    #     cv2.destroyAllWindows()
    #     cv2.waitKey(1)
    #     print("[+] Capture loop exited cleanly")
