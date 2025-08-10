import cv2
from ultralytics import YOLO
from utils.zones import load_zones, check_point_in_zones
from services.camera_state import active_cameras
import json
import os
import numpy as np
import time
import subprocess
import threading

class VideoCamera:
    """
    Manages video capture, object detection, and streaming for a single camera.

    This class handles connecting to an RTSP stream (either directly with OpenCV or via FFmpeg
    subprocess), performing object detection using a YOLOv8 model, identifying vehicles
    within predefined zones, and generating a live annotated video feed. It also manages
    reconnection logic and saves detection statistics.
    """

    def __init__(self, rtsp_url, cam_id, use_subprocess_ffmpeg=True, reconnect_delay=5):
        """
        Initializes the VideoCamera instance.

        Args:
            rtsp_url (str): The RTSP URL of the camera stream.
            cam_id (str): A unique identifier for the camera.
            use_subprocess_ffmpeg (bool, optional): Whether to use FFmpeg as a subprocess
                                                     for video capture. Defaults to True.
            reconnect_delay (int, optional): Delay in seconds before attempting to reconnect.
                                             Defaults to 5.
        """
        self.rtsp_url = rtsp_url
        self.cam_id = cam_id
        self.use_subprocess_ffmpeg = use_subprocess_ffmpeg
        self.reconnect_delay = reconnect_delay
        self.cap = None
        self.ffmpeg_process = None
        self.frame_width = None
        self.frame_height = None
        self.raw_image_size = None
        self._initialize_capture()

        if not self.cap or (isinstance(self.cap, cv2.VideoCapture) and not self.cap.isOpened()):
            print(f"ERROR: Could not initialize video capture for camera {self.cam_id} from {self.rtsp_url}")
            self.is_connected = False
        else:
            self.is_connected = True

        self.model = YOLO('yolov8n.pt')
        self.zones_file = f'data/zones_{cam_id}.json'
        self.stats_file = f'data/stats_{cam_id}.json'
        os.makedirs('data', exist_ok=True)

        self.vehicle_class_ids = {
            2: 'car',
            3: 'motorcycle',
            5: 'bus',
            7: 'truck',
        }
        self.lock = threading.Lock()

    def _initialize_capture(self):
        """
        Initializes the video capture mechanism, either using FFmpeg subprocess or OpenCV's VideoCapture.
        """
        if self.use_subprocess_ffmpeg:
            print(f"Attempting to start FFmpeg subprocess for camera {self.cam_id} at {self.rtsp_url}")
            try:
                command = [
                    'ffmpeg',
                    '-rtsp_transport', 'tcp',
                    '-i', self.rtsp_url,
                    '-vf', 'fps=10,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2',
                    '-f', 'image2pipe',
                    '-pix_fmt', 'bgr24',
                    '-vcodec', 'rawvideo',
                    '-an',
                    '-'
                ]
                self.frame_width = 1280
                self.frame_height = 720
                self.raw_image_size = self.frame_width * self.frame_height * 3

                self.ffmpeg_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=None)
                self.cap = "ffmpeg_subprocess"
            except Exception as e:
                print(f"Failed to start FFmpeg subprocess for camera {self.cam_id}: {e}")
                self.ffmpeg_process = None
                self.cap = None
        else:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if self.cap.isOpened():
                self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            else:
                self.cap = None

    def read_frame(self):
        """
        Reads a single frame from the video capture. Handles reconnection logic.

        Returns:
            tuple: A tuple containing:
                - bool: True if a frame was successfully read, False otherwise.
                - numpy.ndarray: The captured frame (BGR format) or None if reading failed.
        """
        if not self.is_connected:
            print(f"Camera {self.cam_id} not connected, attempting to re-initialize...")
            self._initialize_capture()
            if not self.cap or (isinstance(self.cap, cv2.VideoCapture) and not self.cap.isOpened()):
                self.is_connected = False
                print(f"Failed to re-initialize capture for camera {self.cam_id}. Waiting {self.reconnect_delay}s...")
                time.sleep(self.reconnect_delay)
                return False, None
            else:
                self.is_connected = True
                print(f"Successfully re-initialized capture for camera {self.cam_id}.")

        if self.use_subprocess_ffmpeg:
            try:
                raw_frame = self.ffmpeg_process.stdout.read(self.raw_image_size)
                if not raw_frame or len(raw_frame) != self.raw_image_size:
                    print(f"FFmpeg process for camera {self.cam_id} ended or returned incomplete frame. Reconnecting...")
                    self._release_capture()
                    self.is_connected = False
                    return False, None

                frame = np.frombuffer(raw_frame, np.uint8).reshape((self.frame_height, self.frame_width, 3))
                return True, frame
            except Exception as e:
                print(f"Error reading from FFmpeg pipe for camera {self.cam_id}: {e}. Reconnecting...")
                self._release_capture()
                self.is_connected = False
                return False, None
        else:
            ret, frame = self.cap.read()
            if not ret:
                print(f"Failed to read frame from camera {self.cam_id}. Reconnecting...")
                self.cap.release()
                self.is_connected = False
                return False, None
            return True, frame

    def _release_capture(self):
        """
        Releases the video capture resources.
        """
        if self.use_subprocess_ffmpeg:
            if self.ffmpeg_process is not None:
                print(f"Terminating FFmpeg process for camera {self.cam_id}...")
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if self.ffmpeg_process.poll() is None:
                        print(f"FFmpeg process for camera {self.cam_id} did not terminate, killing it.")
                        self.ffmpeg_process.kill()
                self.ffmpeg_process = None
                print(f"FFmpeg process for camera {self.cam_id} released.")
            else:
                print(f"No FFmpeg process to release for camera {self.cam_id}.")
            self.cap = None
        else:
            if self.cap:
                print(f"Releasing OpenCV capture for camera {self.cam_id}...")
                self.cap.release()
                self.cap = None
                print(f"OpenCV capture for camera {self.cam_id} released.")
            else:
                print(f"No OpenCV capture to release for camera {self.cam_id}.")

    def generate(self):
        """
        Generates a continuous stream of annotated video frames as JPEG bytes.

        This method is designed to be used with Flask's `Response` object for streaming.
        It continuously reads frames, performs object detection, overlays detection
        and zone information, and then encodes the frame as JPEG.
        """
        while True:
            ret, frame = self.read_frame()
            if not ret:
                continue

            zones_data = load_zones(self.zones_file)

            polygons_only = []
            valid_zones = []
            for zone in zones_data:
                if isinstance(zone, dict) and 'points' in zone and isinstance(zone['points'], list):
                    polygons_only.append(zone['points'])
                    valid_zones.append(zone)
                else:
                    print(f"Warning: Malformed zone data encountered: {zone}. Skipping.")

            zones_data = valid_zones

            try:
                desired_class_ids = list(self.vehicle_class_ids.keys())
                results = self.model.predict(source=frame, conf=0.5, verbose=False, classes=desired_class_ids)

                total_vehicles = 0
                vehicle_type_counts = {}
                zone_vehicle_counts = [{} for _ in range(len(polygons_only))]

                detections_in_zones = []

                if results and results[0].boxes is not None:
                    for i, box in enumerate(results[0].boxes.xyxy):
                        x1, y1, x2, y2 = box.tolist()
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

                        cls_id = int(results[0].boxes.cls[i])
                        conf = float(results[0].boxes.conf[i])
                        class_name = self.model.names[cls_id]

                        zone_idx = check_point_in_zones((cx, cy), polygons_only)

                        if cls_id in self.vehicle_class_ids and zone_idx != -1:
                            total_vehicles += 1
                            vehicle_type_counts[class_name] = vehicle_type_counts.get(class_name, 0) + 1

                            if zone_idx < len(zone_vehicle_counts):
                                zone_vehicle_counts[zone_idx][class_name] = zone_vehicle_counts[zone_idx].get(class_name, 0) + 1

                            detections_in_zones.append({
                                'box': [x1, y1, x2, y2],
                                'class_name': class_name,
                                'confidence': conf
                            })

                stats_data = {
                    "total_vehicles": total_vehicles,
                    "vehicle_type_counts": vehicle_type_counts,
                    "zone_vehicle_counts": zone_vehicle_counts
                }

                with open(self.stats_file, 'w') as f:
                    json.dump(stats_data, f)

                annotated_frame = frame.copy()

                for det in detections_in_zones:
                    x1, y1, x2, y2 = [int(coord) for coord in det['box']]
                    class_name = det['class_name']
                    confidence = det['confidence']

                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 255, 255), 2)

                    label = f'{class_name} {confidence:.2f}'

                    font = cv2.FONT_HERSHEY_SIMPLEX
                    font_scale = 0.6
                    font_thickness = 1
                    text_size = cv2.getTextSize(label, font, font_scale, font_thickness)[0]
                    text_x = x1
                    text_y = y1 - 10 if y1 - 10 > text_size[1] else y1 + text_size[1] + 10

                    cv2.rectangle(annotated_frame, (text_x, text_y - text_size[1] - 2),
                                    (text_x + text_size[0] + 2, text_y + 2), (255, 255, 255), -1)

                    cv2.putText(annotated_frame, label, (text_x, text_y),
                                    font, font_scale, (0, 0, 0), font_thickness, cv2.LINE_AA)

                overlay = annotated_frame.copy()
                alpha = 0.2

                for i, zone in enumerate(zones_data):
                    poly = zone['points']
                    if not poly:
                        continue
                    pts = np.array([(int(x), int(y)) for x, y in poly], np.int32)
                    pts = pts.reshape((-1, 1, 2))

                    if len(pts) > 2:
                        cv2.fillPoly(overlay, [pts], (255, 255, 255))
                        cv2.polylines(annotated_frame, [pts], True, (255, 255, 255), 2)

                annotated = cv2.addWeighted(overlay, alpha, annotated_frame, 1 - alpha, 0)

                _, jpeg = cv2.imencode('.jpg', annotated)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

            except Exception as e:
                print(f"Error processing frame in VideoCamera: {e}")
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                continue

    def __del__(self):
        """
        Destructor to ensure capture resources are released when the object is deleted.
        """
        self._release_capture()