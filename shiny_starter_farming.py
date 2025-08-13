import cv2
import numpy as np
import os
import time
import pyautogui
import win32gui

# Rectangle coordinates for starter sprite area
RECT_X1, RECT_Y1 = 400, 200
RECT_X2, RECT_Y2 = 100, 400

NORMAL_FOLDER = os.path.join("data", "pokemon_normal")
SHINY_FOLDER = os.path.join("data", "pokemon_shiny")

def load_templates(folder):
    templates = []
    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        img = cv2.imread(path)
        if img is not None:
            templates.append(img)
    return templates

normal_templates = load_templates(NORMAL_FOLDER)
shiny_templates = load_templates(SHINY_FOLDER)

def activate_mgba():
    """Brings mGBA window to foreground."""
    hwnd = win32gui.FindWindow(None, "mGBA")
    if hwnd:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)

def press_key(key, duration=0.1):
    pyautogui.keyDown(key)
    time.sleep(duration)
    pyautogui.keyUp(key)

def run_sequence():
    """The movement/dialogue sequence."""
    press_key("up", 0.8)   # move forward
    press_key("z", 0.1)    # skip dialogue (Z is A in mGBA default)
    press_key("left", 0.5)
    press_key("left", 0.5)
    press_key("left", 0.5)
    press_key("up", 0.5)
    press_key("z", 0.1)
    press_key("z", 0.1)
    press_key("z", 0.1)

def check_shiny(frame: np.ndarray) -> bool:
    """Returns True if shiny detected."""
    frame = np.ascontiguousarray(frame)
    sprite_area = frame[RECT_Y1:RECT_Y2, RECT_X1:RECT_X2]

    for template in shiny_templates:
        template_resized = cv2.resize(template, (sprite_area.shape[1], sprite_area.shape[0]))
        res = cv2.matchTemplate(sprite_area, template_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > 0.9:
            return True
    return False

def reset_game():
    """Sends reset hotkey to mGBA (default Ctrl+R)."""
    pyautogui.hotkey("ctrl", "r")
    time.sleep(1)

def shinystartermethod(frame: np.ndarray):
    """Called every frame from window_capture."""
    # Draw debug rectangle
    cv2.rectangle(frame, (RECT_X1, RECT_Y1), (RECT_X2, RECT_Y2), (0, 0, 255), 2)

    # This runs only once per loop when we need to check
    if check_shiny(frame):
        print("[!!!] SHINY FOUND! [!!!]")
        pyautogui.alert("Shiny Pokémon found!")
        exit(0)  # stop bot
    else:
        print("No shiny. Resetting...")
        reset_game()
        time.sleep(1)
        run_sequence()
import cv2
import numpy as np
import os
import time
import pyautogui
import win32gui

# Rectangle coordinates for starter sprite area
RECT_X1, RECT_Y1 = 400, 200
RECT_X2, RECT_Y2 = 100, 400

NORMAL_FOLDER = os.path.join("data", "pokemon_normal")
SHINY_FOLDER = os.path.join("data", "pokemon_shiny")

def load_templates(folder):
    templates = []
    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        img = cv2.imread(path)
        if img is not None:
            templates.append(img)
    return templates

normal_templates = load_templates(NORMAL_FOLDER)
shiny_templates = load_templates(SHINY_FOLDER)

def activate_mgba():
    """Brings mGBA window to foreground."""
    hwnd = win32gui.FindWindow(None, "mGBA")
    if hwnd:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)

def press_key(key, duration=0.1):
    pyautogui.keyDown(key)
    time.sleep(duration)
    pyautogui.keyUp(key)

def run_sequence():
    """The movement/dialogue sequence."""
    press_key("up", 0.8)   # move forward
    press_key("z", 0.1)    # skip dialogue (Z is A in mGBA default)
    press_key("left", 0.5)
    press_key("left", 0.5)
    press_key("left", 0.5)
    press_key("up", 0.5)
    press_key("z", 0.1)
    press_key("z", 0.1)
    press_key("z", 0.1)

def check_shiny(frame: np.ndarray) -> bool:
    """Returns True if shiny detected."""
    frame = np.ascontiguousarray(frame)
    sprite_area = frame[RECT_Y1:RECT_Y2, RECT_X1:RECT_X2]

    for template in shiny_templates:
        template_resized = cv2.resize(template, (sprite_area.shape[1], sprite_area.shape[0]))
        res = cv2.matchTemplate(sprite_area, template_resized, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        if max_val > 0.9:
            return True
    return False

def reset_game():
    """Sends reset hotkey to mGBA (default Ctrl+R)."""
    pyautogui.hotkey("ctrl", "r")
    time.sleep(1)

def shinystartermethod(frame: np.ndarray):
    """Called every frame from window_capture."""
    # Draw debug rectangle
    cv2.rectangle(frame, (RECT_X1, RECT_Y1), (RECT_X2, RECT_Y2), (0, 0, 255), 2)

    # This runs only once per loop when we need to check
    if check_shiny(frame):
        print("[!!!] SHINY FOUND! [!!!]")
        pyautogui.alert("Shiny Pokémon found!")
        exit(0)  # stop bot
    else:
        print("No shiny. Resetting...")
        reset_game()
        time.sleep(1)
        run_sequence()
