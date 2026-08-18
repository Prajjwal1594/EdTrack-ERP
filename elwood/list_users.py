from app import create_app
from app.models import User
app = create_app()
with app.app_context():
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id} | Role: {u.role} | Email: {u.email}")
