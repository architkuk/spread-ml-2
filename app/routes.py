from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.spreadsheet import Spreadsheet

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/home')
@login_required
def home():
    # Get user's spreadsheets
    spreadsheets = Spreadsheet.query.filter_by(user_id=current_user.id).order_by(Spreadsheet.updated_at.desc()).all()
    return render_template('home.html', title='SpreadML - Home', spreadsheets=spreadsheets) 