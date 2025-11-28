# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)

    # <--- NEW COLUMN --->
    role = Column(String, default="doctor")  # Can be "doctor" or "admin"
    # --------------------

    predictions = relationship("Prediction", back_populates="owner")


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    patient_name = Column(String)
    patient_age = Column(Integer)
    filename = Column(String)
    label = Column(String)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="predictions")


# gaurang code
# backend/models.py
# from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
# from sqlalchemy.orm import relationship
# from datetime import datetime
# from .database import Base


# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String, unique=True, index=True)
#     password_hash = Column(String)
#     predictions = relationship("Prediction", back_populates="owner")
#
#
# class Prediction(Base):
#     __tablename__ = "predictions"
#
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"))
#
#     # --- NEW FIELDS ---
#     patient_name = Column(String)
#     patient_age = Column(Integer)
#     # ------------------
#
#     filename = Column(String)
#     label = Column(String)
#     confidence = Column(Float)
#     created_at = Column(DateTime, default=datetime.utcnow)
#
#     owner = relationship("User", back_populates="predictions")