import cv2
import json
from ultralytics import YOLO
from zones import load_zones, check_point_in_zones

# === CONFIG ===
RTSP_URL = "rtsp://localhost:8554/camera1"
YOLO_MODEL = 'yolov8n.pt'  # nano for fast test

# === LOAD ===
print("[INFO] Loading YOLO...")
model = YOLO(YOLO_MODEL)

print("[INFO] Opening RTSP stream...")
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)
if not cap.isOpened():
    print("[ERROR] Cannot open RTSP stream.")
    exit(1)

print("[INFO] Loading zones...")
polygons = load_zones()

print("[INFO] Starting detection loop...")
while True:
    ret, frame = cap.read()
    if not ret:
        print("[WARN] Failed to grab frame.")
        break

    results = model.predict(source=frame, conf=0.3)

    zone_counts = {}

    for box in results[0].boxes.xyxy:
        x1, y1, x2, y2 = box.tolist()
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        zone_idx = check_point_in_zones((cx, cy), polygons)
        if zone_idx != -1:
            zone_counts[zone_idx] = zone_counts.get(zone_idx, 0) + 1

        cv2.circle(frame, (int(cx), int(cy)), 4, (0, 255, 0), -1)

    annotated_frame = results[0].plot()

    y_offset = 30
    for idx, count in zone_counts.items():
        text = f"Zone {idx}: {count}"
        cv2.putText(annotated_frame, text, (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        y_offset += 30

    desired_width = 800
    aspect_ratio = annotated_frame.shape[1] / annotated_frame.shape[0]
    desired_height = int(desired_width / aspect_ratio)
    resized_frame = cv2.resize(annotated_frame, (desired_width, desired_height))

    cv2.imshow("YOLO + Zones", resized_frame)

    with open("stats.json", "w") as f:
        json.dump(zone_counts, f, indent=2)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()