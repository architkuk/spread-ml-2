from datetime import datetime
from app import db
from flask_login import current_user

class Spreadsheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Store spreadsheet data as JSON string
    data = db.Column(db.Text, default='{}')
    
    # Add relationship to ML models
    models = db.relationship('MLModel', backref='spreadsheet', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Spreadsheet {self.name}>' 