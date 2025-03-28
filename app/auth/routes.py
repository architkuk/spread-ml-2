from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.auth import bp
from app.models.user import User
from app import db

# Demo credentials
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123"

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Only allow demo account
        if username == DEMO_USERNAME and password == DEMO_PASSWORD:
            # Create or get demo user
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            return redirect(url_for('main.home'))
        flash('Invalid credentials. Please contact the administrator for access.', 'error')
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login')) 