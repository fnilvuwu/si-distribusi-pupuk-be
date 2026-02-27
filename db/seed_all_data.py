"""
Comprehensive seeding script for all database tables.
Seeds all necessary dummy data: users, profiles, fertilizers, requests, schedules, etc.
Run this to populate the database with test data.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.db_base import SessionLocal, engine, Base
from db.models import (
    User, ProfilePetani, ProfileDistributor, ProfileAdmin, ProfileSuperadmin,
    StokPupuk, PermohonanPupuk, JadwalDistribusi, HasilTani, 
    JadwalDistribusiEvent, JadwalDistribusiItem, RiwayatStockPupuk,
    VerifikasiPenerimaPupuk
)
from core.security import hash_password
from datetime import datetime, timedelta, date

def seed_all_data():
    """Seed all dummy data to the database"""
    
    # Create tables first
    Base.metadata.create_all(bind=engine)

    # Create uploads directory if it doesn't exist
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        print(f"[OK] Created {upload_dir} directory")
    
    # Create dummy proof images
    dummy_files = ["bukti_pengiriman1.jpg", "bukti_pengiriman2.jpg"]
    for f in dummy_files:
        path = os.path.join(upload_dir, f)
        if not os.path.exists(path):
            with open(path, "w") as file:
                file.write("Dummy image content")
    print("[OK] Created dummy proof images")
    
    # Create a session
    session = SessionLocal()
    
    try:
        # Clear existing test data
        print("Clearing existing test data...")
        session.query(VerifikasiPenerimaPupuk).delete()
        session.query(JadwalDistribusiItem).delete()
        session.query(JadwalDistribusiEvent).delete()
        session.query(RiwayatStockPupuk).delete()
        session.query(JadwalDistribusi).delete()
        session.query(PermohonanPupuk).delete()
        session.query(HasilTani).delete()
        session.query(StokPupuk).delete()
        session.query(ProfileSuperadmin).delete()
        session.query(ProfileAdmin).delete()
        session.query(ProfileDistributor).delete()
        session.query(ProfilePetani).delete()
        session.query(User).delete()
        session.commit()
        print("[OK] Cleared existing data")
        
        # ========== USERS & PROFILES ==========
        print("\nSeeding users and profiles...")
        
        # Petani users
        petani_users = [
            User(username="petani001", password_hash=hash_password("password123"), role="petani"),
            User(username="petani002", password_hash=hash_password("password123"), role="petani"),
            User(username="petani003", password_hash=hash_password("password123"), role="petani"),
            User(username="petani004", password_hash=hash_password("password123"), role="petani"),
            User(username="petani005", password_hash=hash_password("password123"), role="petani"),
        ]
        session.add_all(petani_users)
        session.flush()
        
        # Distributor users
        distributor_users = [
            User(username="distributor001", password_hash=hash_password("password123"), role="distributor"),
            User(username="distributor002", password_hash=hash_password("password123"), role="distributor"),
        ]
        session.add_all(distributor_users)
        session.flush()
        
        # Admin user
        admin_user = User(username="admin001", password_hash=hash_password("password123"), role="admin")
        session.add(admin_user)
        session.flush()
        
        # Superadmin user
        superadmin_user = User(username="superadmin001", password_hash=hash_password("password123"), role="super_admin")
        session.add(superadmin_user)
        session.flush()
        
        session.commit()
        
        # Create petani profiles
        petani_profiles = [
            ProfilePetani(
                user_id=petani_users[0].id,
                nama_lengkap="Budi Santoso",
                nik="3201111234567890",
                alamat="Desa Suka Maju, RT 01 RW 02, Kabupaten Sleman",
                no_hp="081234567890",
                url_ktp="https://example.com/ktp/budi.jpg",
                url_kartu_tani="https://example.com/kartu/budi.jpg",
                status_verifikasi=True
            ),
            ProfilePetani(
                user_id=petani_users[1].id,
                nama_lengkap="Siti Nurhaliza",
                nik="3201111234567891",
                alamat="Desa Makmur Jaya, RT 03 RW 05, Kabupaten Sleman",
                no_hp="081234567891",
                url_ktp="https://example.com/ktp/siti.jpg",
                url_kartu_tani="https://example.com/kartu/siti.jpg",
                status_verifikasi=True
            ),
            ProfilePetani(
                user_id=petani_users[2].id,
                nama_lengkap="Gunawan Wijaya",
                nik="3201111234567892",
                alamat="Desa Maju Sejahtera, RT 02 RW 03, Kabupaten Sleman",
                no_hp="081234567892",
                url_ktp="https://example.com/ktp/gunawan.jpg",
                url_kartu_tani="https://example.com/kartu/gunawan.jpg",
                status_verifikasi=True
            ),
            ProfilePetani(
                user_id=petani_users[3].id,
                nama_lengkap="Rahayu Utami",
                nik="3201111234567893",
                alamat="Desa Harmoni Tani, RT 04 RW 01, Kabupaten Sleman",
                no_hp="081234567893",
                url_ktp=None,
                url_kartu_tani=None,
                status_verifikasi=False
            ),
            ProfilePetani(
                user_id=petani_users[4].id,
                nama_lengkap="Hendra Pratama",
                nik="3201111234567894",
                alamat="Desa Tani Subur, RT 05 RW 02, Kabupaten Sleman",
                no_hp="081234567894",
                url_ktp="https://example.com/ktp/hendra.jpg",
                url_kartu_tani=None,
                status_verifikasi=True
            ),
        ]
        session.add_all(petani_profiles)
        session.flush()
        
        # Create distributor profiles
        distributor_profiles = [
            ProfileDistributor(
                user_id=distributor_users[0].id,
                nama_lengkap="Anto Kuswoyo",
                perusahaan="PT Pupuk Indonesia Sejahtera",
                alamat="Jl. Industri No. 123, Sleman, Yogyakarta",
                no_hp="082234567890",
                status_verifikasi=True
            ),
            ProfileDistributor(
                user_id=distributor_users[1].id,
                nama_lengkap="Dewi Lestari",
                perusahaan="CV Tani Maju Bersama",
                alamat="Jl. Perdagangan No. 456, Sleman, Yogyakarta",
                no_hp="082234567891",
                status_verifikasi=True
            ),
        ]
        session.add_all(distributor_profiles)
        session.flush()
        
        # Create admin profile
        admin_profile = ProfileAdmin(
            user_id=admin_user.id,
            nama_lengkap="Yudi Pranoto",
            alamat="Jl. Kantor Desa No. 789, Sleman, Yogyakarta",
            no_hp="083234567890"
        )
        session.add(admin_profile)
        session.flush()
        
        # Create superadmin profile
        superadmin_profile = ProfileSuperadmin(
            user_id=superadmin_user.id,
            nama_lengkap="Bambang Sutrisno",
            alamat="Jl. Pusat Kota No. 999, Yogyakarta",
            no_hp="083234567899"
        )
        session.add(superadmin_profile)
        session.commit()
        print("[OK] Seeded 5 petani, 2 distributor, 1 admin, 1 superadmin")
        
        # ========== FERTILIZERS (STOK PUPUK) ==========
        print("\nSeeding fertilizers...")
        
        fertilizers = [
            StokPupuk(nama_pupuk="Urea", jumlah_stok=5000, satuan="kg"),
            StokPupuk(nama_pupuk="TSP (Triple Super Phosphate)", jumlah_stok=3000, satuan="kg"),
            StokPupuk(nama_pupuk="KCl (Potassium Chloride)", jumlah_stok=2500, satuan="kg"),
            StokPupuk(nama_pupuk="NPK 16:16:16", jumlah_stok=4000, satuan="kg"),
            StokPupuk(nama_pupuk="Pupuk Organik Kompos", jumlah_stok=6000, satuan="kg"),
            StokPupuk(nama_pupuk="Dolomit", jumlah_stok=2000, satuan="kg"),
        ]
        session.add_all(fertilizers)
        session.commit()
        print("[OK] Seeded 6 types of fertilizers")
        
        # ========== JADWAL DISTRIBUSI EVENT ==========
        print("\nSeeding distribution events...")
        
        events = [
            JadwalDistribusiEvent(
                nama_acara="Pembagian Pupuk Musim Tanam Musim Hujan",
                tanggal=date.today() + timedelta(days=10),
                lokasi="Lapangan Desa Suka Maju",
                status="dijadwalkan"
            ),
            JadwalDistribusiEvent(
                nama_acara="Pembagian Pupuk Berkualitas Tinggi untuk Petani",
                tanggal=date.today() + timedelta(days=20),
                lokasi="Balai Desa Makmur Jaya"
            ),
        ]
        session.add_all(events)
        session.flush()
        
        # Event items
        event_items = [
            JadwalDistribusiItem(
                event_id=events[0].id,
                pupuk_id=fertilizers[0].id,
                jumlah=1000,
                satuan="kg"
            ),
            JadwalDistribusiItem(
                event_id=events[0].id,
                pupuk_id=fertilizers[1].id,
                jumlah=500,
                satuan="kg"
            ),
            JadwalDistribusiItem(
                event_id=events[1].id,
                pupuk_id=fertilizers[3].id,
                jumlah=800,
                satuan="kg"
            ),
            JadwalDistribusiItem(
                event_id=events[1].id,
                pupuk_id=fertilizers[4].id,
                jumlah=600,
                satuan="kg"
            ),
        ]
        session.add_all(event_items)
        session.commit()
        print("[OK] Seeded 2 events with 4 items")

        # ========== PERMOHONAN PUPUK (REQUESTS) ==========
        print("\nSeeding fertilizer requests...")
        
        permohonan_list = [
            PermohonanPupuk(
                petani_id=petani_profiles[0].user_id,
                pupuk_id=fertilizers[0].id,
                jumlah_diminta=300,
                jumlah_disetujui=280,
                status="terverifikasi",
                alasan="Kebutuhan musim tanam padi",
                created_at=datetime.now(),
                jadwal_event_id=events[0].id
            ),
            PermohonanPupuk(
                petani_id=petani_profiles[1].user_id,
                pupuk_id=fertilizers[1].id,
                jumlah_diminta=200,
                jumlah_disetujui=200,
                status="dijadwalkan",
                alasan="Pemupukan lanjutan tanaman jagung",
                created_at=datetime.now(),
                jadwal_event_id=events[0].id
            ),
            PermohonanPupuk(
                petani_id=petani_profiles[2].user_id,
                pupuk_id=fertilizers[3].id,
                jumlah_diminta=250,
                jumlah_disetujui=250,
                status="dijadwalkan",
                alasan="Persiapan penanaman musim tanam",
                created_at=datetime.now(),
                jadwal_event_id=events[1].id
            ),
            PermohonanPupuk(
                petani_id=petani_profiles[3].user_id,
                pupuk_id=fertilizers[2].id,
                jumlah_diminta=150,
                jumlah_disetujui=None,
                status="pending",
                alasan="Kebutuhan mendesak untuk tanaman sayuran",
                created_at=datetime.now()
            ),
            PermohonanPupuk(
                petani_id=petani_profiles[4].user_id,
                pupuk_id=fertilizers[4].id,
                jumlah_diminta=500,
                jumlah_disetujui=450,
                status="dijadwalkan",
                alasan="Pemupukan organik untuk keberlanjutan",
                created_at=datetime.now(),
                jadwal_event_id=events[1].id
            ),
            PermohonanPupuk(
                petani_id=petani_profiles[0].user_id,
                pupuk_id=fertilizers[4].id,
                jumlah_diminta=100,
                jumlah_disetujui=100,
                status="selesai",
                alasan="Pemeliharaan tanaman",
                created_at=datetime.now() - timedelta(days=7)
            ),
        ]
        session.add_all(permohonan_list)
        session.commit()
        print("[OK] Seeded 6 fertilizer requests")
        
        # ========== JADWAL DISTRIBUSI (DISTRIBUTION SCHEDULES) ==========
        print("\nSeeding distribution schedules...")
        
        jadwal_list = [
            JadwalDistribusi(
                permohonan_id=permohonan_list[0].id,
                tanggal_pengiriman=date.today() + timedelta(days=3),
                lokasi="Gudang Desa Suka Maju, RT 01 RW 02",
                status="dijadwalkan"
            ),
            JadwalDistribusi(
                permohonan_id=permohonan_list[1].id,
                tanggal_pengiriman=date.today() + timedelta(days=5),
                lokasi="Gudang Desa Makmur Jaya, RT 03 RW 05",
                status="dijadwalkan"
            ),
            JadwalDistribusi(
                permohonan_id=permohonan_list[2].id,
                tanggal_pengiriman=date.today() + timedelta(days=2),
                lokasi="Gudang Desa Maju Sejahtera, RT 02 RW 03",
                status="dijadwalkan"
            ),
            JadwalDistribusi(
                permohonan_id=permohonan_list[4].id,
                tanggal_pengiriman=date.today() + timedelta(days=20),
                lokasi="Gudang Desa Tani Subur, RT 05 RW 02",
                status="dijadwalkan"
            ),
            JadwalDistribusi(
                permohonan_id=permohonan_list[5].id,
                tanggal_pengiriman=date.today() - timedelta(days=8),
                lokasi="Gudang Desa Suka Maju, RT 01 RW 02",
                status="selesai"
            ),
        ]
        session.add_all(jadwal_list)
        session.commit()
        print("[OK] Seeded 5 distribution schedules")
        
        # ========== RIWAYAT STOCK (STOCK HISTORY) ==========
        print("\nSeeding stock history...")
        
        riwayat_stock = [
            RiwayatStockPupuk(
                pupuk_id=fertilizers[0].id,
                tipe="tambah",
                jumlah=5000,
                satuan="kg",
                catatan="Stock awal dari gudang pusat",
                admin_user_id=admin_user.id,
                created_at=datetime.now() - timedelta(days=30)
            ),
            RiwayatStockPupuk(
                pupuk_id=fertilizers[0].id,
                tipe="kurangi",
                jumlah=280,
                satuan="kg",
                catatan="Penyerahan untuk Permohonan #1",
                admin_user_id=admin_user.id,
                created_at=datetime.now() - timedelta(days=2)
            ),
            RiwayatStockPupuk(
                pupuk_id=fertilizers[1].id,
                tipe="tambah",
                jumlah=3000,
                satuan="kg",
                catatan="Stock awal dari gudang pusat",
                admin_user_id=admin_user.id,
                created_at=datetime.now() - timedelta(days=30)
            ),
            RiwayatStockPupuk(
                pupuk_id=fertilizers[2].id,
                tipe="tambah",
                jumlah=2500,
                satuan="kg",
                catatan="Pembelian tambahan dari supplier",
                admin_user_id=admin_user.id,
                created_at=datetime.now() - timedelta(days=15)
            ),
        ]
        session.add_all(riwayat_stock)
        session.commit()
        print("[OK] Seeded 4 stock history records")
        
        # ========== HASIL TANI (HARVEST RECORDS) ==========
        print("\nSeeding harvest records...")
        
        hasil_tani_list = [
            HasilTani(
                petani_id=petani_profiles[0].user_id,
                jenis_tanaman="Padi",
                jumlah_hasil=5000,
                satuan="kg",
                tanggal_panen=date.today() - timedelta(days=30),
                created_at=datetime.now() - timedelta(days=30)
            ),
            HasilTani(
                petani_id=petani_profiles[1].user_id,
                jenis_tanaman="Jagung",
                jumlah_hasil=3500,
                satuan="kg",
                tanggal_panen=date.today() - timedelta(days=25),
                created_at=datetime.now() - timedelta(days=25)
            ),
            HasilTani(
                petani_id=petani_profiles[2].user_id,
                jenis_tanaman="Cabai",
                jumlah_hasil=800,
                satuan="kg",
                tanggal_panen=date.today() - timedelta(days=20),
                created_at=datetime.now() - timedelta(days=20)
            ),
            HasilTani(
                petani_id=petani_profiles[0].user_id,
                jenis_tanaman="Bawang Merah",
                jumlah_hasil=1200,
                satuan="kg",
                tanggal_panen=date.today() - timedelta(days=15),
                created_at=datetime.now() - timedelta(days=15)
            ),
            HasilTani(
                petani_id=petani_profiles[3].user_id,
                jenis_tanaman="Tomat",
                jumlah_hasil=600,
                satuan="kg",
                tanggal_panen=date.today() - timedelta(days=10),
                created_at=datetime.now() - timedelta(days=10)
            ),
            HasilTani(
                petani_id=petani_profiles[4].user_id,
                jenis_tanaman="Kentang",
                jumlah_hasil=2000,
                satuan="kg",
                tanggal_panen=date.today() - timedelta(days=5),
                created_at=datetime.now() - timedelta(days=5)
            ),
        ]
        session.add_all(hasil_tani_list)
        session.commit()
        print("[OK] Seeded 6 harvest records")
        

        
        # ========== VERIFIKASI PENERIMA PUPUK ==========
        print("\nSeeding recipient verification records...")
        
        verifikasi_list = [
            VerifikasiPenerimaPupuk(
                permohonan_id=permohonan_list[5].id,
                distributor_id=distributor_users[0].id,
                bukti_foto_url="uploads/bukti_pengiriman1.jpg",
                catatan="Pupuk diterima dalam kondisi baik oleh petani",
                tanggal_verifikasi=datetime.now() - timedelta(days=7)
            )
        ]
        session.add_all(verifikasi_list)
        session.commit()
        print("[OK] Seeded 1 verification records")
        
        # Print summary
        print("\n" + "="*60)
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY")
        print("="*60)
        print("[OK] Users created: 9")
        print("[OK] Fertilizer types: 6")
        print("[OK] Requests: 6")
        print("[OK] Distribution schedules: 5")
        print("[OK] Stock history: 4")
        print("[OK] Harvest records: 6")
        print("[OK] Events: 2")
        print("[OK] Verification records: 2")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] Error seeding data: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed_all_data()
