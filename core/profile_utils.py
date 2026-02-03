from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from db.models import ProfilePetani, ProfileDistributor, ProfileAdmin, ProfileSuperadmin
import logging

logger = logging.getLogger(__name__)


def create_or_update_profile_petani(
    db: Session,
    user_id: int,
    nama_lengkap: str,
    nik: str,
    alamat: str,
    no_hp: str,
    foto_ktp: UploadFile = None,
    foto_kartu_tani: UploadFile = None,
    require_ktp: bool = False
) -> dict:
    """
    Helper function to create or update ProfilePetani.
    If require_ktp=True, foto_ktp must be provided. foto_kartu_tani is always optional.
    Returns dict with urls.
    """
    from core.file_utils import save_upload_file

    if require_ktp and not foto_ktp:
        raise HTTPException(status_code=400, detail="KTP file is required")

    url_ktp = None
    if foto_ktp:
        try:
            url_ktp = save_upload_file(foto_ktp, "ktp")
        except Exception as e:
            logger.error(f"Error saving KTP file: {str(e)}")
            raise

    url_kartu_tani = None
    if foto_kartu_tani:
        try:
            url_kartu_tani = save_upload_file(foto_kartu_tani, "kartu_tani")
        except Exception as e:
            logger.error(f"Error saving kartu tani file: {str(e)}")
            raise

    existing_profile = db.query(ProfilePetani).filter(ProfilePetani.user_id == user_id).first()

    if existing_profile:
        existing_profile.nama_lengkap = nama_lengkap
        existing_profile.nik = nik
        existing_profile.alamat = alamat
        existing_profile.no_hp = no_hp
        if url_ktp:
            existing_profile.url_ktp = url_ktp
        if url_kartu_tani:
            existing_profile.url_kartu_tani = url_kartu_tani
    else:
        new_profile = ProfilePetani(
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            nik=nik,
            alamat=alamat,
            no_hp=no_hp,
            url_ktp=url_ktp,
            url_kartu_tani=url_kartu_tani,
            status_verifikasi=False
        )
        db.add(new_profile)

    db.commit()
    return {"url_ktp": url_ktp, "url_kartu_tani": url_kartu_tani}

def create_or_update_profile_distributor(
    db: Session,
    user_id: int,
    nama_lengkap: str,
    perusahaan: str,
    alamat: str,
    no_hp: str
) -> None:
    existing_profile = db.query(ProfileDistributor).filter(ProfileDistributor.user_id == user_id).first()
    if existing_profile:
        existing_profile.nama_lengkap = nama_lengkap
        existing_profile.perusahaan = perusahaan
        existing_profile.alamat = alamat
        existing_profile.no_hp = no_hp
    else:
        new_profile = ProfileDistributor(
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            perusahaan=perusahaan,
            alamat=alamat,
            no_hp=no_hp,
            status_verifikasi=False
        )
        db.add(new_profile)
    db.commit()

def create_or_update_profile_admin(
    db: Session,
    user_id: int,
    nama_lengkap: str,
    alamat: str,
    no_hp: str
) -> None:
    existing_profile = db.query(ProfileAdmin).filter(ProfileAdmin.user_id == user_id).first()
    if existing_profile:
        existing_profile.nama_lengkap = nama_lengkap
        existing_profile.alamat = alamat
        existing_profile.no_hp = no_hp
    else:
        new_profile = ProfileAdmin(
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            alamat=alamat,
            no_hp=no_hp
        )
        db.add(new_profile)
    db.commit()

def create_or_update_profile_superadmin(
    db: Session,
    user_id: int,
    nama_lengkap: str,
    alamat: str,
    no_hp: str
) -> None:
    existing_profile = db.query(ProfileSuperadmin).filter(ProfileSuperadmin.user_id == user_id).first()
    if existing_profile:
        existing_profile.nama_lengkap = nama_lengkap
        existing_profile.alamat = alamat
        existing_profile.no_hp = no_hp
    else:
        new_profile = ProfileSuperadmin(
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            alamat=alamat,
            no_hp=no_hp
        )
        db.add(new_profile)
    db.commit()

# --- Add wrapper function at top-level scope ---
def create_or_update_profile(
    db: Session,
    user_id: int,
    nama_lengkap: str,
    nik: str = None,
    alamat: str = None,
    no_hp: str = None,
    foto_ktp: UploadFile = None,
    foto_kartu_tani: UploadFile = None,
    require_ktp: bool = False,
    perusahaan: str = None,
    role: str = None
) -> dict:
    """
    Wrapper for creating or updating user profile based on role.
    Returns dict with urls for petani, None for others.
    
    Args:
        db: Database session
        user_id: User ID
        nama_lengkap: Full name
        nik: National ID (for petani)
        alamat: Address
        no_hp: Phone number
        foto_ktp: KTP file upload (optional)
        foto_kartu_tani: Kartu Tani file upload (optional)
        require_ktp: If True, KTP file is required for petani
        perusahaan: Company name (for distributor)
        role: User role ('petani', 'distributor', 'admin', 'superadmin')
    
    Returns:
        Dict with file URLs for petani, None for other roles
        
    Raises:
        HTTPException: If invalid role or missing required fields
    """
    if role == "petani":
        return create_or_update_profile_petani(
            db=db,
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            nik=nik,
            alamat=alamat,
            no_hp=no_hp,
            foto_ktp=foto_ktp,
            foto_kartu_tani=foto_kartu_tani,
            require_ktp=require_ktp
        )
    elif role == "distributor":
        create_or_update_profile_distributor(
            db=db,
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            perusahaan=perusahaan,
            alamat=alamat,
            no_hp=no_hp
        )
        return {}
    elif role == "admin":
        create_or_update_profile_admin(
            db=db,
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            alamat=alamat,
            no_hp=no_hp
        )
        return {}
    elif role == "superadmin":
        create_or_update_profile_superadmin(
            db=db,
            user_id=user_id,
            nama_lengkap=nama_lengkap,
            alamat=alamat,
            no_hp=no_hp
        )
        return {}
    else:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
