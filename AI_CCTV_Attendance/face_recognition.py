import base64
import binascii
import os
import shutil
import threading
from pathlib import Path

import cv2
import numpy as np


class FaceRecognizer:
    """Local Haar-face detection and LBPH matching for explicitly enrolled students."""

    def __init__(self, students_dir):
        self.students_dir = Path(students_dir)
        self.students_dir.mkdir(parents=True, exist_ok=True)
        self.confidence_limit = float(os.environ.get("FACE_CONFIDENCE_LIMIT", "70"))
        self.detector = cv2.CascadeClassifier(
            str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        )
        self._lock = threading.RLock()
        self._model = None
        self.train()

    @staticmethod
    def _decode_image(payload):
        if not isinstance(payload, str) or "," not in payload:
            raise ValueError("A captured image was missing or invalid.")
        try:
            encoded = payload.split(",", 1)[1]
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ValueError("A captured image could not be decoded.") from error
        image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("A captured image could not be read.")
        return image

    def _crop_face(self, image):
        faces = self.detector.detectMultiScale(
            image, scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)
        )
        if len(faces) == 0:
            return None
        x, y, width, height = max(faces, key=lambda face: face[2] * face[3])
        crop = image[y : y + height, x : x + width]
        return cv2.resize(crop, (200, 200), interpolation=cv2.INTER_AREA)

    def register(self, student_id, image_payloads):
        crops = []
        for payload in image_payloads:
            crop = self._crop_face(self._decode_image(payload))
            if crop is not None:
                crops.append(crop)
        if len(crops) < 3:
            raise ValueError("At least three clear captures with a visible face are required.")

        student_dir = self.students_dir / str(student_id)
        student_dir.mkdir(parents=True, exist_ok=False)
        try:
            for index, crop in enumerate(crops, start=1):
                if not cv2.imwrite(str(student_dir / f"{index:02d}.png"), crop):
                    raise RuntimeError("Could not save the enrollment images.")
            self.train()
        except Exception:
            shutil.rmtree(student_dir, ignore_errors=True)
            self.train()
            raise

    def remove_student(self, student_id):
        shutil.rmtree(self.students_dir / str(student_id), ignore_errors=True)
        self.train()

    def train(self):
        with self._lock:
            images = []
            labels = []
            for student_dir in sorted(self.students_dir.iterdir()):
                if not student_dir.is_dir() or not student_dir.name.isdigit():
                    continue
                for image_path in sorted(student_dir.glob("*.png")):
                    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
                    if image is not None:
                        images.append(cv2.resize(image, (200, 200)))
                        labels.append(int(student_dir.name))
            if not images:
                self._model = None
                return
            if not hasattr(cv2, "face"):
                raise RuntimeError("Install opencv-contrib-python to enable face matching.")
            model = cv2.face.LBPHFaceRecognizer_create()
            model.train(images, np.asarray(labels, dtype=np.int32))
            self._model = model

    def identify(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(70, 70)
        )
        results = []
        with self._lock:
            model = self._model
            for x, y, width, height in faces:
                student_id = None
                confidence = None
                if model is not None:
                    crop = cv2.resize(gray[y : y + height, x : x + width], (200, 200))
                    label, confidence = model.predict(crop)
                    if confidence <= self.confidence_limit:
                        student_id = int(label)
                results.append(
                    {
                        "box": (int(x), int(y), int(width), int(height)),
                        "student_id": student_id,
                        "confidence": confidence,
                    }
                )
        return results