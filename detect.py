import cv2
from ultralytics import YOLO
from zones import load_zones, check_point_in_zones
import json
import os
import numpy as np
import time
import subprocess
import threading

class VideoCamera:
    def __init__(self, rtsp_url, cam_id, use_subprocess_ffmpeg=True, reconnect_delay=5):
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

        if not self.cap or (not self.use_subprocess_ffmpeg and not self.cap.isOpened()):
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
        self.exclude_class_ids = {0: 'person'} # Keep this as you might still want to exclude persons even if they are in a zone

        self.lock = threading.Lock()

    def _initialize_capture(self):
        if self.use_subprocess_ffmpeg:
            print(f"Attempting to start FFmpeg subprocess for camera {self.cam_id} at {self.rtsp_url}")
            try:
                command = [
                    'ffmpeg',
                    '-i', self.rtsp_url,
                    '-rtsp_transport', 'tcp',
                    '-f', 'image2pipe',
                    '-pix_fmt', 'bgr24',
                    '-vcodec', 'rawvideo',
                    '-an',
                    '-'
                ]
                self.frame_width = 1280
                self.frame_height = 720
                self.raw_image_size = self.frame_width * self.frame_height * 3

                self.ffmpeg_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.cap = True

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
        if not self.is_connected:
            print(f"Camera {self.cam_id} not connected, attempting to re-initialize...")
            self._initialize_capture()
            if not self.cap or (not self.use_subprocess_ffmpeg and not self.cap.isOpened()):
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
        if self.use_subprocess_ffmpeg:
            if self.ffmpeg_process:
                self.ffmpeg_process.terminate()
                self.ffmpeg_process.wait(timeout=5)
                if self.ffmpeg_process.poll() is None:
                    self.ffmpeg_process.kill()
                self.ffmpeg_process = None
                self.cap = None
        else:
            if self.cap:
                self.cap.release()
                self.cap = None

    def generate(self):
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
                # Perform prediction without initial class filtering, to get all detections
                results = self.model.predict(source=frame, conf=0.5, verbose=False)

                total_vehicles = 0
                vehicle_type_counts = {}
                zone_vehicle_counts = [{} for _ in range(len(polygons_only))]

                # Prepare a list to store only the detections we want to keep and plot
                detections_to_plot = [] 
                
                if results and results[0].boxes is not None:
                    for i, box in enumerate(results[0].boxes.xyxy):
                        x1, y1, x2, y2 = box.tolist()
                        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

                        cls_id = int(results[0].boxes.cls[i])
                        class_name = self.model.names[cls_id]

                        # 1. Check if the detection's center is within any of the defined zones
                        zone_idx = check_point_in_zones((cx, cy), polygons_only)
                        
                        # 2. If it's in a zone AND it's a desired vehicle class AND NOT an excluded class
                        if zone_idx != -1 and cls_id in self.vehicle_class_ids and cls_id not in self.exclude_class_ids:
                            # This detection meets all criteria (in-zone, vehicle, not excluded person)
                            detections_to_plot.append({
                                'box': box,
                                'cls_id': cls_id,
                                'conf': results[0].boxes.conf[i]
                            })

                            total_vehicles += 1
                            vehicle_type_counts[class_name] = vehicle_type_counts.get(class_name, 0) + 1
                            
                            if zone_idx < len(zone_vehicle_counts):
                                zone_vehicle_counts[zone_idx][class_name] = zone_vehicle_counts[zone_idx].get(class_name, 0) + 1

                stats_data = {
                    "total_vehicles": total_vehicles,
                    "vehicle_type_counts": vehicle_type_counts,
                    "zone_vehicle_counts": zone_vehicle_counts
                }

                with open(self.stats_file, 'w') as f:
                    json.dump(stats_data, f)

                # Create a blank frame or the original frame to draw on
                annotated_frame = frame.copy() 

                # Manually draw bounding boxes for detections_to_plot
                for det in detections_to_plot:
                    x1, y1, x2, y2 = [int(coord) for coord in det['box']]
                    cls_id = det['cls_id']
                    conf = det['conf']
                    class_name = self.model.names[cls_id]

                    # Define color for bounding box (e.g., green for vehicles)
                    color = (0, 255, 0) 
                    
                    # Draw rectangle
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Put label
                    label = f"{class_name} {conf:.2f}"
                    cv2.putText(annotated_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                # Ensure annotated_frame is BGR for drawing zones
                if annotated_frame.ndim == 3 and annotated_frame.shape[2] == 4:
                    annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGBA2BGR)
                elif annotated_frame.ndim == 3 and annotated_frame.shape[2] == 3:
                    # Already BGR or RGB, assume BGR if coming from OpenCV read
                    pass 
                else: # Handle grayscale or other formats if necessary
                    annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_GRAY2BGR)


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
                # If an error occurs during processing, still yield the raw frame
                _, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                continue

    def __del__(self):
        self._release_capture()