from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import re

from core.security import create_access_token, hash_password, verify_password
from core.profile_utils import create_or_update_profile
from core.dependencies import get_current_user
from db.db_base import get_db
from db.models import User, ProfilePetani
from db.models import ProfilePetani
from schemas.auth import LoginResponse

router = APIRouter()


@router.post("/register_petani")
def register_petani(
    nama_lengkap: str = Form(...),
    nik: str = Form(...),
    alamat: str = Form(...),
    no_hp: str = Form(...),
    foto_ktp: UploadFile = File(...),
    foto_kartu_tani: UploadFile = File(None),
    password: str = Form(...),
    db: Session = Depends(get_db)
) -> dict:
    """
    Register a new user account with the petani role and profile.
    No authentication required - for new petani registration.
    """
    nik = nik.strip()
    if not re.fullmatch(r"\d{16}", nik):
        raise HTTPException(status_code=400, detail="NIK harus 16 digit")

    if not password:
        raise HTTPException(status_code=400, detail="password required")

    password_hash = hash_password(password)

    # Check if nik exists (NIK will be used as username)
    existing_nik = db.query(ProfilePetani).filter(ProfilePetani.nik == nik).first()
    if existing_nik:
        raise HTTPException(status_code=409, detail="NIK sudah terdaftar")

    # Check if username (NIK) already exists as a user
    existing_user = db.query(User).filter(User.username == nik).first()
    if existing_user:
        raise HTTPException(status_code=409, detail="User dengan NIK ini sudah terdaftar")

    # Create new user (use NIK as username)
    new_user = User(username=nik, password_hash=password_hash, role="petani")
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create profile (KTP required, Kartu Tani optional for registration)
    profile_result = create_or_update_profile(
        db, new_user.id, nama_lengkap, nik, alamat, no_hp, foto_ktp, foto_kartu_tani, 
        require_ktp=True, role="petani"
    )

    # Generate access token for immediate login
    access_token = create_access_token(data={"sub": str(new_user.id)})

    return {
        "status": "user_created_and_logged_in",
        "id": new_user.id, 
        "username": new_user.username, 
        "role": new_user.role, 
        "full_name": nama_lengkap,
        "access_token": access_token,
        **profile_result
    }


@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> LoginResponse:
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get full name if petani
    full_name = None
    if user.role == "petani" and user.profile_petani:
        full_name = user.profile_petani.nama_lengkap

    access_token = create_access_token(data={"sub": str(user.id)})
    return LoginResponse(access_token=access_token, role=user.role, full_name=full_name)


@router.post("/logout")
def logout(user=Depends(get_current_user)) -> dict:
    """
    Logout endpoint. Client should discard the token.
    """
    return {"message": "Logged out successfully"}
