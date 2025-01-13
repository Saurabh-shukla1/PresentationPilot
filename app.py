import os
import cv2
from cvzone.HandTrackingModule import HandDetector
import numpy as np
from flask import Flask, render_template, Response, request, redirect, url_for, flash, send_from_directory

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Variables
width, height = 1280, 720
folderpath = "images"

# Create the images folder if it doesn't exist
if not os.path.exists(folderpath):
    os.makedirs(folderpath)

# Load slides
pathImages = sorted(os.listdir(folderpath), key=len)
imagenumber = 0

# Annotation variables
annotations = [[]]
annotationsNumber = 0
annotationsstart = False

# Gesture thresholds and delay
gestureThreashold = 450
buttonPressed = False
buttonDelay = 30
counter = 0

# Initialize webcam and hand detector
cap = cv2.VideoCapture(0)
cap.set(3, width)
cap.set(4, height)
detector = HandDetector(detectionCon=0.8, maxHands=1)

def load_images():
    global pathImages
    pathImages = sorted(os.listdir(folderpath), key=len)

def generate_frames():
    global imagenumber, annotations, annotationsNumber, annotationsstart, buttonPressed, counter

    while True:
        success, img = cap.read()
        if not success:
            break

        img = cv2.flip(img, 1)
        pathfullImage = os.path.join(folderpath, pathImages[imagenumber])
        imgCurrent = cv2.imread(pathfullImage)

        hands, img = detector.findHands(img)
        cv2.line(img, (0, gestureThreashold), (width, gestureThreashold), (0, 255, 255))

        if hands and not buttonPressed:
            hand = hands[0]
            fingers = detector.fingersUp(hand)
            lmList = hand['lmList']
            cx, cy = hand['center']

            # Finger positions for drawing
            indexfinger = lmList[8][0], lmList[8][1]
            xval = int(np.interp(lmList[8][0], [width // 2, width], [0, width]))
            yval = int(np.interp(lmList[8][1], [150, height - 150], [0, height]))
            indexfinger = xval, yval

            if cy <= gestureThreashold:
                # Gesture: Left navigation
                if fingers == [1, 0, 0, 0, 0]:
                    if imagenumber > 0:
                        annotations = [[]]
                        annotationsNumber = 0
                        annotationsstart = False
                        buttonPressed = True
                        imagenumber -= 1

                # Gesture: Right navigation
                elif fingers == [0, 0, 0, 0, 1]:
                    if imagenumber < len(pathImages) - 1:
                        annotations = [[]]
                        annotationsNumber = 0
                        annotationsstart = False
                        buttonPressed = True
                        imagenumber += 1

            # Gesture: Pointer
            if fingers == [0, 1, 1, 0, 0]:
                cv2.circle(imgCurrent, indexfinger, 12, (255, 0, 0), cv2.FILLED)

            # Gesture: Drawing
            if fingers == [0, 1, 0, 0, 0]:
                if not annotationsstart:
                    annotationsstart = True
                    annotationsNumber += 1
                    annotations.append([])
                cv2.circle(imgCurrent, indexfinger, 12, (0, 255, 0), cv2.FILLED)
                annotations[annotationsNumber].append(indexfinger)
            else:
                annotationsstart = False

            # Gesture: Erase
            if fingers == [1, 1, 1, 1, 1]:
                if annotations:
                    if annotationsNumber >= 0:
                        annotations.pop(-1)
                        annotationsNumber -= 1
                        buttonPressed = True

        # Button delay handling
        if buttonPressed:
            counter += 1
            if counter > buttonDelay:
                counter = 0
                buttonPressed = False

        # Draw annotations
        for i in range(len(annotations)):
            for j in range(len(annotations[i])):
                if j != 0:
                    cv2.line(imgCurrent, annotations[i][j - 1], annotations[i][j], (0, 100, 120), 8)

        # Add webcam feed to slide
        hs, ws = int(120 * 1), int(213 * 1)
        imgSmall = cv2.resize(img, (ws, hs))
        h, w, _ = imgCurrent.shape
        imgCurrent[0:hs, w - ws:w] = imgSmall

        # Encode for streaming
        _, buffer = cv2.imencode('.jpg', imgCurrent)
        imgCurrent = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + imgCurrent + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

# Route for another page
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')


@app.route('/start')
def start():
    return render_template('start.html')

@app.route('/powerpoint')
def powerpoint():
    return render_template('powerpoint.html')

@app.route('/Gtype1')
def Gtype1():
    return render_template('Gtype1.html')

@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            file_path = os.path.join(folderpath, file.filename)
            file.save(file_path)
            load_images()  # Reload images after upload
            flash('File uploaded successfully')
            return redirect(url_for('upload'))
    return render_template('upload.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    try:
        app.run(debug=True, host="0.0.0.0", port=5000)
    finally:
        cap.release()
