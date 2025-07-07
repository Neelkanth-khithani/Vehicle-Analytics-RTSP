from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import uuid
import os
import json
from utils.user_camera_utils import (
    get_user_cameras, add_user_camera, delete_user_camera
)

camera_bp = Blueprint('camera', __name__)


@camera_bp.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles the display and addition of user cameras.

    For GET requests, this function retrieves the list of cameras associated with the logged-in user
    and renders the main index page, displaying these cameras. If the user is not logged in,
    they are redirected to the login page.

    For POST requests, this function processes the addition of a new camera. It extracts the RTSP URL
    from the form submission, ensures it includes the 'rtsp_transport=tcp' parameter, generates a
    unique ID for the new camera, and then saves this camera to the user's configuration.
    After adding the camera, it redirects the user back to the index page to refresh the camera list.
    """
    if not session.get('logged_in'):
        return redirect(url_for('auth.login'))

    username = session['username']
    user_cameras_config = get_user_cameras(username)
    camera_list = [{'id': cid, 'rtsp_url': conf['rtsp_url']} for cid, conf in user_cameras_config.items()]

    if request.method == 'POST':
        rtsp = request.form['rtsp_url']
        if '?rtsp_transport=' not in rtsp:
            rtsp += '?rtsp_transport=tcp'

        cam_id = str(uuid.uuid4())
        add_user_camera(username, cam_id, rtsp)
        return redirect(url_for('camera.index'))

    return render_template('index.html', cameras=camera_list)


@camera_bp.route('/save_zones/<cam_id>', methods=['GET', 'POST'])
def save_zones(cam_id):
    """
    Manages the saving and loading of zone configurations for a specific camera.

    This function first ensures that a user is logged in and authorized to access the specified camera.
    For POST requests, it receives JSON data containing zone information, saves this data to a
    JSON file specific to the camera ID within the 'data' directory, and returns a success status.
    For GET requests, it attempts to load existing zone data from the corresponding JSON file.
    If the file exists, the zone data is returned as a JSON response. If the file is not found,
    an empty JSON object for zones is returned.
    """
    if not session.get('logged_in'):
        return "Unauthorized", 401

    username = session['username']
    user_cameras_config = get_user_cameras(username)
    if cam_id not in user_cameras_config:
        return "Unauthorized", 401

    zones_path = f'data/zones_{cam_id}.json'

    if request.method == 'POST':
        zones_data = request.get_json()
        os.makedirs('data', exist_ok=True)
        with open(zones_path, 'w') as f:
            json.dump(zones_data, f, indent=4)
        return '', 200
    else:
        if os.path.exists(zones_path):
            with open(zones_path, 'r') as f:
                return jsonify(json.load(f))
        return jsonify({"zones": []})


@camera_bp.route('/stats/<cam_id>')
def stats(cam_id):
    """
    Retrieves and serves statistical data for a given camera ID.

    This function verifies user login and authorization for the specified camera.
    It attempts to load pre-calculated statistics from a JSON file named `stats_{cam_id}.json`
    located in the 'data' directory. If the file is found, its content is returned as a JSON response.
    In case the file does not exist (FileNotFoundError), an empty JSON object is returned,
    indicating no statistics are available yet for that camera. Unauthorized access
    or non-existent camera IDs result in a 401 Unauthorized response.
    """
    if not session.get('logged_in'):
        return "Unauthorized", 401

    username = session['username']
    user_cameras_config = get_user_cameras(username)
    if cam_id not in user_cameras_config:
        return "Unauthorized", 401

    try:
        with open(f'data/stats_{cam_id}.json') as f:
            return jsonify(json.load(f))
    except FileNotFoundError:
        return jsonify({})


@camera_bp.route('/delete_camera/<cam_id>', methods=['POST'])
def delete_camera(cam_id):
    """
    Deletes a camera and its associated data.

    This function handles POST requests to delete a camera specified by `cam_id`.
    It first ensures that the user is logged in and authorized. Upon successful deletion
    of the camera from the user's configuration, it attempts to stop and remove
    the active `VideoCamera` instance if it exists. Additionally, it removes any
    corresponding zone and statistics JSON files from the 'data' directory.
    Finally, the user is redirected to the main camera index page.
    """
    from services.detect import active_cameras

    if not session.get('logged_in'):
        return "Unauthorized", 401

    username = session['username']
    if delete_user_camera(username, cam_id):
        if cam_id in active_cameras:
            active_cameras[cam_id].__del__()
            del active_cameras[cam_id]
        for suffix in ['zones', 'stats']:
            path = f'data/{suffix}_{cam_id}.json'
            if os.path.exists(path):
                os.remove(path)
    return redirect(url_for('camera.index'))