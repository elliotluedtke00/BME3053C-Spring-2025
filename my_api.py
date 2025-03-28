from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
import jwt
from enum import Enum
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="Patient Management System API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security configuration
SECRET_KEY = "your-secure-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Enums for data validation
class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

# Data Models
class PatientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    age: int = Field(..., gt=0, lt=150)
    gender: Gender
    medical_history: Optional[str] = None

class Patient(PatientBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Mock database
patients_db = {}
users_db = {
    "admin": {
        "username": "admin",
        "password": "admin123"  # In production, use hashed passwords
    }
}

# Authentication functions
def create_access_token(data: dict):
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    to_encode.update({"exp": expires})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# API Endpoints
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or form_data.password != user["password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    token = create_access_token({"sub": user["username"]})
    return {"access_token": token, "token_type": "bearer"}

@app.post("/patients/", response_model=Patient, status_code=201)
async def create_patient(
    patient: PatientBase,
    username: str = Depends(get_current_user)
):
    patient_id = len(patients_db) + 1
    patient_data = Patient(
        id=patient_id,
        created_at=datetime.now(),
        **patient.dict()
    )
    patients_db[patient_id] = patient_data
    return patient_data

@app.get("/patients/", response_model=List[Patient])
async def read_patients(
    skip: int = 0,
    limit: int = 10,
    username: str = Depends(get_current_user)
):
    return list(patients_db.values())[skip : skip + limit]

@app.get("/patients/{patient_id}", response_model=Patient)
async def read_patient(
    patient_id: int,
    username: str = Depends(get_current_user)
):
    if patient_id not in patients_db:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )
    return patients_db[patient_id]

@app.put("/patients/{patient_id}", response_model=Patient)
async def update_patient(
    patient_id: int,
    patient: PatientBase,
    username: str = Depends(get_current_user)
):
    if patient_id not in patients_db:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )
    patient_data = Patient(
        id=patient_id,
        created_at=patients_db[patient_id].created_at,
        **patient.dict()
    )
    patients_db[patient_id] = patient_data
    return patient_data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)