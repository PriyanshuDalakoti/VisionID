from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    """User model for storing user data and face embeddings."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    # In a production system, this would store face encoding data
    face_embedding = db.Column(db.LargeBinary, nullable=True)

class FaceRecord(db.Model):
    """Model to store face recognition data."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # This would store face embedding data (feature vectors)
    embedding = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    
    # Define relationship
    user = db.relationship('User', backref=db.backref('face_records', lazy=True))
