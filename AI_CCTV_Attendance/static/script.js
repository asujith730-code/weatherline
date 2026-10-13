const page = document.body.dataset.page;

if (page === "dashboard") {
  const refreshStatus = async () => {
    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      if (!response.ok) return;
      const data = await response.json();
      document.querySelector("#present-count").textContent = data.present;
      document.querySelector("#student-count").textContent = data.students;
    } catch {
      // The dashboard remains usable while the local server is reconnecting.
    }
  };
  window.setInterval(refreshStatus, 10000);
}

if (page === "register") {
  const form = document.querySelector("#enrollment-form");
  const video = document.querySelector("#capture-video");
  const canvas = document.querySelector("#capture-canvas");
  const startButton = document.querySelector("#camera-start");
  const captureButton = document.querySelector("#capture-button");
  const submitButton = document.querySelector("#submit-enrollment");
  const placeholder = document.querySelector("#capture-placeholder");
  const counter = document.querySelector("#capture-counter");
  const message = document.querySelector("#capture-message");
  const error = document.querySelector("#form-error");
  const captures = [];
  let stream;

  startButton.addEventListener("click", async () => {
    error.textContent = "";
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
      });
      video.srcObject = stream;
      placeholder.hidden = true;
      captureButton.disabled = false;
      startButton.textContent = "Camera ready";
      message.textContent = "Center the face in frame, then capture up to five angles.";
    } catch {
      error.textContent = "Camera access was unavailable. Allow camera permission and try again.";
    }
  });

  captureButton.addEventListener("click", () => {
    if (!video.videoWidth || captures.length >= 5) return;
    const context = canvas.getContext("2d");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    captures.push(canvas.toDataURL("image/jpeg", 0.82));
    counter.textContent = `${captures.length} / 5`;
    message.textContent = captures.length >= 3
      ? "Enough captures. Add up to two more, or save the student."
      : `Captured ${captures.length}. At least three are needed.`;
    submitButton.disabled = captures.length < 3;
    if (captures.length === 5) captureButton.disabled = true;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.textContent = "";
    if (!form.reportValidity()) return;
    if (captures.length < 3) {
      error.textContent = "Capture at least three face images before saving.";
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Saving profile…";
    const body = new FormData(form);
    captures.forEach((image) => body.append("images", image));
    try {
      const response = await fetch("/register", { method: "POST", body });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Enrollment failed.");
      window.location.assign(result.redirect);
    } catch (reason) {
      error.textContent = reason.message || "Enrollment failed. Try again.";
      submitButton.disabled = false;
      submitButton.innerHTML = 'Save student <span aria-hidden="true">→</span>';
    }
  });

  window.addEventListener("pagehide", () => stream?.getTracks().forEach((track) => track.stop()));
}