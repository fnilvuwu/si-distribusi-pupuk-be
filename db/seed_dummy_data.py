"""
Seed script for dummy data: pengajuan pupuk, jadwal distribusi pupuk, stock pupuk, and related entities.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.db_base import SessionLocal
from db.models import ProfilePetani, StokPupuk, PermohonanPupuk, JadwalDistribusi, HasilTani
from datetime import datetime, timedelta, date

# Create a new database session
session = SessionLocal()

# Delete existing dummy data
session.query(JadwalDistribusi).delete()
session.query(PermohonanPupuk).delete()
session.query(StokPupuk).delete()
session.query(HasilTani).delete()
session.query(ProfilePetani).filter(ProfilePetani.nik.in_(["1234567890123456", "1234567890123457"])).delete(synchronize_session=False)
session.commit()

# Dummy petani
petanis = [
    ProfilePetani(
        user_id=101,
        nama_lengkap="Petani 1",
        nik="1234567890123456",
        alamat="Desa Suka Maju",
        no_hp="081234567892",
        url_ktp=None,
        url_kartu_tani=None,
        status_verifikasi=True
    ),
    ProfilePetani(
        user_id=102,
        nama_lengkap="Petani 2",
        nik="1234567890123457",
        alamat="Desa Suka Makmur",
        no_hp="081234567893",
        url_ktp=None,
        url_kartu_tani=None,
        status_verifikasi=True
    ),
]
session.add_all(petanis)
session.commit()

# Dummy stok pupuk
stok_list = [
    StokPupuk(nama_pupuk="Urea", jumlah_stok=1000, satuan="kg"),
    StokPupuk(nama_pupuk="NPK", jumlah_stok=800, satuan="kg"),
]
session.add_all(stok_list)
session.commit()

# Dummy pengajuan pupuk
permohonan_list = [
    PermohonanPupuk(
        petani_id=petanis[0].user_id,
        pupuk_id=stok_list[0].id,
        jumlah_diminta=200,
        jumlah_disetujui=180,
        status="selesai",
        alasan="Kebutuhan musim tanam",
        created_at=datetime.now()
    ),
    PermohonanPupuk(
        petani_id=petanis[1].user_id,
        pupuk_id=stok_list[1].id,
        jumlah_diminta=150,
        jumlah_disetujui=150,
        status="dijadwalkan",
        alasan="Kebutuhan musim tanam",
        created_at=datetime.now()
    ),
]
session.add_all(permohonan_list)
session.commit()

# Dummy jadwal distribusi pupuk
jadwal_list = [
    JadwalDistribusi(
        permohonan_id=permohonan_list[0].id,
        tanggal_pengiriman=date.today() + timedelta(days=3),
        lokasi="Gudang Desa Suka Maju",
        status="dijadwalkan"
    ),
    JadwalDistribusi(
        permohonan_id=permohonan_list[1].id,
        tanggal_pengiriman=date.today() + timedelta(days=5),
        lokasi="Gudang Desa Suka Makmur",
        status="dijadwalkan"
    ),
]
session.add_all(jadwal_list)
session.commit()

# Dummy hasil tani
hasil_tani_list = [
    HasilTani(
        petani_id=petanis[0].user_id,
        jenis_tanaman="Padi",
        jumlah_hasil=5000,
        satuan="kg",
        tanggal_panen=datetime.now().date(),
        created_at=datetime.now()
    ),
    HasilTani(
        petani_id=petanis[1].user_id,
        jenis_tanaman="Jagung",
        jumlah_hasil=3000,
        satuan="kg",
        tanggal_panen=datetime.now().date(),
        created_at=datetime.now()
    ),
]
session.add_all(hasil_tani_list)
session.commit()

print("Dummy data seeded successfully.")
session.close()
