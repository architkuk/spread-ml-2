from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.spreadsheet import Spreadsheet
from app.models.ml_model import MLModel
import json
import numpy as np

bp = Blueprint('main', __name__)

def detect_column_type(data, col_letter):
    """Detect the type of a column based on its values."""
    col_index = ord(col_letter) - 65  # A=0, B=1, etc.
    has_number = False
    has_string = False
    has_non_empty = False
    
    # Check all cells in the column
    for key, value in data.items():
        if '-' in key:
            row, col = map(int, key.split('-'))
            if col == col_index:
                if value:
                    has_non_empty = True
                    try:
                        float(value)
                        has_number = True
                    except ValueError:
                        has_string = True
    
    if not has_non_empty:
        return None
    elif has_number and not has_string:
        return 'number'
    elif has_string and not has_number:
        return 'string'
    else:
        return 'mixed'

@bp.route('/')
@bp.route('/home')
@login_required
def home():
    # Get user's spreadsheets
    spreadsheets = Spreadsheet.query.filter_by(user_id=current_user.id).order_by(Spreadsheet.updated_at.desc()).all()
    
    # Create mappings for column names and types
    spreadsheet_column_names = {}
    spreadsheet_column_types = {}
    
    for spreadsheet in spreadsheets:
        try:
            column_names = json.loads(spreadsheet.column_names)
            spreadsheet_column_names[spreadsheet.id] = column_names
        except:
            spreadsheet_column_names[spreadsheet.id] = {}
            
        try:
            data = json.loads(spreadsheet.data)
            column_types = {}
            for col_letter in [chr(i) for i in range(65, 75)]:  # A through J
                col_type = detect_column_type(data, col_letter)
                if col_type:
                    column_types[col_letter] = col_type
            spreadsheet_column_types[spreadsheet.id] = column_types
        except:
            spreadsheet_column_types[spreadsheet.id] = {}
    
    # Get user's models through their spreadsheets
    models = MLModel.query.join(Spreadsheet).filter(Spreadsheet.user_id == current_user.id).order_by(MLModel.created_at.desc()).all()
    
    return render_template('home.html', 
                         title='SpreadML - Home', 
                         spreadsheets=spreadsheets, 
                         models=models,
                         spreadsheet_column_names=spreadsheet_column_names,
                         spreadsheet_column_types=spreadsheet_column_types) 