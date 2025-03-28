from app import create_app, db
from app.models.user import User

def init_db():
    app = create_app()
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if demo user exists
        demo_user = User.query.filter_by(username='demo').first()
        if not demo_user:
            # Create demo user
            demo_user = User(username='demo')
            demo_user.set_password('cNrV70Mr$4#%')
            db.session.add(demo_user)
            db.session.commit()
            print("Demo user created successfully")
        else:
            print("Demo user already exists")

if __name__ == '__main__':
    init_db() 