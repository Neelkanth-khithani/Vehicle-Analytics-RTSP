from flask import Flask
from routes.auth_routes import auth_bp
from routes.camera_routes import camera_bp
from routes.stream_routes import stream_bp

app = Flask(__name__)
app.secret_key = 'SECRET@123'

app.register_blueprint(auth_bp)
app.register_blueprint(camera_bp)
app.register_blueprint(stream_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)