import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.db_base import SessionLocal
from db.models import (
    User, ProfilePetani, ProfileDistributor, ProfileAdmin, ProfileSuperadmin,
    StokPupuk, PermohonanPupuk, JadwalDistribusiEvent
)

def verify():
    db = SessionLocal()
    try:
        print("=== USERS ===")
        users = db.query(User).all()
        for user in users:
            print(f"ID: {user.id}, Username: {user.username}, Role: {user.role}")
        print(f"Total Users: {len(users)}\n")

        print("=== PROFILES ===")
        print(f"Petani: {db.query(ProfilePetani).count()}")
        print(f"Distributor: {db.query(ProfileDistributor).count()}")
        print(f"Admin: {db.query(ProfileAdmin).count()}")
        print(f"Superadmin: {db.query(ProfileSuperadmin).count()}\n")

        print("=== FERTILIZERS ===")
        pupuks = db.query(StokPupuk).all()
        for p in pupuks:
            print(f"- {p.nama_pupuk}: {p.jumlah_stok} {p.satuan}")
        print(f"Total Types: {len(pupuks)}\n")

        print("=== DISTRIBUTION EVENTS ===")
        events = db.query(JadwalDistribusiEvent).all()
        for e in events:
            print(f"ID: {e.id}, Acara: {e.nama_acara}, Lokasi: {e.lokasi}")
        print(f"Total Events: {len(events)}\n")

        print("=== FERTILIZER REQUESTS ===")
        requests = db.query(PermohonanPupuk).all()
        for r in requests:
            event_info = f", Jadwal Event ID: {r.jadwal_event_id}" if r.jadwal_event_id else ""
            print(f"ID: {r.id}, Petani ID: {r.petani_id}, Status: {r.status}{event_info}")
        print(f"Total Requests: {len(requests)}\n")

    except Exception as e:
        print(f"Verification failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify()
