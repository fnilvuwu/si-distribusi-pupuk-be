import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import User, ProfilePetani, ProfileDistributor, ProfileAdmin, ProfileSuperadmin

engine = create_engine('sqlite:///./dev.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("Users:")
for user in db.query(User).all():
    print(f"ID: {user.id}, Username: {user.username}, Role: {user.role}")

print("\nPetani Profiles:")
for p in db.query(ProfilePetani).all():
    print(f"User ID: {p.user_id}, Nama: {p.nama_lengkap}, NIK: {p.nik}, Alamat: {p.alamat}, No HP: {p.no_hp}")

print("\nDistributor Profiles:")
for d in db.query(ProfileDistributor).all():
    print(f"User ID: {d.user_id}, Nama: {d.nama_lengkap}, Perusahaan: {d.perusahaan}, Alamat: {d.alamat}, No HP: {d.no_hp}")

print("\nAdmin Profiles:")
for a in db.query(ProfileAdmin).all():
    print(f"User ID: {a.user_id}, Nama: {a.nama_lengkap}, Alamat: {a.alamat}, No HP: {a.no_hp}")

print("\nSuperadmin Profiles:")
for s in db.query(ProfileSuperadmin).all():
    print(f"User ID: {s.user_id}, Nama: {s.nama_lengkap}, Alamat: {s.alamat}, No HP: {s.no_hp}")

db.close()
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import User, ProfilePetani, ProfileDistributor, ProfileAdmin, ProfileSuperadmin

engine = create_engine('sqlite:///./dev.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("Users:")
for user in db.query(User).all():
    print(f"ID: {user.id}, Username: {user.username}, Role: {user.role}")

print("\nPetani Profiles:")
for p in db.query(ProfilePetani).all():
    print(f"User ID: {p.user_id}, Nama: {p.nama_lengkap}, NIK: {p.nik}, Alamat: {p.alamat}, No HP: {p.no_hp}")

print("\nDistributor Profiles:")
for d in db.query(ProfileDistributor).all():
    print(f"User ID: {d.user_id}, Nama: {d.nama_lengkap}, Perusahaan: {d.perusahaan}, Alamat: {d.alamat}, No HP: {d.no_hp}")

print("\nAdmin Profiles:")
for a in db.query(ProfileAdmin).all():
    print(f"User ID: {a.user_id}, Nama: {a.nama_lengkap}, Alamat: {a.alamat}, No HP: {a.no_hp}")

print("\nSuperadmin Profiles:")
for s in db.query(ProfileSuperadmin).all():
    print(f"User ID: {s.user_id}, Nama: {s.nama_lengkap}, Alamat: {s.alamat}, No HP: {s.no_hp}")

db.close()
