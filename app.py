import os
import logging
import base64
import cv2
import numpy as np
import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from face_recognition_utils import detect_face, verify_face

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///visionid.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Print database URL for debugging (without credentials)
db_url = app.config["SQLALCHEMY_DATABASE_URI"]
logger.info(f"Using database: {db_url.split('@')[-1] if '@' in db_url else db_url}")

# Initialize the app with extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    if session.get('user_type') == 'admin':
        from models import Admin
        return Admin.query.get(int(user_id))
    else:
        from models import User
        return User.query.get(int(user_id))

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Create default admin account if it doesn't exist
    from models import Admin
    admin = Admin.query.filter_by(username="admin").first()
    if not admin:
        admin = Admin(username="admin", email="admin@visionid.com")
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()
        logger.info("Created default admin account")

@app.route('/')
def landing():
    """Render the landing page that directs users to registration or authentication."""
    return render_template('landing.html')

@app.route('/authenticate')
def index():
    """Render the main authentication page."""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a new user."""
    from models import User
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Basic validation
        if not username or not email or not password:
            return render_template('register.html', error='All fields are required')
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error='Username already exists')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            return render_template('register.html', error='Email already registered')
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('profile'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error='An error occurred. Please try again.')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login a user."""
    from models import User
    
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            # Update last login time
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            # Redirect to next page or profile
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('profile'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout a user."""
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    # Count user's face records
    face_count = 0
    if current_user.face_records:
        face_count = len(current_user.face_records)
    
    return render_template('profile.html', user=current_user, face_count=face_count)

@app.route('/api/authenticate', methods=['POST'])
def authenticate():
    """API endpoint to authenticate a face."""
    from models import User, AuthenticationLog, FaceRecord
    
    try:
        # Get the base64 image from the request
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'status': 'failure', 'message': 'No image provided'}), 400
        
        # Extract the base64 image data (remove the data:image/jpeg;base64, prefix)
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Get username if provided (for specific user authentication)
        username = data.get('username')
        
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
        
        # Authentication variables
        is_authenticated = False
        confidence_score = 0.0
        user_id = None
        
        # If a username is provided, attempt to authenticate against that user's face records
        if username:
            user = User.query.filter_by(username=username).first()
            if user:
                user_id = user.id
                face_records = FaceRecord.query.filter_by(user_id=user_id).all()
                
                if face_records:
                    # In a real system, we would compare face embeddings
                    # For now, we'll simulate successful authentication for users with face records
                    is_authenticated = verify_face(face)
                    confidence_score = 0.95 if is_authenticated else 0.3
                else:
                    logger.info(f"User {username} has no face records")
                    is_authenticated = False
                    confidence_score = 0.0
            else:
                logger.info(f"Username {username} not found")
        else:
            # Without a username, use general authentication
            # In a real system, we would search all face records for a match
            is_authenticated = verify_face(face)
            confidence_score = 0.95 if is_authenticated else 0.3
        
        # If authenticated and we have a user_id, log them in
        if is_authenticated and user_id:
            user = User.query.get(user_id)
            if user:
                login_user(user)
                
                # Update last login time
                user.last_login = datetime.datetime.utcnow()
                db.session.commit()
        
        # Log the authentication attempt
        log_entry = AuthenticationLog(
            user_id=user_id,
            success=is_authenticated,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string if request.user_agent else None,
            confidence_score=confidence_score
        )
        db.session.add(log_entry)
        db.session.commit()
        
        # Save the authentication attempt image for security review
        if face is not None:
            import uuid
            import os
            
            # Generate a unique filename for the authentication attempt
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            status = "success" if is_authenticated else "failed"
            auth_filename = f"auth_{timestamp}_{status}_{uuid.uuid4().hex[:8]}.jpg"
            auth_path = os.path.join('static', 'faces', auth_filename)
            
            # Save the authentication face image
            try:
                auth_face_bytes = cv2.imencode('.jpg', face)[1].tobytes()
                with open(auth_path, 'wb') as f:
                    f.write(auth_face_bytes)
                logger.info(f"Saved authentication attempt image to {auth_path}")
            except Exception as e:
                logger.error(f"Error saving authentication face image: {str(e)}")
                # Continue even if file saving fails
        
        if is_authenticated:
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful',
                'user_id': user_id
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

@app.route('/api/enroll', methods=['POST'])
@login_required
def enroll_face():
    """API endpoint to enroll a user's face."""
    from models import FaceRecord
    import pickle
    import uuid
    import os
    
    try:
        # Get the base64 image from the request
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'status': 'failure', 'message': 'No image provided'}), 400
        
        # Extract the base64 image data
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
        
        # In a production system, we would:
        # 1. Extract face embeddings using a face recognition model
        # 2. Store these embeddings in the database
        
        # For this demo, we'll just store the raw face image bytes as a placeholder
        # In a real system, this would be a numeric embedding vector
        face_bytes = cv2.imencode('.jpg', face)[1].tobytes()
        
        # Generate a unique filename for the face image
        face_filename = f"{current_user.username}_{uuid.uuid4().hex}.jpg"
        face_path = os.path.join('static', 'faces', face_filename)
        
        # Save the face image to the filesystem
        try:
            with open(face_path, 'wb') as f:
                f.write(face_bytes)
            logger.info(f"Saved face image to {face_path}")
        except Exception as e:
            logger.error(f"Error saving face image: {str(e)}")
            # Continue even if file saving fails
        
        # Create a new face record for the current user
        face_record = FaceRecord(
            user_id=current_user.id,
            embedding=face_bytes,
            confidence_score=1.0  # Perfect match for enrollment
        )
        
        db.session.add(face_record)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Face enrolled successfully',
            'record_id': face_record.id,
            'image_path': face_path
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Face enrollment error: {str(e)}")
        return jsonify({
            'status': 'failure',
            'message': f'Error processing request: {str(e)}'
        }), 500

