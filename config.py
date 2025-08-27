import threading

# === BOT STATE ===
in_battle = False
battle_start_time = None
detection_complete = False
stop_program = False
running_mode = None
thread_counter = 0

# === LOGGING ===
text_widget = None  # placeholder for GUI text box
log_lock = threading.Lock()

def log_print(msg):
    """Thread-safe logging to GUI textbox if assigned, otherwise fallback to console."""
    with log_lock:
        if text_widget:
            # insert on main thread
            text_widget.after(0, lambda: _append_to_text_widget(msg))
        else:
            print(msg)

def _append_to_text_widget(msg):
    """Helper: insert text and scroll to end"""
    text_widget.configure(state="normal")
    text_widget.insert("end", msg + "\n")
    text_widget.see("end")
    text_widget.configure(state="disabled")
