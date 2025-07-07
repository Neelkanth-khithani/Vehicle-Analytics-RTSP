import json
import os

USERS_FILE = 'data/users.json'
CAMERAS_FILE = 'data/cameras.json'

def load_users():
    os.makedirs('data', exist_ok=True)
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users):
    os.makedirs('data', exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_all_cameras_config():
    os.makedirs('data', exist_ok=True)
    if os.path.exists(CAMERAS_FILE):
        try:
            with open(CAMERAS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
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