import tkinter as tk
import threading
import time
from pynput.keyboard import Controller as KeyboardController
from face_tracker import FaceTracker
from configmanager import ConfigManager
from gui import GUI
import cv2
import logging
from PIL import Image
from pygrabber.dshow_graph import FilterGraph

logging.basicConfig(level=logging.INFO)

# Target UI refresh interval in milliseconds (~30 fps)
_MAIN_LOOP_MS = 33

class Controller:
    def __init__(self, root, config_path):
        self.root = root
        self.tracking_enabled = False
        self.preview_enabled = True
        self.running = True
        self.current_direction = "Center"
        self.keyboard = KeyboardController()
        self.flip = False
        self.selected_camera_index = 0  # Initialize selected camera index

        # Thread-safe storage for the latest processed frame and results
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._latest_results = None

        self.config_manager = ConfigManager(config_file=config_path)
        self.config = self.config_manager.get_config()

        # Initialize GUI after config is loaded
        self.view = GUI(root, self)

        # Initialize camera in a separate thread
        self.init_thread = threading.Thread(target=self.initialize_camera)
        self.init_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.after(_MAIN_LOOP_MS, self.main_loop)

        # Bind the start/stop key
        self.root.bind(f'<KeyPress-{self.view.start_stop_key_var.get()}>', self.toggle_tracking)

    def list_cameras(self):
        graph = FilterGraph()
        devices = graph.get_input_devices()
        return {name: index for index, name in enumerate(devices)}

    def initialize_camera(self):
        try:
            self.face_tracker = FaceTracker(camera_index=self.selected_camera_index, frame_width=self.config["camera_preview_width"], frame_height=self.config["camera_preview_height"])
            self.capture_thread = threading.Thread(target=self.capture_and_process_frames)
            self.capture_thread.daemon = True
            self.capture_thread.start()

            # Remove loading screen
            self.view.hide_message()
        except Exception as e:
            camera_name = list(self.list_cameras().keys())[self.selected_camera_index]
            logging.error(f"Error: Could not open webcam '{camera_name}' with index: {self.selected_camera_index}.")
            self.view.show_message(f"Error: Could not open webcam: '{camera_name}'.")

    def toggle_tracking(self, event=None):
        self.tracking_enabled = not self.tracking_enabled
        self.view.update_ui()
        if not self.tracking_enabled:
            # Ensure keys are released when tracking stops
            self.keyboard.release(self.view.left_key_var.get())
            self.keyboard.release(self.view.right_key_var.get())
            self.current_direction = "Center"

    def toggle_preview(self):
        self.preview_enabled = not self.preview_enabled

    def flip_camera(self):
        self.flip = not self.flip
        if self.flip:
            logging.info("Camera flipped horizontally.")
        else:
            logging.info("Camera flipped back to initial.")

    def on_closing(self):
        self.running = False
        self.root.quit()
        self.root.destroy()

    def capture_and_process_frames(self):
        """Background thread: capture frames from the camera, run face detection,
        and store the latest results for the main loop to consume."""
        while self.running:
            ret, frame = self.face_tracker.capture_frame()
            if not ret:
                time.sleep(0.005)
                continue
            if self.flip:
                frame = cv2.flip(frame, 1)
            # Keep face_tracker.frame in sync so process_frame() uses the right data
            self.face_tracker.frame = frame
            results = self.face_tracker.process_frame()
            with self._frame_lock:
                self._latest_frame = frame
                self._latest_results = results

    def main_loop(self):
        # Grab the latest frame and results captured by the background thread
        with self._frame_lock:
            frame = self._latest_frame
            results = self._latest_results

        if frame is None:
            self.root.after(_MAIN_LOOP_MS, self.main_loop)
            return

        # Get the positions of the defining lines from the sliders
        left_line_pos = int(round(float(self.view.left_line_slider.get())))
        right_line_pos = int(round(float(self.view.right_line_slider.get())))

        # Ensure minimum distance between lines
        if right_line_pos - left_line_pos < 50:
            right_line_pos = left_line_pos + 50
            self.view.right_line_slider.set(right_line_pos)

        # Initialize bounding box variables with default values
        x_min, x_max, y_min, y_max = 0, 0, 0, 0

        if self.tracking_enabled and results and results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                # Get the x-coordinates of the leftmost and rightmost landmarks
                x_coords = [landmark.x * self.face_tracker.frame_width for landmark in face_landmarks.landmark]
                face_center_x = int(sum(x_coords) / len(x_coords))
                self.face_tracker.smoothed_face_center_x = int(self.face_tracker.smoothing_factor * self.face_tracker.smoothed_face_center_x + (1 - self.face_tracker.smoothing_factor) * face_center_x)

                # Update bounding box variables
                x_min = int(min(x_coords))
                x_max = int(max(x_coords))
                y_coords = [landmark.y * self.face_tracker.frame_height for landmark in face_landmarks.landmark]
                y_min = int(min(y_coords))
                y_max = int(max(y_coords))

                # Calculate the midpoint of the top edge of the bounding box
                text_x = (x_min + x_max) // 2

                if self.face_tracker.smoothed_face_center_x < left_line_pos:
                    if self.current_direction != "Left":
                        self.keyboard.press(self.view.left_key_var.get())
                        self.keyboard.release(self.view.right_key_var.get())
                        self.current_direction = "Left"
                    self.view.direction_label.config(text="Direction: Left")
                    if self.preview_enabled:
                        cv2.putText(frame, 'Left', (text_x, y_min), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
                elif self.face_tracker.smoothed_face_center_x > right_line_pos:
                    if self.current_direction != "Right":
                        self.keyboard.press(self.view.right_key_var.get())
                        self.keyboard.release(self.view.left_key_var.get())
                        self.current_direction = "Right"
                    self.view.direction_label.config(text="Direction: Right")
                    if self.preview_enabled:
                        cv2.putText(frame, 'Right', (text_x, y_min), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
                else:
                    if self.current_direction != "Center":
                        self.keyboard.release(self.view.left_key_var.get())
                        self.keyboard.release(self.view.right_key_var.get())
                        self.current_direction = "Center"
                    self.view.direction_label.config(text="Direction: Center")
                    if self.preview_enabled:
                        cv2.putText(frame, 'Center', (text_x, y_min), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)

        else:
            if self.current_direction != "Center":
                self.keyboard.release(self.view.left_key_var.get())
                self.keyboard.release(self.view.right_key_var.get())
                self.current_direction = "Center"
            self.view.direction_label.config(text="Direction: Center")

        if self.preview_enabled:
            # Resize the frame to fit the canvas
            canvas_width = self.view.canvas.winfo_width()
            canvas_height = self.view.canvas.winfo_height()
            display_frame = cv2.resize(frame, (canvas_width, canvas_height))

            # Draw the lines on the resized frame
            cv2.line(display_frame, (left_line_pos, 0), (left_line_pos, canvas_height), (0, 255, 0), 2)
            cv2.line(display_frame, (right_line_pos, 0), (right_line_pos, canvas_height), (0, 255, 0), 2)

            # Draw the bounding box on the resized frame
            cv2.rectangle(display_frame, (x_min, y_min), (x_max, y_max), (0, 0, 255), 2)

            # Convert the frame to an image and update the canvas
            img = Image.fromarray(cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB))
            self.view.update_canvas(img)

        self.root.after(_MAIN_LOOP_MS, self.main_loop)

    def set_left_keybind(self):
        key = self.view.left_key_var.get()
        if len(key) == 1 and key.isalpha():
            self.view.left_key_var.set(key.lower())
        else:
            self.view.left_key_var.set('q')  # Reset to default if invalid
        self.config_manager.update_config("left.key", self.view.left_key_var.get())

    def set_right_keybind(self):
        key = self.view.right_key_var.get()
        if len(key) == 1 and key.isalpha():
            self.view.right_key_var.set(key.lower())
        else:
            self.view.right_key_var.set('e')  # Reset to default if invalid
        self.config_manager.update_config("right.key", self.view.right_key_var.get())

    def set_start_stop_keybind(self):
        key = self.view.start_stop_key_var.get()
        if len(key) == 1 and key.isalpha():
            self.view.start_stop_key_var.set(key.lower())
        else:
            self.view.start_stop_key_var.set('space')  # Reset to default if invalid
        # Rebind the key
        self.root.bind(f'<KeyPress-{self.view.start_stop_key_var.get()}>', self.toggle_tracking)
        self.config_manager.update_config("start.stop.key", self.view.start_stop_key_var.get())

    def update_left_line_position(self, value):
        # Convert the slider value to an integer and update the configuration
        int_value = int(round(float(value)))
        self.config_manager.update_config("left.line.position", int_value)

    def update_right_line_position(self, value):
        # Convert the slider value to an integer and update the configuration
        int_value = int(round(float(value)))
        self.config_manager.update_config("right.line.position", int_value)