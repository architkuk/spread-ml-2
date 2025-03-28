from app import create_app, db
from app.models.user import User

app = create_app()

# Initialize database and create demo user
with app.app_context():
    db.create_all()
    demo_user = User.query.filter_by(username='demo').first()
    if not demo_user:
        demo_user = User(username='demo')
        demo_user.set_password('demo123')
        db.session.add(demo_user)
        db.session.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 