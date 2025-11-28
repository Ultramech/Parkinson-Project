# create_admin.py
from backend.database import SessionLocal, engine
from backend import models
from passlib.context import CryptContext

# Setup Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()


def create_super_admin():
    username = "admin1"
    password = "secret_password_123"

    # Check if exists
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        print("Admin already exists!")
        return

    # Create Admin
    hashed_pw = pwd_context.hash(password)
    admin_user = models.User(
        username=username,
        password_hash=hashed_pw,
        role="admin"  # <--- This is the only place "admin" is allowed
    )

    db.add(admin_user)
    db.commit()
    print(f"Success! Admin created. Username: {username}")


if __name__ == "__main__":
    create_super_admin()