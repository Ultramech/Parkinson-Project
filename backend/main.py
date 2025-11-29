# backend/main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func  # <--- Imported func for counting stats
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import numpy as np
import cv2
from tensorflow.keras.models import load_model
from . import models, database
import tensorflow as tf

# --- CONFIGURATION ---
# MODEL_PATH = r"C:\Users\manav\Downloads\Parkinson-s-Disease-Classifier-master\Parkinson-s-Disease-Classifier-master\model\parkinsons_detector.model"
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "parkinsons_detector.keras")


CLASSES = ["Healthy", "Parkinson"]
SECRET_KEY = "my_super_secret_key_for_final_year_project"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI()
models.Base.metadata.create_all(bind=database.engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
model = None


# --- HELPERS ---
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@app.on_event("startup")
def load_ai_model():
    global model
    try:
        # model = load_model(MODEL_PATH)
        model = tf.keras.models.load_model(MODEL_PATH)

        print("[INFO] Model loaded successfully!")
    except Exception as e:
        print(f"[ERROR] Could not load model: {e}")


# --- AUTH ROUTES ---

# In backend/main.py

@app.post("/register")
def register_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    db_user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # ✅ TC1 SECURITY FIX: bcrypt 72-byte safe handling
    raw_password = form_data.password
    safe_password = raw_password.encode("utf-8")[:72].decode("utf-8", errors="ignore")

    hashed_password = pwd_context.hash(safe_password)

    new_user = models.User(
        username=form_data.username,
        password_hash=hashed_password,
        role="doctor"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully"}



@app.post("/token")
def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    raw_password = form_data.password
    safe_password = raw_password.encode("utf-8")[:72].decode("utf-8", errors="ignore")

    if not user or not pwd_context.verify(safe_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }



# --- DOCTOR ROUTES ---

@app.get("/history")
def get_prediction_history(current_user: models.User = Depends(get_current_user)):
    return current_user.predictions


@app.post("/predict")
async def predict(
        patient_name: str = Form(...),
        patient_age: int = Form(...),
        file: UploadFile = File(...),
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (224, 224))
    image = image.astype("float32") / 255.0
    image = np.expand_dims(image, axis=0)

    preds = model.predict(image)
    idx = np.argmax(preds, axis=1)[0]
    label = CLASSES[idx]
    confidence = float(preds[0][idx] * 100)

    db_record = models.Prediction(
        user_id=current_user.id,
        patient_name=patient_name,
        patient_age=patient_age,
        filename=file.filename,
        label=label,
        confidence=confidence
    )
    db.add(db_record)
    db.commit()
    return {"patient": patient_name, "prediction": label, "confidence": round(confidence, 2)}


# --- NEW ADMIN ROUTES ---

@app.get("/admin/stats")
def get_system_stats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if user is actually an admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized. Admin access required.")

    # Calculate Stats
    total_users = db.query(models.User).count()
    total_predictions = db.query(models.Prediction).count()
    parkinson_count = db.query(models.Prediction).filter(models.Prediction.label == "Parkinson").count()
    healthy_count = db.query(models.Prediction).filter(models.Prediction.label == "Healthy").count()

    return {
        "total_users": total_users,
        "total_predictions": total_predictions,
        "parkinson_cases": parkinson_count,
        "healthy_cases": healthy_count
    }