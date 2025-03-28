from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)
    
    from app.routes import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.spreadsheet import bp as spreadsheet_bp
    app.register_blueprint(spreadsheet_bp)
    
    from app.ml import bp as ml_bp
    app.register_blueprint(ml_bp)
    
    return app 