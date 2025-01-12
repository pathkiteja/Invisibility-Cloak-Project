import cv2
import numpy as np
import threading
import time
import os
import signal
import subprocess
from flask import Flask, Response, render_template, request, jsonify

# Global variable to store the browser process
browser_process = None

# ==================== Cloak Effect Logic ====================
class CloakEffect:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.background = None
        self.cloak_type = 'Red'
        self.running = False

        self.color_bounds = {
            'Red': ([0, 120, 70], [10, 255, 255]),
            'Blue': ([90, 50, 50], [130, 255, 255]),
            'Green': ([35, 52, 72], [90, 255, 255]),
            'Yellow': ([20, 100, 100], [30, 255, 255]),
            'Skin': ([0, 48, 80], [20, 255, 255]),
        }

    def set_cloak_type(self, cloak_type):
        self.cloak_type = cloak_type

    def capture_background(self):
        print("Capturing background. Please move out of the frame...")
        time.sleep(2)
        for _ in range(30):
            _, self.background = self.cap.read()
        self.background = np.flip(self.background, axis=1)
        print("Background captured.")

    def generate_mask(self, frame):
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower, upper = self.color_bounds[self.cloak_type]
        mask = cv2.inRange(hsv_frame, np.array(lower), np.array(upper))
        return mask

    def start_cloak(self):
        self.capture_background()
        self.running = True

        while self.running:
            success, frame = self.cap.read()
            if not success:
                break

            frame = np.flip(frame, axis=1)
            mask = self.generate_mask(frame)
            inverse_mask = cv2.bitwise_not(mask)

            cloak_area = cv2.bitwise_and(self.background, self.background, mask=mask)
            visible_area = cv2.bitwise_and(frame, frame, mask=inverse_mask)
            combined_frame = cv2.addWeighted(cloak_area, 1, visible_area, 1, 0)

            ret, buffer = cv2.imencode('.jpg', combined_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    def stop(self):
        self.running = False
        self.cap.release()
        cv2.destroyAllWindows()

# ==================== Flask Backend ====================
app = Flask(__name__)
cloak_effect = CloakEffect()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(cloak_effect.start_cloak(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start', methods=['POST'])
def start_cloak():
    data = request.get_json()
    cloak_type = data.get('cloak_type')
    cloak_effect.set_cloak_type(cloak_type)
    return jsonify({'message': f'{cloak_type} cloak activated!'})

@app.route('/exit', methods=['POST'])
def exit_app():
    print("Shutting down the server and closing the browser...")
    shutdown_browser()
    shutdown_server()
    return jsonify({'message': 'Server is shutting down.'})

def shutdown_browser():
    global browser_process
    if browser_process:
        browser_process.terminate()
        print("Browser closed.")

def shutdown_server():
    os.kill(os.getpid(), signal.SIGTERM)

def run_flask():
    app.run(host='127.0.0.1', port=5000)

if __name__ == "__main__":
    print("Starting Flask server...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    time.sleep(2)  # Give the server time to start

    # Open browser and store the process
    browser_process = subprocess.Popen(["cmd", "/c", "start", "chrome", "http://127.0.0.1:5000"])
    
    print("Flask server is running. Open http://127.0.0.1:5000 in your browser.")
    while True:
        time.sleep(1)
