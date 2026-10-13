import os
import threading

import cv2


class Camera:
    def __init__(self, camera_index=None):
        configured_index = camera_index if camera_index is not None else os.environ.get("CAMERA_INDEX", "0")
        self.camera_index = int(configured_index)
        self._capture = None
        self._lock = threading.Lock()

    def read(self):
        with self._lock:
            if self._capture is None or not self._capture.isOpened():
                self._capture = cv2.VideoCapture(self.camera_index)
                self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
                self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
            success, frame = self._capture.read()
            if not success:
                self._capture.release()
                self._capture = None
                return None
            return frame

    def release(self):
        with self._lock:
            if self._capture is not None:
                self._capture.release()
                self._capture = None