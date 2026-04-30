import customtkinter as ctk
import threading
import config
import os
import sys
from debug_preview import find_window_by_title
from unique_battle import Unique_encounters
from random_shiny import random_shiny_hunt
from PIL import Image

selected_mode = None

# === Paths ===
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(__file__)

IMG_DIR = os.path.join(BASE_DIR, "data", "bin")

# Store references to images so they don't get garbage-collected
button_images = {}

def start():
    if config.running_mode:
        config.log_print("[!] Mode already running. Stop first before starting another.")
        return

    config.stop_program = False
    config.running_mode = selected_mode

    hwnd = find_window_by_title("mGBA")
    if hwnd is None:
        config.log_print("[!] Could not find mGBA window.")
        config.stop_program = True
        config.running_mode = None
        return

    if selected_mode is None:
        config.log_print("[!] No mode selected.")
        config.running_mode = None
        return

    shiny_event = threading.Event()
    not_shiny_event = threading.Event()

    if selected_mode == "Random Shiny":
        threading.Thread(
            target=random_shiny_hunt,
            args=(hwnd, shiny_event, not_shiny_event),
            daemon=True
        ).start()
    elif selected_mode == "Unique Encounters":
        threading.Thread(
            target=Unique_encounters,
            args=(hwnd, shiny_event, not_shiny_event),
            daemon=True
        ).start()
    elif selected_mode == "Fishing Rod":
        config.log_print("[!] Fishing Rod mode not implemented yet")
        config.running_mode = None

def stop():
    config.stop_program = True
    config.log_print("[*] Stop requested")

def select_mode(mode_name):
    global selected_mode
    selected_mode = mode_name
    for btn in mode_buttons.values():
        btn.configure(fg_color="gray")
    mode_buttons[mode_name].configure(fg_color="green")

# === GUI SETUP ===
app = ctk.CTk()
app.title("Shiny Hunter Bot")
app.geometry("500x500")

# Mode buttons
mode_frame = ctk.CTkFrame(app)
mode_frame.pack(pady=20)

mode_buttons = {}
modes = ["Random Shiny", "Unique Encounters", "Fishing Rod"]

for i, mode in enumerate(modes):
    # Build image path (replace spaces in filenames with underscores if needed)
    img_path = os.path.join(IMG_DIR, f"{mode}.png")
    if os.path.exists(img_path):
        button_images[mode] = ctk.CTkImage(Image.open(img_path), size=(120, 120))
        btn = ctk.CTkButton(
            mode_frame,
            text=mode,
            image=button_images[mode],
            compound="top",  # text over image
            width=120,
            height=120,
            fg_color="transparent", 
            hover_color="gray25", 
            command=lambda m=mode: select_mode(m)
        )
    else:
        config.log_print(f"[WARN] Missing icon for {mode}, using text button instead")
        btn = ctk.CTkButton(
            mode_frame,
            text=mode,
            width=120,
            height=120,
            command=lambda m=mode: select_mode(m)
        )

    btn.grid(row=0, column=i, padx=10)
    mode_buttons[mode] = btn

# Loop counter label
label_counter = ctk.CTkLabel(app, text="Loops: 0")
label_counter.pack(pady=10)

# Start/Stop buttons
control_frame = ctk.CTkFrame(app)
control_frame.pack(side="bottom", pady=20)

start_button = ctk.CTkButton(control_frame, text="Start", width=100, command=start)
start_button.pack(side="left", padx=20)

stop_button = ctk.CTkButton(control_frame, text="Stop", width=100, command=stop)
stop_button.pack(side="left", padx=20)

# Log textbox
log_textbox = ctk.CTkTextbox(app, width=480, height=200)
log_textbox.pack(pady=10)
log_textbox.configure(state="disabled")

# Assign to config
config.text_widget = log_textbox

def loop_counter():
    label_counter.configure(text=f"Loops: {config.thread_counter}")
    app.after(500, loop_counter)  # check every 0.5s
loop_counter()

def run():
    app.mainloop()
