import database
import threading
from datetime import datetime


class AttendanceService:
    def __init__(self, recognizer):
        self.recognizer = recognizer
        self._lock = threading.Lock()
        self._attendance_date = datetime.now().astimezone().date().isoformat()
        self._checked_in = database.get_student_ids_for_date(self._attendance_date)

    def process_frame(self, frame):
        detections = self.recognizer.identify(frame)
        today = datetime.now().astimezone().date().isoformat()
        with self._lock:
            if today != self._attendance_date:
                self._attendance_date = today
                self._checked_in = database.get_student_ids_for_date(today)
            for detection in detections:
                student_id = detection["student_id"]
                detection["marked_now"] = False
                if student_id is not None and student_id not in self._checked_in:
                    detection["marked_now"] = database.mark_attendance(student_id)
                    self._checked_in.add(student_id)
        return detections