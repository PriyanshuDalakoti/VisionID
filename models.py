from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    """User model for storing user data and face embeddings."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FaceRecord(db.Model):
    """Model to store face recognition data."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # This stores face embedding data (feature vectors)
    embedding = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    
    # Define relationship
    user = db.relationship('User', backref=db.backref('face_records', lazy=True))

class AuthenticationLog(db.Model):
    """Logs all authentication attempts."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    success = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 can be up to 45 chars
    user_agent = db.Column(db.String(256), nullable=True)
    confidence_score = db.Column(db.Float, nullable=True)
    
    # Define relationship
    user = db.relationship('User', backref=db.backref('authentication_logs', lazy=True))
