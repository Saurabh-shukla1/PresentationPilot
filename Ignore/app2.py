import math

from flask import Flask, render_template, Response, jsonify, request, url_for
import cv2
import mediapipe as mp
import numpy as np
from pptx import Presentation
from PIL import Image
import io
import os
import shutil
import win32com.client
import pythoncom
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/slides'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# Global variables
current_slide = 0
drawing_mode = False
highlight_mode = False
erase_mode = False
drawings = {}  # Dictionary to store drawings for each slide
slide_count = 0


def convert_pptx_to_images(pptx_path):
    """Convert PowerPoint slides to images using win32com"""
    pythoncom.CoInitialize()

    # Clear existing slides
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'])
    os.makedirs(app.config['UPLOAD_FOLDER'])

    # Create a PowerPoint application object
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    presentation = powerpoint.Presentations.Open(pptx_path)

    try:
        for i, slide in enumerate(presentation.Slides):
            # Export slide as JPG
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], f'slide{i}.jpg')
            slide.Export(image_path, "JPG")

        global slide_count
        slide_count = len(presentation.Slides)
    finally:
        # Close PowerPoint
        presentation.Close()
        powerpoint.Quit()
        pythoncom.CoUninitialize()


def calculate_finger_distance(hand_landmarks):
    thumb_tip = (hand_landmarks.landmark[4].x, hand_landmarks.landmark[4].y)
    index_tip = (hand_landmarks.landmark[8].x, hand_landmarks.landmark[8].y)
    return math.sqrt((thumb_tip[0] - index_tip[0]) ** 2 + (thumb_tip[1] - index_tip[1]) ** 2)


def detect_gestures(hand_landmarks):
    global current_slide, drawing_mode, highlight_mode, erase_mode

    # Get finger positions
    thumb_tip = hand_landmarks.landmark[4].y
    index_tip = hand_landmarks.landmark[8].y
    middle_tip = hand_landmarks.landmark[12].y
    ring_tip = hand_landmarks.landmark[16].y
    pinky_tip = hand_landmarks.landmark[20].y

    # Next slide gesture (index finger up)
    if index_tip < hand_landmarks.landmark[5].y and all(
            finger > hand_landmarks.landmark[5].y for finger in [middle_tip, ring_tip, pinky_tip]):
        if current_slide < slide_count - 1:
            current_slide += 1
            return "NEXT"

    # Previous slide gesture (middle finger up)
    if middle_tip < hand_landmarks.landmark[9].y and all(
            finger > hand_landmarks.landmark[5].y for finger in [index_tip, ring_tip, pinky_tip]):
        if current_slide > 0:
            current_slide -= 1
            return "PREVIOUS"

    # Draw gesture (pinch)
    finger_distance = calculate_finger_distance(hand_landmarks)
    if finger_distance < 0.1:
        drawing_mode = True
        erase_mode = False
        highlight_mode = False
        return "DRAW"
    else:
        drawing_mode = False

    # Erase gesture (three fingers up)
    if all(tip < hand_landmarks.landmark[5].y for tip in [index_tip, middle_tip, ring_tip]) and pinky_tip > \
            hand_landmarks.landmark[5].y:
        drawing_mode = False
        erase_mode = True
        highlight_mode = False
        return "ERASE"
    else:
        erase_mode = False

    # Highlight gesture (index and middle fingers up)
    if all(tip < hand_landmarks.landmark[5].y for tip in [index_tip, middle_tip]) and all(
            tip > hand_landmarks.landmark[5].y for tip in [ring_tip, pinky_tip]):
        drawing_mode = False
        erase_mode = False
        highlight_mode = True
        return "HIGHLIGHT"
    else:
        highlight_mode = False

    return None


def process_frame(frame):
    # Initialize drawings for current slide if not exists
    if current_slide not in drawings:
        drawings[current_slide] = []

    # Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw hand landmarks
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            # Get index finger tip coordinates
            x = int(hand_landmarks.landmark[8].x * frame.shape[1])
            y = int(hand_landmarks.landmark[8].y * frame.shape[0])

            # Detect gestures
            gesture = detect_gestures(hand_landmarks)

            if drawing_mode:
                # Add point to drawings
                drawings[current_slide].append(('draw', (x, y)))

            elif erase_mode:
                # Erase nearby points
                erase_radius = 20
                new_drawings = []
                for mode, point in drawings[current_slide]:
                    dist = math.sqrt((x - point[0]) ** 2 + (y - point[1]) ** 2)
                    if dist > erase_radius:
                        new_drawings.append((mode, point))
                drawings[current_slide] = new_drawings

            elif highlight_mode:
                # Add highlight point
                drawings[current_slide].append(('highlight', (x, y)))

    # Draw all points for current slide
    for i in range(1, len(drawings[current_slide])):
        prev_mode, prev_point = drawings[current_slide][i - 1]
        curr_mode, curr_point = drawings[current_slide][i]

        if prev_mode == curr_mode:
            if curr_mode == 'draw':
                cv2.line(frame, prev_point, curr_point, (0, 255, 0), 2)
            elif curr_mode == 'highlight':
                cv2.rectangle(frame,
                              (curr_point[0] - 25, curr_point[1] - 25),
                              (curr_point[0] + 25, curr_point[1] + 25),
                              (0, 255, 255), 2)

    return frame


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.endswith('.pptx'):
        return jsonify({'error': 'Invalid file type'}), 400

    # Save uploaded file to temporary location
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, 'presentation.pptx')
    file.save(temp_path)

    try:
        # Convert PPTX to images
        convert_pptx_to_images(temp_path)
        return jsonify({'success': True, 'slide_count': slide_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir)


def gen_frames():
    camera = cv2.VideoCapture(0)
    while True:
        success, frame = camera.read()
        if not success:
            break

        frame = process_frame(frame)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/get_current_slide')
def get_current_slide():
    return jsonify({
        'slide': current_slide,
        'total_slides': slide_count
    })


@app.route('/clear_drawings')
def clear_drawings():
    global drawings
    drawings[current_slide] = []
    return jsonify({'success': True})


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)