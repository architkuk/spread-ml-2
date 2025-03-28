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
        
        # Convert to spreadsheet data format
        spreadsheet_data = {}
        for row_idx, row in enumerate(csv_data):  # Start from 0 to match spreadsheet's internal indexing
            for col_idx, value in enumerate(row):
                if value:  # Only store non-empty values
                    cell_key = f"{row_idx}-{col_idx}"
                    spreadsheet_data[cell_key] = value
        
        # Create new spreadsheet with CSV data
        spreadsheet = Spreadsheet(
            name=name,
            user_id=current_user.id,
            data=json.dumps(spreadsheet_data)
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
    
    # Ensure user owns this spreadsheet
    if spreadsheet.user_id != current_user.id:
        flash('You do not have permission to access this spreadsheet.')
        return redirect(url_for('main.home'))
    
    # Parse the data JSON
    try:
        data = json.loads(spreadsheet.data)
    except:
        data = {}
    
    return render_template('spreadsheet/edit.html', 
                          spreadsheet=spreadsheet, 
                          data=data,
                          title=f'Edit: {spreadsheet.name}')

@bp.route('/save/<int:id>', methods=['POST'])
@login_required
def save(id):
    spreadsheet = Spreadsheet.query.get_or_404(id)
    
    # Ensure user owns this spreadsheet
    if spreadsheet.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    # Get data from request
    data = request.json.get('data', {})
    
    # Update spreadsheet
    spreadsheet.data = json.dumps(data)
    db.session.commit()
    
    return jsonify({'success': True}) 