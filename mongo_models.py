import pymongo
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
import config

# Connect to MongoDB
if config.USE_MONGODB:
    mongo_client = pymongo.MongoClient(config.MONGODB_URI)
    db = mongo_client[config.MONGODB_DB]

    # Ensure indexes for performance
    db.users.create_index('username', unique=True)
    db.users.create_index('email', unique=True)
    db.admins.create_index('username', unique=True)
    db.admins.create_index('email', unique=True)
    db.face_records.create_index('user_id')
    db.authentication_logs.create_index('user_id')


class MongoDBMixin:
    """Base mixin to provide common functionality for MongoDB models."""
    
    @classmethod
    def get_by_id(cls, id):
        """Get document by ID."""
        if isinstance(id, str):
            # Convert string ID to ObjectId
            id = ObjectId(id)
        return cls.collection.find_one({'_id': id})

    @classmethod
    def get_all(cls):
        """Get all documents."""
        return list(cls.collection.find())

    def save(self):
        """Save document to database."""
        if hasattr(self, '_id') and self._id:
            # Update existing document
            result = self.collection.update_one(
                {'_id': self._id},
                {'$set': self.to_dict(exclude=['_id'])}
            )
            return result.modified_count > 0
        else:
            # Insert new document
            result = self.collection.insert_one(self.to_dict())
            self._id = result.inserted_id
            return bool(result.inserted_id)

    def delete(self):
        """Delete document from database."""
        if hasattr(self, '_id') and self._id:
            result = self.collection.delete_one({'_id': self._id})
            return result.deleted_count > 0
        return False

    def to_dict(self, exclude=None):
        """Convert model to dictionary, optionally excluding fields."""
        exclude = exclude or []
        result = {}
        for key, value in self.__dict__.items():
            if key not in exclude and not key.startswith('_'):
                result[key] = value
        return result

    def is_authenticated(self):
        """Flask-Login compatibility."""
        return True

    def is_active(self):
        """Flask-Login compatibility."""
        return self.is_active if hasattr(self, 'is_active') else True

    def is_anonymous(self):
        """Flask-Login compatibility."""
        return False

    def get_id(self):
        """Flask-Login compatibility."""
        return str(self._id)


class MongoAdmin(MongoDBMixin):
    """Admin model for MongoDB."""
    collection = db.admins if config.USE_MONGODB else None

    def __init__(self, **kwargs):
        self._id = kwargs.get('_id')
        self.username = kwargs.get('username')
        self.email = kwargs.get('email')
        self.password_hash = kwargs.get('password_hash')
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.datetime.utcnow())
        self.last_login = kwargs.get('last_login')

    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against stored hash."""
        return check_password_hash(self.password_hash, password)

    @classmethod
    def find_by_username(cls, username):
        """Find admin by username."""
        return cls.collection.find_one({'username': username})


class MongoUser(MongoDBMixin):
    """User model for MongoDB."""
    collection = db.users if config.USE_MONGODB else None

    def __init__(self, **kwargs):
        self._id = kwargs.get('_id')
        self.username = kwargs.get('username')
        self.email = kwargs.get('email')
        self.password_hash = kwargs.get('password_hash')
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.datetime.utcnow())
        self.last_login = kwargs.get('last_login')

    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against stored hash."""
        return check_password_hash(self.password_hash, password)

    @classmethod
    def find_by_username(cls, username):
        """Find user by username."""
        return cls.collection.find_one({'username': username})

    @classmethod
    def find_by_email(cls, email):
        """Find user by email."""
        return cls.collection.find_one({'email': email})
    
    @property
    def face_records(self):
        """Get all face records for this user."""
        if not hasattr(self, '_id') or not self._id:
            return []
        
        records = list(MongoFaceRecord.collection.find({'user_id': str(self._id)}))
        return [MongoFaceRecord(**record) for record in records]


class MongoFaceRecord(MongoDBMixin):
    """Face record model for MongoDB."""
    collection = db.face_records if config.USE_MONGODB else None

    def __init__(self, **kwargs):
        self._id = kwargs.get('_id')
        self.user_id = kwargs.get('user_id')
        self.embedding = kwargs.get('embedding')
        self.created_at = kwargs.get('created_at', datetime.datetime.utcnow())
        self.last_used = kwargs.get('last_used')
        self.confidence_score = kwargs.get('confidence_score')

    @classmethod
    def find_by_user_id(cls, user_id):
        """Find all face records for a user."""
        return list(cls.collection.find({'user_id': str(user_id)}))


class MongoAuthenticationLog(MongoDBMixin):
    """Authentication log model for MongoDB."""
    collection = db.authentication_logs if config.USE_MONGODB else None

    def __init__(self, **kwargs):
        self._id = kwargs.get('_id')
        self.user_id = kwargs.get('user_id')
        self.timestamp = kwargs.get('timestamp', datetime.datetime.utcnow())
        self.success = kwargs.get('success', False)
        self.ip_address = kwargs.get('ip_address')
        self.user_agent = kwargs.get('user_agent')
        self.confidence_score = kwargs.get('confidence_score')

    @classmethod
    def find_by_user_id(cls, user_id):
        """Find all authentication logs for a user."""
        return list(cls.collection.find({'user_id': str(user_id)}))


def create_default_admin():
    """Create default admin account if it doesn't exist."""
    if not config.USE_MONGODB:
        return
    
    admin = MongoAdmin.find_by_username('admin')
    if not admin:
        admin = MongoAdmin(
            username='admin',
            email='admin@visionid.com',
            is_active=True
        )
        admin.set_password('adminpass123')
        admin.save()
        print("Created default admin account in MongoDB")