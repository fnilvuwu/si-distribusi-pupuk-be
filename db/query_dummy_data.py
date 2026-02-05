"""
Query and print dummy data for petani, stok pupuk, pengajuan pupuk, and jadwal distribusi pupuk.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.db_base import SessionLocal
from db.models import ProfilePetani, StokPupuk, PermohonanPupuk, JadwalDistribusi, HasilTani

session = SessionLocal()

print("\n--- Petani ---")
for petani in session.query(ProfilePetani).all():
    print(f"ID: {petani.user_id}, Nama: {petani.nama_lengkap}, NIK: {petani.nik}, Alamat: {petani.alamat}, No HP: {petani.no_hp}")

print("\n--- Stok Pupuk ---")
for stok in session.query(StokPupuk).all():
    print(f"ID: {stok.id}, Nama: {stok.nama_pupuk}, Jumlah: {stok.jumlah_stok} {stok.satuan}")

print("\n--- Pengajuan Pupuk ---")
for permohonan in session.query(PermohonanPupuk).all():
    event_str = f", EventID: {permohonan.jadwal_event_id}" if permohonan.jadwal_event_id else ""
    print(f"ID: {permohonan.id}, Petani ID: {permohonan.petani_id}, Pupuk ID: {permohonan.pupuk_id}, Diminta: {permohonan.jumlah_diminta}, Disetujui: {permohonan.jumlah_disetujui}, Status: {permohonan.status}{event_str}")

print("\n--- Jadwal Distribusi Event ---")
# Import JadwalDistribusiEvent locally or at top if added
from db.models import JadwalDistribusiEvent
for event in session.query(JadwalDistribusiEvent).all():
    print(f"ID: {event.id}, Acara: {event.nama_acara}, Lokasi: {event.lokasi}, Tanggal: {event.tanggal}")

print("\n--- Jadwal Distribusi Pupuk ---")
for jadwal in session.query(JadwalDistribusi).all():
    print(f"ID: {jadwal.id}, Permohonan ID: {jadwal.permohonan_id}, Tanggal: {jadwal.tanggal_pengiriman}, Lokasi: {jadwal.lokasi}, Status: {jadwal.status}")

print("\n--- Hasil Tani ---")
for hasil in session.query(HasilTani).all():
    print(f"ID: {hasil.id}, Petani ID: {hasil.petani_id}, Jenis Tanaman: {hasil.jenis_tanaman}, Jumlah: {hasil.jumlah_hasil} {hasil.satuan}, Tanggal Panen: {hasil.tanggal_panen}")

session.close()
