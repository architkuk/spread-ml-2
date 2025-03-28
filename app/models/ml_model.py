from datetime import datetime
from app import db

class MLModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model_type = db.Column(db.String(20), nullable=False)  # 'regression' or 'classification'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    input_columns = db.Column(db.Text, nullable=False)  # Stored as JSON string
    output_column = db.Column(db.String(10), nullable=False)  # Column letter (A, B, C, etc.)
    
    # Model parameters and metrics stored as JSON
    parameters = db.Column(db.Text, default='{}')
    metrics = db.Column(db.Text, default='{}')
    
    # Reference to the spreadsheet this model belongs to
    spreadsheet_id = db.Column(db.Integer, db.ForeignKey('spreadsheet.id'), nullable=False)
    
    def __repr__(self):
        return f'<MLModel {self.name} ({self.model_type})>' 