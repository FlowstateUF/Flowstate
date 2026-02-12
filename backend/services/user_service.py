from app.db import db
from app.models import User

# Remove once user creation is implemented
def create_test_user():
    u = User(username='test', email='test@test.com')
    u.set_password('test')

    db.session.add(u)
    db.session.commit()

    print("Test user created successfully.")