from flask import render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.spreadsheet import bp
from app.models.spreadsheet import Spreadsheet
import json

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