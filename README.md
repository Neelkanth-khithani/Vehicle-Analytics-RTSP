# RTSP Stream-based Vehicle Detection and Zone Analytics

This project provides web application for monitoring RTSP (Real-Time Streaming Protocol) camera streams, performing real-time object detection (specifically vehicles) using YOLOv8, and analyzing object presence within user-defined zones. Built with Flask, it offers a secure login system, camera management, live video streaming, and interactive zone drawing capabilities.

## Table of Contents
* [Project Overview and Structure](#rtsp-stream-based-vehicle-detection-and-zone-analytics)
    * [Core Files and Directories](#core-files-and-directories)
    * [Routes](#routes)
    * [Services](#services)
    * [Static Web Assets](#static-web-assets)
    * [HTML Templates](#html-templates)
    * [Utility Functions](#utility-functions)
* [How the Entire Project Works](#how-the-entire-project-works)
    * [Application Initialization](#application-initialization)
    * [User Authentication](#user-authentication)
    * [Camera Management](#camera-management)
    * [Live Stream and Object Detection](#live-stream-and-object-detection)
    * [Utilities](#utilities)
* [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Installation](#installation)
    * [Running the Application](#running-the-application)
* [Test RTSP Server Setup](#test-rtsp-server-setup)
    * [How to Run the Test RTSP Server](#how-to-run-the-test-rtsp-server)
    * [How to Finetune the Test RTSP Server](#how-to-finetune-the-test-rtsp-server)

## Project Structure
```
.
├── app.py
├── requirements.txt
├── yolov8n.pt
├── data
├── routes
│   ├── init.py
│   ├── auth_routes.py
│   ├── camera_routes.py
│   └── stream_routes.py
├── services
│   ├── init.py
│   ├── camera_state.py
│   └── detect.py
├── static
│   └── css
│       ├── index.css
│       ├── login.css
│       ├── register.css
│       └── stream.css
├── templates
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── stream.html
└── utils
    ├── init.py
    ├── user_camera_utils.py
    └── zones.py
```

---

## Core Files and Directories

### Routes
#### Defining Application Endpoints

- **`routes/auth_routes.py`**
  Handles user authentication (login, registration, logout).

| Route | Method(s) | Description |
|-------|-----------|-------------|
| `/login` | GET | Renders `login.html`. |
| | POST | Authenticates user using credentials. On success, sets `session['logged_in']` and redirects to dashboard. |
| `/register` | GET | Renders `register.html`. |
| | POST | Creates a new user if username doesn't exist. Saves credentials using `save_users()`. |
| `/logout` | GET | Logs the user out by clearing session variables. |

- **`routes/camera_routes.py`**
  Manages camera configurations, zone setup, and detection statistics.

| Route | Method(s) | Description |
|-------|-----------|-------------|
| `/` | GET | Displays camera dashboard (`index.html`) for the authenticated user. |
| | POST | Registers a new RTSP camera. Appends `?rtsp_transport=tcp`, assigns UUID, saves via `add_user_camera()`. |
| `/save_zones/<cam_id>` | GET | Loads zone config from `data/zones_<cam_id>.json`. |
| | POST | Validates and saves updated zone config to the same file. |
| `/get_stats/<cam_id>` | GET | Returns detection stats from `data/stats_<cam_id>.json`. |
| `/delete_camera/<cam_id>` | POST | Removes camera from user config, shuts down stream, deletes associated JSON files. |

- **`routes/stream_routes.py`**
  Provides live video streaming routes.

| Route | Method(s) | Description |
|-------|-----------|-------------|
| `/stream/<cam_id>` | GET | Renders `stream.html`. Validates session and initializes a `VideoCamera` instance if not already active. |
| `/video_feed/<cam_id>` | GET | Streams MJPEG video using Flask response. Frames are fetched from the active `VideoCamera` object. |

### Services
#### Core Logic and External Interactions

Encapsulates business logic, live stream management, and integration with the YOLOv8 detection model.

| File | Description |
|------|-------------|
| `camera_state.py` | Defines `active_cameras`, a global dictionary used to track live `VideoCamera` instances per user/camera. Serves as an in-memory state manager. |
| `detect.py` | Core detection module containing the `VideoCamera` class for streaming, inference, annotation, and statistics collection. See below for a breakdown of the class. |

<details>
<summary><strong>VideoCamera Class (in <code>detect.py</code>)</strong></summary>

| Component | Purpose |
|----------|---------|
| **`_initialize_capture()` / `read_frame()`** | Connects to the RTSP stream and fetches video frames. Supports fallback between OpenCV and FFmpeg, with reconnection logic. |
| **`get_frame()`** | Performs real-time detection on each frame using YOLOv8, filters results based on defined zones, annotates detections, and updates `stats_<cam_id>.json`. |
| **`__del__()`** | Ensures all resources (video capture handles or FFmpeg subprocesses) are cleanly released on object destruction. |

</details>

### Static Web Assets
#### Web Assets

Contains static resources (CSS) served directly to the client browser.

| Path | Description |
|------|-------------|
| `static/css/index.css` | Styles for the main camera dashboard (`index.html`). |
| `static/css/login.css` | Stylesheet for the login form and layout. |
| `static/css/register.css` | Styling for the user registration page. |
| `static/css/stream.css` | Layout and UI styling for the camera stream page (`stream.html`). |

### HTML Templates
#### HTML Templates

Holds [Jinja2](https://jinja.palletsprojects.com/) templates rendered by Flask to generate dynamic pages.

| Template | Description |
|----------|-------------|
| `index.html` | Main camera dashboard. Lists existing cameras, provides UI for adding new RTSP streams, displays user-specific content, and includes logout functionality. |
| `login.html` | Login form for user authentication. |
| `register.html` | User registration form with input validation and error messaging. |
| `stream.html` | Live stream view with zone management UI. Integrates canvas drawing for zone creation, JavaScript logic for real-time detection stats, and stream playback tied to `VideoCamera` instances. |

### Utility Functions
#### Utility Functions

Contains reusable helper functions for user management, camera configuration, and zone detection logic.

#### `user_camera_utils.py` — User & Camera Management

| Function | Description |
|----------|-------------|
| `load_users()` | Loads user credentials from `data/users.json`. |
| `save_users(users)` | Saves user credentials to `data/users.json`. |
| `load_all_cameras_config()` | Loads all camera configurations from `data/cameras.json`. |
| `save_all_cameras_config(config)` | Persists all camera configurations to `data/cameras.json`. |
| `get_user_cameras(username)` | Retrieves a list of cameras configured for a given user. |
| `add_user_camera(username, cam_id, rtsp_url)` | Adds a new camera entry for the specified user. |
| `delete_user_camera(username, cam_id)` | Removes a camera entry associated with a user. |

#### `zones.py` — Zone Handling Logic

| Function | Description |
|----------|-------------|
| `load_zones(zones_file)` | Loads zone definitions from a given JSON file (e.g., `data/zones_<cam_id>.json`). |
| `save_zones(zones_file, zones)` | Writes zone definitions to a JSON file. |
| `check_point_in_zones(point, zones_polygons_only)` | Returns `True` if a given point lies inside any of the defined polygonal zones. Uses a ray casting algorithm. |

## How the Entire Project Works

### Application Initialization
It begins with `app.py`. When you run this file, it:

- Initializes the Flask web application instance.
- Sets a `secret_key` for secure session management (used for login state).
- Registers the `auth_bp`, `camera_bp`, and `stream_bp` blueprints, which link route handlers across modules into the app.

### User Authentication
- **Accessing the Application**
  Users start by visiting the root URL (`http://localhost:5000/`). If not authenticated, they are redirected to `/login` by the route handler in `camera_routes.py`.

- **Login Process**
  - Loads `login.html` on GET request.
  - On form submission (`POST /login`), the server:
    - Retrieves `username` and `password`
    - Verifies them using `user_camera_utils.load_users()` from `data/users.json`
    - If correct, sets `session['logged_in'] = True` and stores `session['username']`
    - Redirects to the camera dashboard (`/`)

- **Registration Process**
  - Accessible via `/register`
  - On form submission:
    - Checks if the username exists
    - If not, adds user via `save_users()`
    - Prompts the user to log in

### Camera Management
- **Dashboard Display**
  - After login, users land on the dashboard (`/`), handled by `index()` in `camera_routes.py`
  - It calls `get_user_cameras(username)` to fetch the user's camera list from `data/cameras.json`
  - Renders `index.html` with the camera list

- **Adding a New Camera**
  - The user submits an RTSP URL via a form on the dashboard
  - `camera_routes.py`:
    - Appends `?rtsp_transport=tcp` to the URL
    - Generates a unique `cam_id` using `uuid.uuid4()`
    - Saves the configuration using `add_user_camera()`
    - Refreshes the dashboard view

- **Deleting a Camera**
  - A "Delete" button on each camera triggers a `POST` to `/delete_camera/<cam_id>`
  - The server:
    - Removes the camera from `data/cameras.json`
    - Stops the active stream (if any) via `VideoCamera` instance
    - Deletes zone and statistics files:
      - `data/zones_<cam_id>.json`
      - `data/stats_<cam_id>.json`

### Live Stream and Object Detection
#### Initiating a Stream

- Clicking "View Stream" navigates to `/stream/<cam_id>`
- The `stream_page()` function in `stream_routes.py`:
  - Verifies the user’s access
  - Renders `stream.html` for the camera

#### Fetching the Video Feed

- `stream.html` contains an `<img>` element pointing to `/video_feed/<cam_id>`, which is a streaming MJPEG endpoint
- On request:
  - `stream_routes.py` checks if a `VideoCamera` instance exists in `active_cameras`
  - If not, it instantiates one from `detect.py`
  - The instance connects to the RTSP stream (via OpenCV or FFmpeg)
  - `generate_frames()` continuously:
    - Captures a frame
    - Runs object detection
    - Annotates and yields the frame as a JPEG
  - Flask streams this multipart response to the browser

#### Real-time Detection & Zone Logic
- `VideoCamera.get_frame()`:
  - Uses `yolov8n.pt` with the Ultralytics API to detect objects in each frame
  - Filters for vehicle classes using a predefined `vehicle_class_ids` map

##### Zone Management

- Users draw polygon zones over the stream using canvas tools in `stream.html`
- JavaScript captures the zone data and sends it to `/save_zones/<cam_id>` via AJAX
- `camera_routes.py` writes the data using `zones.save_zones()` to:
  - `data/zones_<cam_id>.json`
- Each frame:
  - Loads these zones via `zones.load_zones()`
  - Calls `zones.check_point_in_zones()` to determine if a detected object intersects any zone

##### Statistics Collection

- `VideoCamera` tracks detection counts per zone
- Saves data incrementally to `data/stats_<cam_id>.json`
- `stream.html` polls `/get_stats/<cam_id>` via AJAX
- The results are displayed in a "Stats Panel" next to the live video stream

### Utilities
Throughout the process, the utility files play a crucial supporting role:

* **`user_camera_utils.py`**: Manages the persistence of user accounts and their associated camera configurations (RTSP URLs, unique IDs) by interacting with `data/users.json` and `data/cameras.json`.
* **`zones.py`**: Provides the essential logic for loading, saving, and performing point-in-polygon checks for the detection zones, which is fundamental to the zone-based analysis.

## Getting Started

### Prerequisites

| Requirement | Description |
|-------------|-------------|
| [Python](https://www.python.org/downloads/) ≥ 3.10| Backend runtime environment |
| [FFmpeg](https://ffmpeg.org/download.html) | RTSP stream processing tool |
| [requirements.txt](./requirements.txt) | Python package dependencies |

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Neelkanth-khithani/Vehicle-Analytics-RTSP.git
    cd Vehicle-Analytics/RTSP
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

1.  **Ensure FFmpeg is installed and accessible in your system's PATH.**

2.  **Run the Flask application:**
    ```bash
    python app.py
    ```
    The application will run on `http://0.0.0.0:5000/`.

## Test RTSP Server Setup

This setup allows you to create a simulated live RTSP stream from a video file (like `test1.mp4`) using `mediamtx` as the streaming server and FFmpeg to push the video to `mediamtx`.

* **`mediamtx` (or `rtsp-simple-server`)**: A lightweight, robust, and zero-dependency RTSP/RTMP/HLS/WebRTC server. It acts as the central hub that receives the video stream from FFmpeg and serves it to your Flask application (or any RTSP client).
* **FFmpeg**: A powerful open-source multimedia framework that can decode, encode, transcode, mux, demux, stream, filter, and play nearly anything that humans and machines have created. Here, it's used to read a local video file (`test1.mp4`) and re-stream it over RTSP to `mediamtx`.
* **`test1.mp4`**: Your source video file that will be streamed.

### How to Run the Test RTSP Server

To get this test server running, you'll need both `mediamtx` and FFmpeg.

| Component | Purpose / Action |
|---|---|
| [mediamtx](https://github.com/bluenviron/mediamtx/releases) | RTSP server binary (formerly `rtsp-simple-server`). |
| [FFmpeg](https://ffmpeg.org/download.html) | Required to push video stream to the RTSP server. Ensure it's installed and available in system PATH. |
| `test1.mp4` | A sample video file. Place in same directory as `mediamtx`, or update the path in `server1.yml`. |

**Steps to Run:**

1.  **Configure `mediamtx`:** Your `server1.yml` file seems to be a configuration for `mediamtx`. It defines the RTSP transport, addresses, and crucially, a `path` named `camera1` with a `runOnInit` command.
    * **`server1.yml` Content Analysis:**
        ```yaml
        rtspTransports: [tcp] # Specifies to use TCP for RTSP transport (more reliable)
        rtspAddress: :8554    # mediamtx will listen for RTSP connections on port 8554
        # ... other addresses for RTP, RTMP, HLS, WebRTC, SRT
        paths:
          camera1: # Defines a stream path named 'camera1'
            runOnInit: ffmpeg -re -stream_loop -1 -i test1.mp4 -r 10 -c:v libx264 -preset medium -crf 34 -vf scale=1280:-2 -an -f rtsp -rtsp_transport tcp rtsp://ffmpeguser1:ffmpegpass1@localhost:8554/camera1
            # This command is executed by mediamtx when the 'camera1' path is initialized.
            # It pushes 'test1.mp4' as an RTSP stream to mediamtx itself.
        ```
    * **Note:** Your `mediamtx.yml` file is a more general configuration for `mediamtx`. You can either combine the settings from `server1.yml` into `mediamtx.yml` or just use `server1.yml` if it contains all necessary overrides for your test setup. For this explanation, we assume `server1.yml` is used as the primary configuration passed directly to `mediamtx`, overriding or supplementing default `mediamtx.yml` settings.

2.  **Start `mediamtx`:**
    Open a terminal or command prompt, navigate to the directory where you saved `mediamtx.exe` (or `mediamtx` binary) and `server1.yml`. Then, run:
    ```bash
    ./mediamtx server1.yml
    ```
    (On Windows, it might be `mediamtx.exe server1.yml`)

    * `mediamtx` will start and, because of the `runOnInit` command in `server1.yml`, it will automatically execute the FFmpeg command to start streaming `test1.mp4` to its own `rtsp://localhost:8554/camera1` path.

3.  **Verify the Stream:**
    You can use VLC media player or your Flask application to connect to the RTSP URL: `rtsp://ffmpeguser1:ffmpegpass1@localhost:8554/camera1`.

### How to Finetune the Test RTSP Server

Finetuning primarily involves adjusting the FFmpeg command within the `runOnInit` section of your `server1.yml` (or `mediamtx.yml`). You can also adjust `mediamtx` server settings.

#### FFmpeg Command (`runOnInit`) Parameters:

The FFmpeg command is:
`ffmpeg -re -stream_loop -1 -i test1.mp4 -r 10 -c:v libx264 -preset medium -crf 34 -vf scale=1280:-2 -an -f rtsp -rtsp_transport tcp rtsp://ffmpeguser1:ffmpegpass1@localhost:8554/camera1`
Here's how to finetune it:

| Parameter | Description | How to Customize |
|---|---|---|
| `-re` | Simulate live input | Keep this for real-time playback speed |
| `-stream_loop -1` | Loop video forever | Change `-1` to a number (e.g., `5`) or remove to play once |
| `-i test1.mp4` | Input video file | Replace with your video file path |
| `-r 10` | Output frame rate | Increase for smoother stream (e.g., `25`), decrease for low bandwidth |
| `-c:v libx264` | Use H.264 codec | Use `libx265` for better compression or `copy` to skip re-encoding |
| `-preset medium` | Encoding speed/quality | Use `ultrafast`, `fast`, or `slow` depending on performance/quality need |
| `-crf 34` | Video quality setting | Lower = better quality (18–28 recommended), `23` is default |
| `-vf scale=1280:-2` | Resize video | Set desired resolution (e.g., `640:480`), or remove to keep original |
| `-an` | Disable audio | Remove this to include audio, add `-c:a aac` if needed |
| `-f rtsp` | Set output format | Must be `rtsp` for RTSP streaming |
| `-rtsp_transport tcp` | RTSP over TCP | Keep for reliable streaming over most networks |
| `rtsp://ffmpeguser1:ffmpegpass1@localhost:8554/camera1` | RTSP output URL | Change username, password, IP, port, or stream path as needed |

---

## Members

This project was built during an internship program by:

* **Neelkanth Khithani**
    * [https://www.linkedin.com/in/neelkanth-khithani/](https://www.linkedin.com/in/neelkanth-khithani/)
* **Kushl Alve**
    * [https://www.linkedin.com/in/kushl-alve/](https://www.linkedin.com/in/kushl-alve/)
* **Vedang Gambhire**
    * [https://www.linkedin.com/in/vedang-gambhire-114049254/](https://www.linkedin.com/in/vedang-gambhire-114049254/)
* **Jatin Navani**
    * [https://www.linkedin.com/in/jatinnavani/](https://www.linkedin.com/in/jatinnavani/)


***
