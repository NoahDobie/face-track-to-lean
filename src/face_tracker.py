import cv2
import mediapipe as mp
import logging

logging.basicConfig(level=logging.INFO)

class FaceTracker:
    def __init__(self, camera_index, frame_width=1920, frame_height=1080, smoothing_factor=0.5):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            logging.error(f"Error: Could not open webcam with index {camera_index}.")
            raise RuntimeError(f"Could not open webcam with index {camera_index}.")
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.frame_center_x = self.frame_width // 2
        self.smoothing_factor = smoothing_factor
        self.smoothed_face_center_x = self.frame_center_x
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.frame = None
        self.ret = False

    def capture_frame(self):
        """Read one frame from the camera.

        Returns:
            (ret, frame): ret is True when a frame was successfully read;
                          frame is the raw BGR numpy array (or None on failure).
        """
        self.ret, self.frame = self.cap.read()
        return self.ret, self.frame

    def process_frame(self):
        small_frame = cv2.resize(self.frame, (self.frame_width, self.frame_height))
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        return results

    def release(self):
        self.cap.release()