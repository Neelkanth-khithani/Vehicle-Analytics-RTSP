from flask import Flask, render_template, request, Response, redirect, url_for, jsonify, session
from detect import VideoCamera
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here'

USERS_FILE = 'data/users.json'

def load_users():
    os.makedirs('data', exist_ok=True)
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_users(users):
    os.makedirs('data', exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

CAMERAS_FILE = 'data/cameras.json'
active_cameras = {} 

def load_all_cameras_config():
    os.makedirs('data', exist_ok=True)
    if os.path.exists(CAMERAS_FILE):
        try:
            with open(CAMERAS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_all_cameras_config(all_cameras_config):
    os.makedirs('data', exist_ok=True)
    with open(CAMERAS_FILE, 'w') as f:
        json.dump(all_cameras_config, f, indent=4)

def get_user_cameras(username):
    all_cameras = load_all_cameras_config()
    return all_cameras.get(username, {})

def add_user_camera(username, cam_id, rtsp_url):
    all_cameras = load_all_cameras_config()
    if username not in all_cameras:
        all_cameras[username] = {}
    all_cameras[username][cam_id] = {'rtsp_url': rtsp_url}
    save_all_cameras_config(all_cameras)

def delete_user_camera(username, cam_id):
    all_cameras = load_all_cameras_config()
    if username in all_cameras and cam_id in all_cameras[username]:
        del all_cameras[username][cam_id]
        save_all_cameras_config(all_cameras)
        return True
    return False


# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username]['password'] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users:
            return render_template('register.html', error='Username already exists')
        
        users[username] = {'password': password} # No encryption as per request
        save_users(users)
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

# --- Protected Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    username = session['username']
    user_cameras_config = get_user_cameras(username)
    camera_list = []
    for cam_id, config in user_cameras_config.items():
        camera_list.append({'id': cam_id, 'rtsp_url': config['rtsp_url']})

    if request.method == 'POST':
        rtsp = request.form['rtsp_url']
        if '?rtsp_transport=' not in rtsp:
            rtsp += '?rtsp_transport=tcp'
        
        cam_id = str(uuid.uuid4())
        add_user_camera(username, cam_id, rtsp)
        return redirect(url_for('index'))
    
    return render_template('index.html', cameras=camera_list)

@app.route('/stream/<cam_id>')
def stream_page(cam_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    username = session['username']
    user_cameras_config = get_user_cameras(username)
    
    if cam_id not in user_cameras_config:
        return "Camera not found for this user", 404
    
    rtsp_url = user_cameras_config[cam_id]['rtsp_url']

    if cam_id not in active_cameras or not active_cameras[cam_id].cap.isOpened():
        active_cameras[cam_id] = VideoCamera(rtsp_url, cam_id)
    
    return render_template('stream.html', cam_id=cam_id)

@app.route('/video_feed/<cam_id>')
def video_feed(cam_id):
    if not session.get('logged_in'):
        return "Unauthorized", 401
    
    username = session['username']
    user_cameras_config = get_user_cameras(username)
    if cam_id not in user_cameras_config: 
        return "Camera not found for this user or unauthorized", 401

    if cam_id not in active_cameras:
        rtsp_url = user_cameras_config[cam_id]['rtsp_url']
        active_cameras[cam_id] = VideoCamera(rtsp_url, cam_id)
        
    return Response(active_cameras[cam_id].generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/save_zones/<cam_id>', methods=['GET', 'POST'])
def save_zones(cam_id):
    if not session.get('logged_in'):
        return "Unauthorized", 401

    username = session['username']
    user_cameras_config = get_user_cameras(username)
    if cam_id not in user_cameras_config: 
        return "Camera not found for this user or unauthorized", 401

    zones_file_path = f'data/zones_{cam_id}.json'
    if request.method == 'POST':
        zones_data = request.get_json()
        os.makedirs('data', exist_ok=True)
        with open(zones_file_path, 'w') as f:
            json.dump(zones_data, f, indent=4)
        return '', 200
    else: # GET request to load zones
        if os.path.exists(zones_file_path):
            try:
                with open(zones_file_path, 'r') as f:
                    return jsonify(json.load(f))
            except (json.JSONDecodeError, IOError):
                return jsonify({"zones": []})
        return jsonify({"zones": []})

@app.route('/stats/<cam_id>')
def stats(cam_id):
    if not session.get('logged_in'):
        return "Unauthorized", 401

    username = session['username']
    user_cameras_config = get_user_cameras(username)
    if cam_id not in user_cameras_config: 
        return "Camera not found for this user or unauthorized", 401

    try:
        with open(f'data/stats_{cam_id}.json') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({})

@app.route('/delete_camera/<cam_id>', methods=['POST'])
def delete_camera(cam_id):
    if not session.get('logged_in'):
        return "Unauthorized", 401

    username = session['username']
    if delete_user_camera(username, cam_id): 
        if cam_id in active_cameras:
            active_cameras[cam_id].__del__()
            del active_cameras[cam_id]

        zones_file_path = f'data/zones_{cam_id}.json'
        stats_file_path = f'data/stats_{cam_id}.json'
        if os.path.exists(zones_file_path):
            os.remove(zones_file_path)
        if os.path.exists(stats_file_path):
            os.remove(stats_file_path)
            
        print(f"Camera {cam_id} and its associated data deleted for user {username}.")
    else:
        print(f"Attempted to delete camera {cam_id} for user {username}, but it was not found.")
        
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)