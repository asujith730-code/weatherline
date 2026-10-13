import csv
import io
import os
import sqlite3
import time
from datetime import date
from pathlib import Path

import cv2
from flask import Flask, Response, jsonify, render_template, request, url_for

import database
from attendance import AttendanceService
from camera import Camera
from face_recognition import FaceRecognizer


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-cctv-attendance")
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

database.init_db()
recognizer = FaceRecognizer(BASE_DIR / "students")
attendance_service = AttendanceService(recognizer)
camera = Camera()


@app.get("/")
def dashboard():
    return render_template(
        "dashboard.html",
        student_count=database.student_count(),
        present_count=database.attendance_count_for_date(),
        students=database.get_students(),
        today=date.today().isoformat(),
        weekday=date.today().strftime("%A").upper(),
    )


@app.get("/register")
def register_page():
    return render_template("register.html")


@app.post("/register")
def register_student():
    name = request.form.get("name", "").strip()
    student_code = request.form.get("student_code", "").strip()
    image_payloads = request.form.getlist("images")
    if not name or len(name) > 80 or not student_code or len(student_code) > 32:
        return jsonify(error="Enter a name (up to 80 characters) and student ID (up to 32)."), 400
    if len(image_payloads) < 3 or len(image_payloads) > 8:
        return jsonify(error="Capture between three and eight face images."), 400
    student_id = None
    try:
        student_id = database.add_student(name, student_code)
        recognizer.register(student_id, image_payloads)
    except sqlite3.IntegrityError:
        return jsonify(error="That student ID is already registered."), 409
    except ValueError as error:
        if student_id is not None:
            database.delete_student(student_id)
        return jsonify(error=str(error)), 400
    except Exception:
        if student_id is not None:
            database.delete_student(student_id)
        app.logger.exception("Student enrollment failed")
        return jsonify(error="Enrollment could not be completed. Check the server log."), 500
    return jsonify(ok=True, redirect=url_for("dashboard"))


@app.get("/reports")
def reports():
    start_date = request.args.get("start", "").strip() or None
    end_date = request.args.get("end", "").strip() or None
    records = database.get_attendance(start_date, end_date)
    return render_template(
        "reports.html", records=records, start_date=start_date or "", end_date=end_date or ""
    )


@app.get("/api/status")
def status():
    return jsonify(students=database.student_count(), present=database.attendance_count_for_date())


@app.get("/attendance.csv")
def export_attendance():
    start_date = request.args.get("start", "").strip() or None
    end_date = request.args.get("end", "").strip() or None
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(("Date", "Time", "Student", "Student ID"))
    for record in database.get_attendance(start_date, end_date, limit=10000):
        writer.writerow(
            (record["attendance_date"], record["attended_at"][11:19], record["name"], record["student_code"])
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance.csv"},
    )


def _placeholder_frame():
    frame = cv2.UMat(540, 960, cv2.CV_8UC3).get()
    frame[:] = (35, 42, 38)
    cv2.putText(frame, "CAMERA OFFLINE", (54, 265), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (225, 235, 226), 2)
    cv2.putText(frame, "Check the camera connection and index", (54, 305), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 179, 166), 1)
    return frame


def video_frames():
    while True:
        frame = camera.read()
        if frame is None:
            frame = _placeholder_frame()
            time.sleep(0.5)
        else:
            for detection in attendance_service.process_frame(frame):
                x, y, width, height = detection["box"]
                known = detection["student_id"] is not None
                color = (72, 190, 137) if known else (84, 118, 232)
                label = "Recognized" if known else "Not enrolled"
                cv2.rectangle(frame, (x, y), (x + width, y + height), color, 2)
                cv2.putText(frame, label, (x, max(y - 10, 22)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        encoded, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if encoded:
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"


@app.get("/video_feed")
def video_feed():
    return Response(video_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False, threaded=True)