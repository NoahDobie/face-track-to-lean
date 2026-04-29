import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

from components.startstop_toggle_frame import create_startstop_toggle_frame
from components.camera_select_frame import create_camera_select_frame
from components.camera_buttons_frame import create_camera_buttons_frame
from components.canvas_frame import create_canvas_frame
from components.direction_label import create_direction_label
from components.lines_frame import create_lines_frame
from components.keybinds_frame import create_keybinds_frame

class GUI:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller

        # Set the window title
        root.title("Face Track to Lean by Noah Dobie")
        
        # Set the window icon
        icon_path = 'src/icons/FTL-Icon.png'
        icon = tk.PhotoImage(file=icon_path)
        root.iconphoto(False, icon)

        # Apply dark theme
        self.style = ttkb.Style("darkly")

        self.setup_ui()

    def setup_ui(self):
        self.root.minsize(400, 300)  # Set minimum window size
        self.root.resizable(False, False)  # Allow window to be resized

        self.startstop_button_frame, self.toggle_button = create_startstop_toggle_frame(self.root, self.controller)
        self.camera_select_frame, self.camera_var, self.camera_dropdown = create_camera_select_frame(self.root, self.controller)
        self.camera_buttons_frame = create_camera_buttons_frame(self.root, self.controller)
        self.canvas, self.loading_label = create_canvas_frame(self.root, self.controller)
        self.direction_label = create_direction_label(self.root)
        self.lines_frame, self.left_line_slider, self.right_line_slider = create_lines_frame(self.root, self.controller)
        self.keybinds_frame, self.left_key_var, self.right_key_var, self.start_stop_key_var = create_keybinds_frame(self.root, self.controller)

        # Load configuration after UI setup
        self.load_config()

    def load_config(self):
        self.left_line_slider.set(self.controller.config["left_line_position"])
        self.right_line_slider.set(self.controller.config["right_line_position"])
        self.left_key_var.set(self.controller.config["left_key"])
        self.right_key_var.set(self.controller.config["right_key"])
        self.start_stop_key_var.set(self.controller.config["start_stop_key"])

    def update_ui(self):
        self.toggle_button.config(text="Stop" if self.controller.tracking_enabled else "Start", bootstyle="danger" if self.controller.tracking_enabled else "success")
        self.direction_label.config(text=f"Direction: {self.controller.current_direction}")
        self.root.update_idletasks()

    def show_message(self, message="Loading..."):
        self.canvas.delete("all")
        cx = int(self.canvas.cget("width")) // 2
        cy = int(self.canvas.cget("height")) // 2
        self.loading_label = self.canvas.create_text(cx, cy, text=message, font=("Helvetica", 14), fill="white")

    def hide_message(self):
        self.canvas.delete(self.loading_label)

    def update_canvas(self, image):
        imgtk = ImageTk.PhotoImage(image=image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.canvas.imgtk = imgtk