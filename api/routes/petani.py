import os
import re
import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import Optional, List

from core.dependencies import require_role
from core.file_utils import save_upload_file
from db.db_base import get_cursor, get_transaction_cursor, get_db
from db.models import ProfilePetani, StokPupuk, PermohonanPupuk, HasilTani
from schemas.application import ProfilPetaniResponse
from core.profile_utils import create_or_update_profile

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/petani/profile", response_model=ProfilPetaniResponse)
def get_profil_petani(user=Depends(require_role("petani")), db: Session = Depends(get_db)) -> ProfilPetaniResponse:
    """Get current petani profile"""
    profil = db.query(ProfilePetani).filter(ProfilePetani.user_id == user["id"]).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Profil tidak ditemukan")
    return ProfilPetaniResponse(
        nama_lengkap=profil.nama_lengkap,
        nik=profil.nik,
        alamat=profil.alamat,
        no_hp=profil.no_hp,
        url_ktp=profil.url_ktp,
        url_kartu_tani=profil.url_kartu_tani,
        status_verifikasi=profil.status_verifikasi
    )


@router.post("/petani/profile/update")
def update_profile(
    nama_lengkap: str = Form(...),
    nik: str = Form(...),
    alamat: str = Form(...),
    no_hp: str = Form(...),
    foto_ktp: UploadFile = File(...),
    foto_kartu_tani: UploadFile = File(None),
    user=Depends(require_role("petani")),
    db: Session = Depends(get_db)
) -> dict:
    """
    Update existing user profile.
    Authentication required - for existing users to update their profile.
    """
    nik = nik.strip()
    if not re.fullmatch(r"\d{16}", nik):
        raise HTTPException(status_code=400, detail="NIK harus 16 digit")

    try:
        # Update profile (KTP required, Kartu Tani optional)
        profile_result = create_or_update_profile(
            db, user["id"], nama_lengkap, nik, alamat, no_hp, 
            foto_ktp, foto_kartu_tani, require_ktp=True, role="petani"
        )

        return {
            "status": "profile_updated",
            "user_id": user["id"],
            **(profile_result or {})
        }
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}")
        raise



@router.get("/petani/pupuk")
def list_pupuk(user=Depends(require_role("petani"))) -> list:
    """Get list of available fertilizers"""
    with get_cursor() as db:
        pupuk_list = db.query(StokPupuk).order_by(StokPupuk.nama_pupuk).all()
        return [
            {
                "id": p.id,
                "nama_pupuk": p.nama_pupuk,
                "jumlah_stok": p.jumlah_stok,
                "satuan": p.satuan
            }
            for p in pupuk_list
        ]


