from flask import Flask, render_template, request, jsonify
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/save_zones', methods=['POST'])
def save_zones():
    data = request.get_json()
    with open('zones.json', 'w') as f:
        json.dump(data, f, indent=2)
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(debug=True)