import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy.orm import Session
from db.models import User, Base
from core.profile_utils import (
    create_or_update_profile_petani,
    create_or_update_profile_distributor,
    create_or_update_profile_admin,
    create_or_update_profile_superadmin
)
from sqlalchemy import create_engine
from passlib.hash import bcrypt

# Example SQLite engine, replace with your actual DB connection
engine = create_engine('sqlite:///./dev.db')
Base.metadata.create_all(bind=engine)

def seed_users_and_profiles(db: Session):
    # Petani
    petani_user = User(
        username="petani1",
        password_hash=bcrypt.hash("password123"),
        role="petani"
    )
    db.add(petani_user)
    db.commit()
    db.refresh(petani_user)
    create_or_update_profile_petani(
        db=db,
        user_id=petani_user.id,
        nama_lengkap="Petani Satu",
        nik="1234567890123456",
        alamat="Desa Makmur",
        no_hp="081234567890"
    )

    # Distributor
    distributor_user = User(
        username="distributor1",
        password_hash=bcrypt.hash("password123"),
        role="distributor"
    )
    db.add(distributor_user)
    db.commit()
    db.refresh(distributor_user)
    create_or_update_profile_distributor(
        db=db,
        user_id=distributor_user.id,
        nama_lengkap="Distributor Satu",
        perusahaan="PT Pupuk Jaya",
        alamat="Kota Industri",
        no_hp="081234567891"
    )

    # Admin
    admin_user = User(
        username="admin1",
        password_hash=bcrypt.hash("password123"),
        role="admin"
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    create_or_update_profile_admin(
        db=db,
        user_id=admin_user.id,
        nama_lengkap="Admin Satu",
        alamat="Kantor Pusat",
        no_hp="081234567892"
    )

    # Superadmin
    superadmin_user = User(
        username="superadmin1",
        password_hash=bcrypt.hash("password123"),
        role="super_admin"
    )
    db.add(superadmin_user)
    db.commit()
    db.refresh(superadmin_user)
    create_or_update_profile_superadmin(
        db=db,
        user_id=superadmin_user.id,
        nama_lengkap="Superadmin Satu",
        alamat="Kantor Pusat",
        no_hp="081234567893"
    )

if __name__ == "__main__":
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    seed_users_and_profiles(db)
    db.close()