# Admin routes and functionality
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    from models import Admin
    
    if current_user.is_authenticated and session.get('user_type') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            # Set session to indicate this is an admin
            session['user_type'] = 'admin'
            
            login_user(admin)
            admin.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid admin credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    """Admin logout."""
    session.pop('user_type', None)
    logout_user()
    return redirect(url_for('landing'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard page."""
    if session.get('user_type') != 'admin':
        return redirect(url_for('landing'))
    
    from models import User, FaceRecord, AuthenticationLog
    
    # Get user and authentication statistics
    user_count = User.query.count()
    face_count = FaceRecord.query.count()
    auth_count = AuthenticationLog.query.count()
    
    # Get all users with their face records
    users = User.query.all()
    
    return render_template('admin_dashboard.html', 
                          admin=current_user, 
                          users=users, 
                          user_count=user_count, 
                          face_count=face_count, 
                          auth_count=auth_count)

@app.route('/admin/delete/user/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    """Delete a user and all their associated records."""
    if session.get('user_type') != 'admin':
        return redirect(url_for('landing'))
    
    from models import User, FaceRecord, AuthenticationLog
    import os
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Delete face records for this user
        face_records = FaceRecord.query.filter_by(user_id=user_id).all()
        for record in face_records:
            # In a production system, you'd also remove the face image files
            db.session.delete(record)
        
        # Delete authentication logs for this user
        auth_logs = AuthenticationLog.query.filter_by(user_id=user_id).all()
        for log in auth_logs:
            db.session.delete(log)
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete/face/<int:face_id>')
@login_required
def admin_delete_face(face_id):
    """Delete a face record."""
    if session.get('user_type') != 'admin':
        return redirect(url_for('landing'))
    
    from models import FaceRecord
    
    face_record = FaceRecord.query.get_or_404(face_id)
    
    try:
        db.session.delete(face_record)
        db.session.commit()
        
        return redirect(url_for('admin_dashboard'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting face record: {str(e)}")
        return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