@router.post("/petani/pengajuan_pupuk")
def ajukan_permohonan(
    jenis_pupuk: str = Form(...),
    jumlah_kg: int = Form(...),
    alasan_pengajuan: str = Form(...),
    lokasi_penggunaan: str = Form(...),
    dokumen_pendukung: Optional[UploadFile] = File(None),
    user=Depends(require_role("petani")),
    db: Session = Depends(get_db)
) -> dict:
    """Submit fertilizer application"""
    
    if jumlah_kg <= 0:
        raise HTTPException(status_code=400, detail="jumlah_kg harus > 0")

    if not jenis_pupuk.strip():
        raise HTTPException(status_code=400, detail="jenis_pupuk wajib diisi")

    try:
        # Check if petani profile exists
        profil = db.query(ProfilePetani).filter(
            ProfilePetani.user_id == user["id"]
        ).first()
        
        if not profil:
            raise HTTPException(status_code=400, detail="Profil belum diisi")



        # Check if fertilizer exists
        pupuk = db.query(StokPupuk).filter(
            StokPupuk.nama_pupuk == jenis_pupuk.strip()
        ).first()
        
        if not pupuk:
            raise HTTPException(status_code=404, detail="Pupuk tidak ditemukan")

        # Handle optional supporting document upload
        url_dokumen_pendukung = None
        if dokumen_pendukung:
            try:
                url_dokumen_pendukung = save_upload_file(dokumen_pendukung, "pengajuan_pupuk")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"File upload error: {str(e)}")
                raise HTTPException(status_code=400, detail="Gagal mengunggah dokumen")

        # Create application
        permohonan = PermohonanPupuk(
            petani_id=user["id"],
            pupuk_id=pupuk.id,
            jumlah_diminta=jumlah_kg,
            status='pending',
            alasan=alasan_pengajuan.strip(),
            url_dokumen_pendukung=url_dokumen_pendukung
        )
        db.add(permohonan)
        db.commit()
        db.refresh(permohonan)

        return {
            "id": permohonan.id,
            "status": "pending",
            "created_at": permohonan.created_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error processing application")


@router.get("/petani/pengajuan_pupuk/riwayat")
def riwayat_permohonan(user=Depends(require_role("petani")), db: Session = Depends(get_db)) -> list:
    """Get application history"""
    permohonan_list = db.query(PermohonanPupuk).filter(
        PermohonanPupuk.petani_id == user["id"]
    ).order_by(PermohonanPupuk.created_at.desc()).limit(5).all()
    
    result = []
    for p in permohonan_list:
        pupuk = db.query(StokPupuk).filter(StokPupuk.id == p.pupuk_id).first()
        result.append({
            "id": p.id,
            "pupuk_id": p.pupuk_id,
            "nama_pupuk": pupuk.nama_pupuk if pupuk else None,
            "jumlah_diminta": p.jumlah_diminta,
            "jumlah_disetujui": p.jumlah_disetujui,
            "status": p.status,
            "created_at": p.created_at
        })
    return result


@router.patch("/petani/pengajuan_pupuk/{permohonan_id}/konfirmasi")
def konfirmasi_terima(
    permohonan_id: int,
    user=Depends(require_role("petani")),
    db: Session = Depends(get_db)
) -> dict:
    """Confirm fertilizer delivery receipt"""
    try:
        # Get application
        permohonan = db.query(PermohonanPupuk).filter(
            PermohonanPupuk.id == permohonan_id,
            PermohonanPupuk.petani_id == user["id"]
        ).first()
        
        if not permohonan:
            raise HTTPException(status_code=404, detail="Permohonan tidak ditemukan")
        
        if permohonan.status != "dikirim":
            raise HTTPException(
                status_code=400, 
                detail="Hanya permohonan dengan status 'dikirim' yang dapat dikonfirmasi"
            )

        # Update status to 'selesai'
        permohonan.status = 'selesai'
        
        # Decrement stok
        pupuk = db.query(StokPupuk).filter(StokPupuk.id == permohonan.pupuk_id).first()
        if pupuk:
            pupuk.jumlah_stok = max(0, pupuk.jumlah_stok - (permohonan.jumlah_disetujui or 0))
        
        db.commit()
        
        return {"status": "selesai", "permohonan_id": permohonan_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming delivery: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error processing confirmation")


@router.post("/petani/lapor_hasil_tani")
def lapor_hasil_tani(
    jenis_tanaman: str = Form(...),
    jumlah_hasil: int = Form(...),
    satuan: str = Form(...),
    tanggal_panen: date = Form(...),
    bukti_dokumen: Optional[UploadFile] = File(None),
    user=Depends(require_role("petani")),
    db: Session = Depends(get_db)
) -> dict:
    """Report harvest results"""
    
    if jumlah_hasil <= 0:
        raise HTTPException(status_code=400, detail="jumlah_hasil harus > 0")
    
    if not jenis_tanaman.strip():
        raise HTTPException(status_code=400, detail="jenis_tanaman wajib diisi")
    
    try:
        url_bukti_dokumen = None
        if bukti_dokumen:
            try:
                url_bukti_dokumen = save_upload_file(bukti_dokumen, "hasil_tani")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"File upload error: {str(e)}")
                raise HTTPException(status_code=400, detail="Gagal mengunggah dokumen bukti")

        hasil = HasilTani(
            petani_id=user["id"],
            jenis_tanaman=jenis_tanaman.strip(),
            jumlah_hasil=jumlah_hasil,
            satuan=satuan.strip(),
            tanggal_panen=tanggal_panen,
            bukti_url=url_bukti_dokumen
        )
        db.add(hasil)
        db.commit()
        db.refresh(hasil)
        
        return {
            "id": hasil.id,
            "status": "reported",
            "created_at": hasil.created_at,
            "bukti_url": hasil.bukti_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting harvest: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error processing harvest report")


@router.get("/petani/laporan_hasil_tani")
def list_laporan_hasil_tani(
    user=Depends(require_role("petani")),
    db: Session = Depends(get_db)
):
    """List laporan hasil tani for the current user."""
    reports = db.query(HasilTani).filter(HasilTani.petani_id == user["id"]).order_by(HasilTani.created_at.desc()).all()
    return reports



