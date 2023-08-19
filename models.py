from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    phone_number = db.Column(db.String(15), unique=True, nullable=True)  
    telegram_id = db.Column(db.String(80), unique=True, nullable=True)
    telegram_link_code = db.Column(db.String(120), unique=True, nullable=True)  # Added this line
    groups = db.relationship('Group', backref='user', lazy=True)
    reminders = db.relationship('Reminder', backref='user', lazy=True)
    theme = db.Column(db.String(5), default='light')  # New column

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    # This relationship means: When a user is defined, there are many reminders associated with this user.
    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(200), nullable=False)  # using the larger string limit
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notification_method = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=True)  # making group_id nullable
    
    def __repr__(self):
        return f"Reminder('{self.text}', '{self.date_time}', '{self.notification_method}')"

