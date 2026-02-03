from pydantic import BaseModel
from typing import Optional

class VerifikasiPetaniListResponse(BaseModel):
    user_id: int
    nama_lengkap: str
    nik: str
    status_verifikasi: bool
    created_at: str

class VerifikasiPetaniDetailResponse(BaseModel):
    user_id: int
    nama_lengkap: str
    nik: str
    alamat: str
    no_hp: str
    url_ktp: Optional[str]
    url_kartu_tani: Optional[str]
    status_verifikasi: bool
    created_at: str

class VerifikasiPetaniActionRequest(BaseModel):
    comment: Optional[str] = None
    reason: Optional[str] = None

class VerifikasiHasilTaniListResponse(BaseModel):
    id: int
    petani_id: int
    nama_lengkap: str
    jenis_tanaman: str
    jumlah_hasil: int
    satuan: str
    tanggal_panen: str
    status_verifikasi: bool
    created_at: str

class VerifikasiHasilTaniDetailResponse(BaseModel):
    id: int
    petani_id: int
    nama_lengkap: str
    jenis_tanaman: str
    jumlah_hasil: int
    satuan: str
    tanggal_panen: str
    status_verifikasi: bool
    created_at: str
    bukti_url: Optional[str]

class VerifikasiHasilTaniActionRequest(BaseModel):
    comment: Optional[str] = None
    reason: Optional[str] = None
