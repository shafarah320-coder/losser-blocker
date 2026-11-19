import os
import sys
import time
import threading
import tempfile
import ctypes
import tkinter as tk
from tkinter import messagebox

import cv2
import numpy as np
import mss
from nudenet import NudeDetector

# Screen Censor 2.0
# Targets: every detected face + exposed female breast labels only.
BREAST_LABELS = {"FEMALE_BREAST_EXPOSED"}
SCAN_INTERVAL = 1.0
NUDENET_THRESHOLD = 0.45
FACE_SCALE = 1.1
FACE_NEIGHBORS = 5

class ScreenCensor:
    def __init__(self, root):
        self.root = root
        self.root.title("Screen Censor 2.0")
        self.root.geometry("390x225")
        self.root.resizable(False, False)
        self.root.configure(bg="#151923")
        self.root.attributes("-topmost", True)

        self.running = False
        self.stop_event = threading.Event()
        self.box_lock = threading.Lock()
        self.boxes = []
        self.detector = None
        self.worker = None
        self.overlay_hwnd = None

        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        tk.Label(root, text="SCREEN CENSOR 2.0", fg="white", bg="#151923",
                 font=("Segoe UI", 16, "bold")).pack(pady=(15, 4))
        tk.Label(root, text="Sensor wajah + area payudara terbuka",
                 fg="#b9c2d0", bg="#151923", font=("Segoe UI", 9)).pack()

        self.status = tk.Label(root, text="Status: Mati", fg="#ff7777",
                               bg="#151923", font=("Segoe UI", 10, "bold"))
        self.status.pack(pady=12)

        row = tk.Frame(root, bg="#151923")
        row.pack()
        self.start_btn = tk.Button(row, text="MULAI SENSOR", width=15,
                                   command=self.start, bg="#238b57", fg="white",
                                   relief="flat", font=("Segoe UI", 10, "bold"))
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(row, text="MATIKAN", width=12,
                                  command=self.stop, state="disabled",
                                  bg="#a83e45", fg="white", relief="flat",
                                  font=("Segoe UI", 10, "bold"))
        self.stop_btn.pack(side="left", padx=5)

        tk.Label(root, text="STOP darurat: tekan Ctrl + Shift + F12",
                 fg="#ffd166", bg="#151923", font=("Segoe UI", 9, "bold")).pack(pady=(12, 2))
        tk.Label(root, text="Sensor memakai kotak hitam; deteksi bisa salah/terlewat.",
                 fg="#9aa5b5", bg="#151923", font=("Segoe UI", 8)).pack()

        self.overlay = tk.Toplevel(root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg="magenta")
        self.overlay.wm_attributes("-transparentcolor", "magenta")
        self.canvas = tk.Canvas(self.overlay, bg="magenta", highlightthickness=0,
                                bd=0)
        self.canvas.pack(fill="both", expand=True)

        self.root.bind_all("<Control-Shift-F12>", lambda _e: self.stop())
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.refresh_overlay)

    def _set_overlay_clickthrough(self):
        if sys.platform != "win32":
            return
        try:
            hwnd = self.overlay.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_TOOLWINDOW = 0x00000080
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE,
                                  style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW)
            self.overlay_hwnd = hwnd
        except Exception:
            self.overlay_hwnd = None

    def start(self):
        if self.running:
            return
        self.start_btn.config(state="disabled")
        self.status.config(text="Status: Memuat model…", fg="#ffd166")
        self.worker = threading.Thread(target=self.load_and_scan, daemon=True)
        self.worker.start()

    def load_and_scan(self):
        try:
            self.detector = NudeDetector()
            if self.stop_event.is_set():
                self.stop_event.clear()
            self.running = True
            self.root.after(0, self._started_ui)
            self.scan_loop()
        except Exception as exc:
            self.running = False
            self.root.after(0, lambda err=str(exc): self._start_failed(err))

    def _started_ui(self):
        self.status.config(text="Status: AKTIF", fg="#65d69a")
        self.stop_btn.config(state="normal")
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.overlay.geometry(f"{sw}x{sh}+0+0")
        self.overlay.deiconify()
        self.overlay.update_idletasks()
        self._set_overlay_clickthrough()
        self.overlay.lift()

    def _start_failed(self, error):
        self.start_btn.config(state="normal")
        self.status.config(text="Gagal memuat model", fg="#ff7777")
        messagebox.showerror("Screen Censor", f"Gagal memuat model deteksi:\n{error}")

    def _capture_screen(self, sct, monitor):
        # Hide only this app's overlay using Win32 synchronously before capture.
        hwnd = self.overlay_hwnd
        if hwnd and sys.platform == "win32":
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        try:
            shot = np.asarray(sct.grab(monitor))
            return cv2.cvtColor(shot, cv2.COLOR_BGRA2BGR)
        finally:
            if hwnd and sys.platform == "win32" and self.running:
                ctypes.windll.user32.ShowWindow(hwnd, 8)  # SW_SHOWNA

    def scan_loop(self):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                while self.running and not self.stop_event.is_set():
                    frame = self._capture_screen(sct, monitor)
                    h, w = frame.shape[:2]
                    found = []

                    # Detect all faces; no gender classification is attempted.
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = self.face_cascade.detectMultiScale(
                        gray, scaleFactor=FACE_SCALE, minNeighbors=FACE_NEIGHBORS,
                        minSize=(35, 35)
                    )
                    for x, y, fw, fh in faces:
                        found.append((int(x), int(y), int(x + fw), int(y + fh)))

                    # NudeNet detection for exposed female breast only.
                    tmp_name = None
                    try:
                        fd, tmp_name = tempfile.mkstemp(suffix=".jpg")
                        os.close(fd)
                        cv2.imwrite(tmp_name, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                        detections = self.detector.detect(tmp_name)
                        for item in detections:
                            label = str(item.get("class", "")).upper()
                            score = float(item.get("score", 0))
                            if label in BREAST_LABELS and score >= NUDENET_THRESHOLD:
                                x, y, bw, bh = item.get("box", [0, 0, 0, 0])
                                px, py = int(bw * 0.10), int(bh * 0.10)
                                x1, y1 = max(0, int(x)-px), max(0, int(y)-py)
                                x2, y2 = min(w, int(x+bw)+px), min(h, int(y+bh)+py)
                                found.append((x1, y1, x2, y2))
                    finally:
                        if tmp_name and os.path.exists(tmp_name):
                            try: os.remove(tmp_name)
                            except OSError: pass

                    with self.box_lock:
                        self.boxes = found
                    time.sleep(SCAN_INTERVAL)
        except Exception as exc:
            self.running = False
            self.root.after(0, lambda err=str(exc): self._scan_failed(err))
        finally:
            self.root.after(0, self._clear_overlay)

    def _scan_failed(self, error):
        self.status.config(text="Sensor berhenti karena error", fg="#ff7777")
        messagebox.showerror("Screen Censor", f"Pemindaian dihentikan:\n{error}")

    def refresh_overlay(self):
        if self.running and self.overlay.state() != "withdrawn":
            with self.box_lock:
                boxes = list(self.boxes)
            self.canvas.delete("all")
            for x1, y1, x2, y2 in boxes:
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                              fill="black", outline="black")
            self.overlay.lift()
        self.root.after(120, self.refresh_overlay)

    def _clear_overlay(self):
        with self.box_lock:
            self.boxes = []
        self.overlay.withdraw()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if self.status.winfo_exists():
            self.status.config(text="Status: Mati", fg="#ff7777")

    def stop(self):
        self.running = False
        self.stop_event.set()
        self._clear_overlay()

    def close(self):
        self.stop()
        self.root.destroy()

if __name__ == "__main__":
    if sys.platform != "win32":
        print("Screen Censor 2.0 dirancang untuk Windows 10/11.")
    root = tk.Tk()
    ScreenCensor(root)
    root.mainloop()
