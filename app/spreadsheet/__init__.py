from flask import Blueprint

bp = Blueprint('spreadsheet', __name__, url_prefix='/spreadsheet')

from app.spreadsheet import routes 