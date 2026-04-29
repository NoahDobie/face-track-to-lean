import tkinter as tk
import threading
from pynput.keyboard import Controller as KeyboardController  # type: ignore[import-untyped]
from face_tracker import FaceTracker
from configmanager import ConfigManager
from gui import GUI
import cv2
import logging
from PIL import Image
from pygrabber.dshow_graph import FilterGraph  # type: ignore[import-untyped]

logging.basicConfig(level=logging.INFO)

_MAIN_LOOP_MS = 33   # ~30 fps
_MIN_LINE_GAP = 50   # minimum pixels between left and right lines

class Controller:
    def __init__(self, root, config_path):
        self.root = root
        self.tracking_enabled = False
        self.preview_enabled = True
        self.running = True
        self.current_direction = "Center"
        self.keyboard = KeyboardController()
        self.flip = False
        self.selected_camera_index = 0
        self.face_tracker = None
        self._capture_running = False
        self._updating_lines = False
        self.view = None

        self.config_manager = ConfigManager(config_file=config_path)
        self.config = self.config_manager.get_config()

        self.view = GUI(root, self)

        self.init_thread = threading.Thread(target=self.initialize_camera, daemon=True)
        self.init_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(_MAIN_LOOP_MS, self.main_loop)

        self.root.bind(f'<KeyPress-{self.view.start_stop_key_var.get()}>', self.toggle_tracking)

    def list_cameras(self):
        graph = FilterGraph()
        devices = graph.get_input_devices()
        return {name: index for index, name in enumerate(devices)}

    def _stop_capture(self):
        """Stop the capture thread and release camera resources."""
        self._capture_running = False
        if hasattr(self, 'capture_thread') and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        if self.face_tracker is not None:
            self.face_tracker.release()

    def initialize_camera(self):
        """Open the selected camera and start the capture thread. Safe to call from any thread."""
        self._stop_capture()
        try:
            self.face_tracker = FaceTracker(
                camera_index=self.selected_camera_index,
                frame_width=self.config["camera_preview_width"],
                frame_height=self.config["camera_preview_height"],
            )
            self._capture_running = True
            self.capture_thread = threading.Thread(target=self.capture_frames, daemon=True)
            self.capture_thread.start()
            self.root.after(0, self.view.hide_message)
        except Exception as e:
            logging.error(f"Could not open webcam index {self.selected_camera_index}: {e}")
            self.root.after(0, self.view.show_message, f"Error: Could not open webcam (index {self.selected_camera_index}).")

    def switch_camera(self):
        """Show loading state then reinitialise the camera in a background thread."""
        self.view.show_message("Loading Camera...")
        threading.Thread(target=self.initialize_camera, daemon=True).start()

    def toggle_tracking(self, event=None):
        self.tracking_enabled = not self.tracking_enabled
        self.view.update_ui()
        if not self.tracking_enabled:
            self.keyboard.release(self.view.left_key_var.get())
            self.keyboard.release(self.view.right_key_var.get())
            self.current_direction = "Center"

    def toggle_preview(self):
        self.preview_enabled = not self.preview_enabled
        if self.preview_enabled:
            self.view.hide_message()
        else:
            self.view.show_message("Preview disabled")

    def flip_camera(self):
        self.flip = not self.flip
        logging.info("Camera flipped horizontally." if self.flip else "Camera flipped back to initial.")

    def on_closing(self):
        self._capture_running = False
        self.running = False
        self.root.quit()
        self.root.destroy()

    def capture_frames(self):
        while self.running and self._capture_running:
            ret, frame = self.face_tracker.cap.read()
            if ret and self.flip:
                frame = cv2.flip(frame, 1)
            self.face_tracker.ret = ret
            self.face_tracker.frame = frame  # single write, already flipped

    def main_loop(self):
        if self.face_tracker is None or not self.face_tracker.ret:
            self.root.after(_MAIN_LOOP_MS, self.main_loop)
            return

        results = self.face_tracker.process_frame()

        left_line_pos = int(round(float(self.view.left_line_slider.get())))
        right_line_pos = int(round(float(self.view.right_line_slider.get())))

        x_min, x_max, y_min, y_max = 0, 0, 0, 0

        if self.tracking_enabled and results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                x_coords = [landmark.x * self.face_tracker.frame_width for landmark in face_landmarks.landmark]
                face_center_x = int(sum(x_coords) / len(x_coords))
                self.face_tracker.smoothed_face_center_x = int(
                    self.face_tracker.smoothing_factor * self.face_tracker.smoothed_face_center_x
                    + (1 - self.face_tracker.smoothing_factor) * face_center_x
                )

                x_min = int(min(x_coords))
                x_max = int(max(x_coords))
                y_coords = [landmark.y * self.face_tracker.frame_height for landmark in face_landmarks.landmark]
                y_min = int(min(y_coords))
                y_max = int(max(y_coords))

                text_x = (x_min + x_max) // 2

                if self.face_tracker.smoothed_face_center_x < left_line_pos:
                    if self.current_direction != "Left":
                        self.keyboard.press(self.view.left_key_var.get())
                        self.keyboard.release(self.view.right_key_var.get())
                        self.current_direction = "Left"
                    self.view.direction_label.config(text="Direction: Left")
                    if self.preview_enabled:
                        cv2.putText(self.face_tracker.frame, 'Left', (text_x, y_min), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
                elif self.face_tracker.smoothed_face_center_x > right_line_pos:
                    if self.current_direction != "Right":
                        self.keyboard.press(self.view.right_key_var.get())
                        self.keyboard.release(self.view.left_key_var.get())
                        self.current_direction = "Right"
                    self.view.direction_label.config(text="Direction: Right")
                    if self.preview_enabled:
                        cv2.putText(self.face_tracker.frame, 'Right', (text_x, y_min), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                else:
                    if self.current_direction != "Center":
                        self.keyboard.release(self.view.left_key_var.get())
                        self.keyboard.release(self.view.right_key_var.get())
                        self.current_direction = "Center"
                    self.view.direction_label.config(text="Direction: Center")
                    if self.preview_enabled:
                        cv2.putText(self.face_tracker.frame, 'Center', (text_x, y_min), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
        else:
            if self.current_direction != "Center":
                self.keyboard.release(self.view.left_key_var.get())
                self.keyboard.release(self.view.right_key_var.get())
                self.current_direction = "Center"
            self.view.direction_label.config(text="Direction: Center")

        if self.preview_enabled:
            canvas_width = self.view.canvas.winfo_width()
            canvas_height = self.view.canvas.winfo_height()
            display_frame = cv2.resize(self.face_tracker.frame, (canvas_width, canvas_height))

            cv2.line(display_frame, (left_line_pos, 0), (left_line_pos, canvas_height), (0, 255, 0), 2)
            cv2.line(display_frame, (right_line_pos, 0), (right_line_pos, canvas_height), (0, 255, 0), 2)
            cv2.rectangle(display_frame, (x_min, y_min), (x_max, y_max), (0, 0, 255), 2)

            img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
            self.view.update_canvas(img)

        self.root.after(_MAIN_LOOP_MS, self.main_loop)

    def set_left_keybind(self):
        key = self.view.left_key_var.get()
        if len(key) == 1 and key.isalpha():
            self.view.left_key_var.set(key.lower())
        else:
            self.view.left_key_var.set('q')
        self.config_manager.update_config("left.key", self.view.left_key_var.get())

    def set_right_keybind(self):
        key = self.view.right_key_var.get()
        if len(key) == 1 and key.isalpha():
            self.view.right_key_var.set(key.lower())
        else:
            self.view.right_key_var.set('e')
        self.config_manager.update_config("right.key", self.view.right_key_var.get())

    def set_start_stop_keybind(self):
        key = self.view.start_stop_key_var.get()
        if len(key) == 1 and key.isalpha():
            self.view.start_stop_key_var.set(key.lower())
        else:
            self.view.start_stop_key_var.set('space')
        self.root.bind(f'<KeyPress-{self.view.start_stop_key_var.get()}>', self.toggle_tracking)
        self.config_manager.update_config("start.stop.key", self.view.start_stop_key_var.get())

    def update_left_line_position(self, value):
        if self._updating_lines or self.view is None:
            return
        self._updating_lines = True
        try:
            max_x = self.config["camera_preview_width"]
            left = int(round(float(value)))
            right = int(round(float(self.view.right_line_slider.get())))
            if right - left < _MIN_LINE_GAP:
                right = min(left + _MIN_LINE_GAP, max_x)
                left = right - _MIN_LINE_GAP
                self.view.left_line_slider.set(left)
                self.view.right_line_slider.set(right)
                self.config_manager.update_config("right.line.position", right)
            self.config_manager.update_config("left.line.position", left)
        finally:
            self._updating_lines = False

    def update_right_line_position(self, value):
        if self._updating_lines or self.view is None:
            return
        self._updating_lines = True
        try:
            right = int(round(float(value)))
            left = int(round(float(self.view.left_line_slider.get())))
            if right - left < _MIN_LINE_GAP:
                left = max(right - _MIN_LINE_GAP, 0)
                right = left + _MIN_LINE_GAP
                self.view.left_line_slider.set(left)
                self.view.right_line_slider.set(right)
                self.config_manager.update_config("left.line.position", left)
            self.config_manager.update_config("right.line.position", right)
        finally:
            self._updating_lines = False
