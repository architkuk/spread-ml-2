from flask import Blueprint

bp = Blueprint('ml', __name__, url_prefix='/ml')

from app.ml import routes 