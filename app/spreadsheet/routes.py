from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.spreadsheet import bp
from app.models.spreadsheet import Spreadsheet
import json
import csv
import io

@bp.route('/create', methods=['POST'])
@login_required
def create():
    name = request.form.get('spreadsheet_name', '').strip()
    
    if not name:
        flash('Spreadsheet name is required.')
        return redirect(url_for('main.home'))
    
    # Create new spreadsheet with empty data
    spreadsheet = Spreadsheet(name=name, user_id=current_user.id, data='{}')
    db.session.add(spreadsheet)
    db.session.commit()
    
    return redirect(url_for('spreadsheet.edit', id=spreadsheet.id))

@bp.route('/upload_csv', methods=['POST'])
@login_required
def upload_csv():
    name = request.form.get('spreadsheet_name', '').strip()
    csv_file = request.files.get('csv_file')
    
    if not name:
        flash('Spreadsheet name is required.')
        return redirect(url_for('main.home'))
    
    if not csv_file or not csv_file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.')
        return redirect(url_for('main.home'))
    
    try:
        # Read CSV file
        stream = io.StringIO(csv_file.stream.read().decode("UTF8"), newline=None)
        csv_data = list(csv.reader(stream))
        
        if not csv_data:
            flash('CSV file must contain at least one row of data.')
            return redirect(url_for('main.home'))
        
        # Extract column headers from first row
        column_headers = csv_data[0]
        
        # Convert to spreadsheet data format, starting from second row
        spreadsheet_data = {}
        for row_idx, row in enumerate(csv_data[1:], start=1):  # Start from 1 to skip header row
            for col_idx, value in enumerate(row):
                if value:  # Only store non-empty values
                    cell_key = f"{row_idx-1}-{col_idx}"
                    spreadsheet_data[cell_key] = value
        
        # Create column names mapping (A=0, B=1, etc.)
        column_names = {}
        for i, header in enumerate(column_headers):
            col_letter = chr(65 + i)  # Convert index to letter (0=A, 1=B, etc.)
            column_names[col_letter] = header
        
        # Create new spreadsheet with CSV data and column names
        spreadsheet = Spreadsheet(
            name=name,
            user_id=current_user.id,
            data=json.dumps(spreadsheet_data),
            column_names=json.dumps(column_names)
        )
        db.session.add(spreadsheet)
        db.session.commit()
        
        flash('Spreadsheet created successfully from CSV file.')
        return redirect(url_for('spreadsheet.edit', id=spreadsheet.id))
        
    except Exception as e:
        flash(f'Error processing CSV file: {str(e)}')
        return redirect(url_for('main.home'))

@bp.route('/edit/<int:id>')
@login_required
def edit(id):
    spreadsheet = Spreadsheet.query.get_or_404(id)
    
    # Check if user owns this spreadsheet
    if spreadsheet.user_id != current_user.id:
        flash('You do not have permission to edit this spreadsheet.')
        return redirect(url_for('main.home'))
    
    # Load spreadsheet data
    try:
        data = json.loads(spreadsheet.data)
    except:
        data = {}
    
    # Load column names
    try:
        column_names = json.loads(spreadsheet.column_names)
    except:
        column_names = {}
    
    return render_template('spreadsheet/edit.html', 
                         spreadsheet=spreadsheet, 
                         data=data,
                         column_names=column_names)

@bp.route('/save/<int:id>', methods=['POST'])
@login_required
def save(id):
    spreadsheet = Spreadsheet.query.get_or_404(id)
    
    # Check if user owns this spreadsheet
    if spreadsheet.user_id != current_user.id:
        return jsonify({
            'success': False,
            'message': 'You do not have permission to save this spreadsheet.'
        })
    
    try:
        data = request.json.get('data', {})
        column_names = request.json.get('column_names', {})
        
        spreadsheet.data = json.dumps(data)
        spreadsheet.column_names = json.dumps(column_names)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Spreadsheet saved successfully.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error saving spreadsheet: {str(e)}'
        }) 