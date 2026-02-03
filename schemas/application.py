from pydantic import BaseModel

class ApplicationCreate(BaseModel):
    jenis_pupuk: str
    jumlah_kg: int
    alasan_pengajuan: str
    lokasi_penggunaan: str

class ProfilPetaniResponse(BaseModel):
    nama_lengkap: str
    nik: str
    alamat: str
    no_hp: str
    url_ktp: str | None = None
    url_kartu_tani: str | None = None
    status_verifikasi: bool
