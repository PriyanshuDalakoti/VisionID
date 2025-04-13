import os
import logging
import base64
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from face_recognition_utils import detect_face, verify_face

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the SQLite database for development
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///visionid.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()

@app.route('/')
def index():
    """Render the main application page."""
    return render_template('index.html')

@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    """API endpoint to authenticate a face."""
    try:
        # Get the base64 image from the request
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'status': 'failure', 'message': 'No image provided'}), 400
        
        # Extract the base64 image data (remove the data:image/jpeg;base64, prefix)
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode the base64 image
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({'status': 'failure', 'message': 'Invalid image data'}), 400
        
        # Detect face in the image
        face = detect_face(img)
        if face is None:
            return jsonify({'status': 'failure', 'message': 'No face detected in image'}), 400
        
        # In a real system, we would compare the detected face with stored face embeddings
        # For demo purposes, we'll simulate authentication
        is_authenticated = verify_face(face)
        
        if is_authenticated:
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful'
            })
        else:
            return jsonify({
                'status': 'failure',
                'message': 'Authentication failed - face not recognized'
            })
            
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        return jsonify({
            'status': 'failure',
            'message': f'Error processing request: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
