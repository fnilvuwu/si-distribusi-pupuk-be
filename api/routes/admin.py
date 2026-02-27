from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import text
from typing import List, Optional
from core.dependencies import require_role
from core.security import hash_password, verify_password
from db.db_base import get_cursor
from core.date_utils import (
    get_day_boundaries,
    get_month_boundaries,
    get_year_boundaries,
    format_date_for_api,
    extract_hour_from_datetime,
    extract_month_from_date,
    extract_date_from_datetime,
)
from schemas.verifikasi import (
    VerifikasiPetaniListResponse,
    VerifikasiPetaniDetailResponse,
    VerifikasiPetaniActionRequest,
    VerifikasiHasilTaniListResponse,
    VerifikasiHasilTaniDetailResponse,
    VerifikasiHasilTaniActionRequest,
)
from pydantic import BaseModel
import datetime

router = APIRouter()


class AdminProfileUpdate(BaseModel):
    nama_lengkap: Optional[str] = None
    alamat: Optional[str] = None
    no_hp: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    new_password_confirm: Optional[str] = None


@router.get("/profile", response_model=dict)
def get_admin_profile(user=Depends(require_role("admin"))):
    with get_cursor() as cur:
        cur.execute("""
            SELECT u.username, p.nama_lengkap, p.alamat, p.no_hp
            FROM users u
            LEFT JOIN profile_admin p ON p.user_id = u.id
            WHERE u.id = %s
        """, (user['id'],))
        row = cur.fetchone()
        # If profile doesn't exist yet, return basic info or empty stats
        if not row:
             return {"username": user['username'], "nama_lengkap": "", "alamat": "", "no_hp": ""}
        return dict(row)


@router.put("/profile", response_model=dict)
def update_admin_profile(req: AdminProfileUpdate, user=Depends(require_role("admin"))):
    with get_cursor(commit=True) as cur:
        # Handle Password Update
        if req.current_password:
            if not req.new_password or not req.new_password_confirm:
                raise HTTPException(status_code=400, detail="Password baru dan konfirmasi wajib diisi")
            if req.new_password != req.new_password_confirm:
                raise HTTPException(status_code=400, detail="Konfirmasi password baru tidak cocok")
            
            # Verify current password
            cur.execute("SELECT password_hash FROM users WHERE id = %s", (user['id'],))
            user_row = cur.fetchone()
            if not user_row:
                raise HTTPException(status_code=404, detail="User tidak ditemukan")
            
            if not verify_password(req.current_password, user_row['password_hash']):
                raise HTTPException(status_code=400, detail="Password saat ini salah")
            
            # Update password
            new_hash = hash_password(req.new_password)
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hash, user['id']))

        # Check if profile exists
        cur.execute("SELECT user_id FROM profile_admin WHERE user_id = %s", (user['id'],))
        exists = cur.fetchone()
        
        if not exists:
            # Create profile if not exists
            cur.execute(
                "INSERT INTO profile_admin (user_id, nama_lengkap, alamat, no_hp) VALUES (%s, %s, %s, %s)",
                (user['id'], req.nama_lengkap or "", req.alamat or "", req.no_hp or "")
            )
            # If creating, we might have updated password already, so just continue or return
            # But normally create logic would consume available fields.
            # We return "created" but if we updated password, maybe we should indicate that?
            # Let's keep it simple.
            return {"status": "created"}

        fields = []
        params = []
        if req.nama_lengkap is not None:
            fields.append("nama_lengkap = %s")
            params.append(req.nama_lengkap)
        if req.alamat is not None:
            fields.append("alamat = %s")
            params.append(req.alamat)
        if req.no_hp is not None:
             fields.append("no_hp = %s")
             params.append(req.no_hp)
        
        if fields:
             params.append(user['id'])
             sql = f"UPDATE profile_admin SET {', '.join(fields)} WHERE user_id = %s"
             cur.execute(sql, tuple(params))
        
        return {"status": "updated"}


@router.get("/verifikasi_petani", response_model=list[VerifikasiPetaniListResponse])
def list_verifikasi_petani(
    status: Optional[bool] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(require_role("admin")),
):
    offset = (page - 1) * page_size

    offset = (page - 1) * page_size
    filters = []
    params = []
    if status is not None:
        filters.append("status_verifikasi = %s")
        params.append(status)
    else:
        filters.append("status_verifikasi = false")
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    sql = f"""
        SELECT user_id, nama_lengkap, nik, status_verifikasi, '' AS created_at
        FROM profile_petani
        {where}
        ORDER BY user_id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    with get_cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        return [dict(row) for row in rows]


@router.get(
    "/verifikasi_petani/{petani_id}", response_model=VerifikasiPetaniDetailResponse
)
def detail_verifikasi_petani(petani_id: int, user=Depends(require_role("admin"))):
    sql = """
        SELECT user_id, nama_lengkap, nik, alamat, no_hp, url_ktp, url_kartu_tani, status_verifikasi, '' AS created_at
        FROM profile_petani WHERE user_id = %s
    """
    with get_cursor() as cur:
        cur.execute(sql, (petani_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Petani tidak ditemukan")
        return dict(row)


@router.post("/verifikasi_petani/{petani_id}/approve")
def approve_verifikasi_petani(
    petani_id: int,
    req: VerifikasiPetaniActionRequest,
    user=Depends(require_role("admin")),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT status_verifikasi FROM profile_petani WHERE user_id = %s",
            (petani_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Petani tidak ditemukan")
        if row["status_verifikasi"]:
            raise HTTPException(status_code=400, detail="Petani sudah diverifikasi")
        cur.execute(
            "UPDATE profile_petani SET status_verifikasi = TRUE WHERE user_id = %s",
            (petani_id,),
        )
        # Audit log placeholder: log who, when, comment
    return {"status": "approved", "comment": req.comment}


@router.post("/verifikasi_petani/{petani_id}/reject")
def reject_verifikasi_petani(
    petani_id: int,
    req: VerifikasiPetaniActionRequest,
    user=Depends(require_role("admin")),
):
    if not req.reason:
        raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi")
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT status_verifikasi FROM profile_petani WHERE user_id = %s",
            (petani_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Petani tidak ditemukan")
        if row["status_verifikasi"]:
            raise HTTPException(
                status_code=400, detail="Petani sudah diverifikasi, tidak bisa ditolak"
            )
        # Optionally, set a rejected status or log only
        # Audit log placeholder: log who, when, reason
    return {"status": "rejected", "reason": req.reason}


@router.get("/riwayat_verifikasi_petani", response_model=list[VerifikasiPetaniListResponse])
def riwayat_verifikasi_petani(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(require_role("admin")),
):
    offset = (page - 1) * page_size
    # Show history: status_verifikasi = TRUE (already processed/accepted)
    sql = """
        SELECT user_id, nama_lengkap, nik, status_verifikasi, '' AS created_at
        FROM profile_petani
        WHERE status_verifikasi = TRUE
        ORDER BY user_id DESC
        LIMIT %s OFFSET %s
    """
    params = [page_size, offset]
    with get_cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        return [dict(row) for row in rows]


@router.get(
    "/verifikasi_hasil_tani", response_model=list[VerifikasiHasilTaniListResponse]
)
def list_verifikasi_hasil_tani(
    status: Optional[bool] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(require_role("admin")),
):
    offset = (page - 1) * page_size
    filters = []
    params = []
    if status is not None:
        filters.append("ht.status_verifikasi = %s")
        params.append(status)
    if date_from:
        filters.append("ht.created_at >= %s")
        params.append(date_from)
    if date_to:
        filters.append("ht.created_at <= %s")
        params.append(date_to)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""

    # Database-agnostic query: retrieve raw datetime/date columns
    sql = f"""
        SELECT ht.id, ht.petani_id, p.nama_lengkap, ht.jenis_tanaman, ht.jumlah_hasil, ht.satuan, 
               ht.tanggal_panen, 
               ht.status_verifikasi, 
               ht.created_at
        FROM hasil_tani ht
        JOIN profile_petani p ON ht.petani_id = p.user_id
        {where}
        ORDER BY ht.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    with get_cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        # Format dates in Python for database-agnostic response
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict['tanggal_panen'] = format_date_for_api(row_dict['tanggal_panen'])
            row_dict['created_at'] = format_date_for_api(row_dict['created_at'])
            result.append(row_dict)
        return result


@router.get(
    "/verifikasi_hasil_tani/{laporan_id}",
    response_model=VerifikasiHasilTaniDetailResponse,
)
def detail_verifikasi_hasil_tani(laporan_id: int, user=Depends(require_role("admin"))):
    # Database-agnostic query
    sql = """
        SELECT ht.id, ht.petani_id, p.nama_lengkap, ht.jenis_tanaman, ht.jumlah_hasil, ht.satuan, 
               ht.tanggal_panen, 
               ht.status_verifikasi, 
               ht.created_at, 
               ht.bukti_url
        FROM hasil_tani ht
        JOIN profile_petani p ON ht.petani_id = p.user_id
        WHERE ht.id = %s
    """
    with get_cursor() as cur:
        cur.execute(sql, (laporan_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404, detail="Laporan hasil tani tidak ditemukan"
            )
        # Format dates in Python
        row_dict = dict(row)
        row_dict['tanggal_panen'] = format_date_for_api(row_dict['tanggal_panen'])
        row_dict['created_at'] = format_date_for_api(row_dict['created_at'])
        return row_dict


@router.post("/verifikasi_hasil_tani/{laporan_id}/approve")
def approve_verifikasi_hasil_tani(
    laporan_id: int,
    req: VerifikasiHasilTaniActionRequest,
    user=Depends(require_role("admin")),
):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT status_verifikasi FROM hasil_tani WHERE id = %s", (laporan_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404, detail="Laporan hasil tani tidak ditemukan"
            )
        if row["status_verifikasi"]:
            raise HTTPException(status_code=400, detail="Laporan sudah diverifikasi")
        cur.execute(
            "UPDATE hasil_tani SET status_verifikasi = TRUE WHERE id = %s",
            (laporan_id,),
        )
        # Audit log placeholder: log who, when, comment
    return {"status": "approved", "comment": req.comment}


@router.post("/verifikasi_hasil_tani/{laporan_id}/reject")
def reject_verifikasi_hasil_tani(
    laporan_id: int,
    req: VerifikasiHasilTaniActionRequest,
    user=Depends(require_role("admin")),
):
    if not req.reason:
        raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi")
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT status_verifikasi FROM hasil_tani WHERE id = %s", (laporan_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(
                status_code=404, detail="Laporan hasil tani tidak ditemukan"
            )
        if row["status_verifikasi"]:
            raise HTTPException(
                status_code=400, detail="Laporan sudah diverifikasi, tidak bisa ditolak"
            )
        # Optionally, set a rejected status or log only
        # Audit log placeholder: log who, when, reason
    return {"status": "rejected", "reason": req.reason}


@router.get("/riwayat_verifikasi_hasil_tani", response_model=list[VerifikasiHasilTaniListResponse])
def riwayat_verifikasi_hasil_tani(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(require_role("admin")),
):
    offset = (page - 1) * page_size
    filters = ["ht.status_verifikasi = TRUE"] # Only verified for history?
    params = []
    
    if date_from:
        filters.append("ht.created_at >= %s")
        params.append(date_from)
    if date_to:
        filters.append("ht.created_at <= %s")
        params.append(date_to)
        
    where = f"WHERE {' AND '.join(filters)}"

    # Database-agnostic query
    sql = f"""
        SELECT ht.id, ht.petani_id, p.nama_lengkap, ht.jenis_tanaman, ht.jumlah_hasil, ht.satuan, 
               ht.tanggal_panen, 
               ht.status_verifikasi, 
               ht.created_at
        FROM hasil_tani ht
        JOIN profile_petani p ON ht.petani_id = p.user_id
        {where}
        ORDER BY ht.created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    with get_cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        # Format dates in Python
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict['tanggal_panen'] = format_date_for_api(row_dict['tanggal_panen'])
            row_dict['created_at'] = format_date_for_api(row_dict['created_at'])
            result.append(row_dict)
        return result



# --- Persetujuan Pupuk (Fertilizer Approval) ---


class PermohonanPupukListResponse(BaseModel):
    id: int
    nama_petani: str
    nama_pupuk: str
    pupuk_id: int
    jumlah_diminta: int
    status: str
    created_at: str
    jadwal_id: Optional[int] = None


class PermohonanPupukActionRequest(BaseModel):
    jumlah_disetujui: int = None
    pupuk_id: int = None
    alasan: str = None
    tanggal_pengiriman: datetime.date = None
    lokasi: str = None
    tanggal_pengiriman: datetime.date = None
    lokasi: str = None
    jadwal_id: int = None


@router.get("/persetujuan_pupuk", response_model=List[PermohonanPupukListResponse])
def list_persetujuan_pupuk(user=Depends(require_role("admin"))):
    """List all pending fertilizer requests."""
    sql = """
        SELECT p.id, prof.nama_lengkap AS nama_petani, s.nama_pupuk, p.pupuk_id, p.jumlah_diminta, p.status, p.created_at,
               p.jadwal_event_id AS jadwal_id
        FROM pengajuan_pupuk p
        JOIN profile_petani prof ON p.petani_id = prof.user_id
        JOIN stok_pupuk s ON p.pupuk_id = s.id
        WHERE p.status = 'pending'
        ORDER BY p.created_at ASC
    """
    with get_cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        # Format dates in Python for database-agnostic response
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict['created_at'] = format_date_for_api(row_dict['created_at'])
            result.append(row_dict)
        return result


@router.get("/riwayat_persetujuan_pupuk", response_model=List[PermohonanPupukListResponse])
def riwayat_persetujuan_pupuk(user=Depends(require_role("admin"))):
    """List all processed fertilizer requests (history)."""
    sql = """
        SELECT p.id, prof.nama_lengkap AS nama_petani, s.nama_pupuk, p.pupuk_id, p.jumlah_diminta, p.status, p.created_at,
               p.jadwal_event_id AS jadwal_id
        FROM pengajuan_pupuk p
        JOIN profile_petani prof ON p.petani_id = prof.user_id
        JOIN stok_pupuk s ON p.pupuk_id = s.id
        WHERE p.status != 'pending'
        ORDER BY p.created_at DESC
    """
    with get_cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict['created_at'] = format_date_for_api(row_dict['created_at'])
            result.append(row_dict)
        return result


class StokPupuk(BaseModel):
    id: int
    nama_pupuk: str
    jumlah_stok: int
    satuan: str | None = None


@router.get("/pupuk_list", response_model=List[StokPupuk])
def list_stok_pupuk(user=Depends(require_role("admin"))):
    """List all fertilizer types with their current stock levels.
    
    Returns complete pupuk information including id, nama_pupuk, jumlah_stok, and satuan.
    This enables frontend to easily match pupuk_id from riwayat_stock_pupuk to pupuk records.
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT id, nama_pupuk, jumlah_stok, satuan 
            FROM stok_pupuk 
            ORDER BY nama_pupuk
        """)
        rows = cur.fetchall()
        return [dict(row) for row in rows]


class StokPupukCreate(BaseModel):
    nama_pupuk: str
    jumlah_stok: int = 0
    satuan: str


class StokPupukUpdate(BaseModel):
    nama_pupuk: Optional[str] = None
    jumlah_stok: Optional[int] = None
    satuan: Optional[str] = None


@router.post("/pupuk_list", response_model=StokPupuk)
def create_stok_pupuk(req: StokPupukCreate, user=Depends(require_role("admin"))):
    with get_cursor(commit=True) as cur:
        # Check duplicate name
        cur.execute("SELECT id FROM stok_pupuk WHERE nama_pupuk = %s", (req.nama_pupuk,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Nama pupuk sudah ada")
        
        cur.execute(
            """
            INSERT INTO stok_pupuk (nama_pupuk, jumlah_stok, satuan)
            VALUES (%s, %s, %s)
            """,
            (req.nama_pupuk, req.jumlah_stok, req.satuan),
        )
        new_id = cur.lastrowid
        if not new_id:
             # Fallback for some DB drivers if lastrowid not avail immediately
             cur.execute("SELECT id FROM stok_pupuk WHERE nama_pupuk = %s", (req.nama_pupuk,))
             new_id = cur.fetchone()["id"]
             
        return {
            "id": new_id,
            "nama_pupuk": req.nama_pupuk,
            "jumlah_stok": req.jumlah_stok,
            "satuan": req.satuan
        }


@router.put("/pupuk_list/{pupuk_id}", response_model=StokPupuk)
def update_stok_pupuk(pupuk_id: int, req: StokPupukUpdate, user=Depends(require_role("admin"))):
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT * FROM stok_pupuk WHERE id = %s", (pupuk_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Pupuk tidak ditemukan")
            
        fields = []
        values = []
        if req.nama_pupuk:
            # Check duplicate if name changing
            if req.nama_pupuk != existing["nama_pupuk"]:
                cur.execute("SELECT id FROM stok_pupuk WHERE nama_pupuk = %s", (req.nama_pupuk,))
                if cur.fetchone():
                    raise HTTPException(status_code=400, detail="Nama pupuk sudah digunakan")
            fields.append("nama_pupuk = %s")
            values.append(req.nama_pupuk)
        
        if req.jumlah_stok is not None:
             fields.append("jumlah_stok = %s")
             values.append(req.jumlah_stok)
             
        if req.satuan:
             fields.append("satuan = %s")
             values.append(req.satuan)
             
        if not fields:
             return existing
             
        values.append(pupuk_id)
        sql = f"UPDATE stok_pupuk SET {', '.join(fields)} WHERE id = %s"
        cur.execute(sql, tuple(values))
        
        # Return updated
        cur.execute("SELECT * FROM stok_pupuk WHERE id = %s", (pupuk_id,))
        return dict(cur.fetchone())


@router.delete("/pupuk_list/{pupuk_id}")
def delete_stok_pupuk(pupuk_id: int, user=Depends(require_role("admin"))):
    with get_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM stok_pupuk WHERE id = %s", (pupuk_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Pupuk tidak ditemukan")
            
        try:
            cur.execute("DELETE FROM stok_pupuk WHERE id = %s", (pupuk_id,))
        except Exception as e:
            # Likely foreign key constraint
            raise HTTPException(status_code=400, detail="Tidak dapat menghapus pupuk karena masih digunakan dalam data lain")
            
        return {"status": "deleted"}


@router.post("/persetujuan_pupuk/{permohonan_id}/approve")
def approve_persetujuan_pupuk(
    permohonan_id: int,
    req: PermohonanPupukActionRequest = Body(...),
    user=Depends(require_role("admin")),
):
    """Approve a fertilizer request with optional quantity/type adjustment."""
    if req.jumlah_disetujui is None or req.jumlah_disetujui <= 0:
        raise HTTPException(
            status_code=400, detail="Jumlah disetujui harus diisi dan > 0"
        )

    with get_cursor(commit=True) as cur:
        # Get current request details
        cur.execute(
            """
            SELECT p.status, p.jumlah_diminta, p.pupuk_id, s.jumlah_stok 
            FROM pengajuan_pupuk p
            JOIN stok_pupuk s ON s.id = p.pupuk_id
            WHERE p.id = %s
        """,
            (permohonan_id,),
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Permohonan tidak ditemukan")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail="Permohonan sudah diproses")

        # Determine target pupuk_id and check stock availability
        target_pupuk_id = row["pupuk_id"]
        available_stock = row["jumlah_stok"]

        if req.pupuk_id and req.pupuk_id != row["pupuk_id"]:
            target_pupuk_id = req.pupuk_id
            # Verify new pupuk exists
            cur.execute(
                "SELECT id, jumlah_stok FROM stok_pupuk WHERE id = %s",
                (target_pupuk_id,),
            )
            new_stok = cur.fetchone()
            if not new_stok:
                raise HTTPException(status_code=400, detail="Jenis pupuk tidak valid")
            available_stock = new_stok["jumlah_stok"]

        # Validation: Check if amount > available stock
        if req.jumlah_disetujui > available_stock:
            raise HTTPException(
                status_code=400,
                detail=f"Stok tidak mencukupi. Stok tersedia: {available_stock}, diminta disetujui: {req.jumlah_disetujui}",
            )

        # Validate jadwal_id if provided
        if req.jadwal_id:
             cur.execute("SELECT id FROM jadwal_distribusi_event WHERE id = %s", (req.jadwal_id,))
             if not cur.fetchone():
                 raise HTTPException(status_code=400, detail="Jadwal event tidak ditemukan")

        # Determine final status
        status_target = 'terverifikasi'
        if (req.tanggal_pengiriman and req.lokasi) or req.jadwal_id:
             status_target = 'dijadwalkan'

        # Update Query Builder
        update_fields = ["jumlah_disetujui = %s", "pupuk_id = %s", "status = %s"]
        update_values = [req.jumlah_disetujui, target_pupuk_id, status_target]

        if req.jadwal_id:
            update_fields.append("jadwal_event_id = %s")
            update_values.append(req.jadwal_id)

        update_values.append(permohonan_id)

        sql = f"UPDATE pengajuan_pupuk SET {', '.join(update_fields)} WHERE id = %s"
        cur.execute(sql, tuple(update_values))

        # Create JadwalDistribusi if applicable
        if req.tanggal_pengiriman and req.lokasi:
            cur.execute(
                """
                INSERT INTO jadwal_distribusi_pupuk (permohonan_id, tanggal_pengiriman, lokasi, status)
                VALUES (%s, %s, %s, 'dijadwalkan')
                """,
                (permohonan_id, req.tanggal_pengiriman, req.lokasi)
            )
        # Optionally, log approval reason
    return {
        "status": "approved",
        "jumlah_disetujui": req.jumlah_disetujui,
        "pupuk_id": target_pupuk_id,
    }


@router.post("/persetujuan_pupuk/{permohonan_id}/reject")
def reject_persetujuan_pupuk(
    permohonan_id: int,
    req: PermohonanPupukActionRequest = Body(...),
    user=Depends(require_role("admin")),
):
    """Reject a fertilizer request."""
    if not req.alasan:
        raise HTTPException(status_code=400, detail="Alasan penolakan wajib diisi")
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT status FROM pengajuan_pupuk WHERE id = %s", (permohonan_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Permohonan tidak ditemukan")
        if row["status"] != "pending":
            raise HTTPException(status_code=400, detail="Permohonan sudah diproses")
        cur.execute(
            "UPDATE pengajuan_pupuk SET status = 'ditolak', alasan_pengajuan = %s WHERE id = %s",
            (req.alasan, permohonan_id),
        )
        # Optionally, log rejection reason
    return {"status": "rejected", "alasan": req.alasan}


# --- Jadwal Distribusi (Event-based Scheduling) ---


class JadwalPupukItem(BaseModel):
    pupuk_id: int
    jumlah: int
    satuan: str


class BuatJadwalDistribusiRequest(BaseModel):
    nama_acara: str
    tanggal: datetime.date
    lokasi: str
    items: List[JadwalPupukItem]


class BuatJadwalDistribusiResponse(BaseModel):
    id: int
    nama_acara: str
    tanggal: datetime.date
    lokasi: str
    status: str
    created_at: str
    items: List[JadwalPupukItem]


@router.post(
    "/buat_jadwal_distribusi_pupuk", response_model=BuatJadwalDistribusiResponse
)
def buat_jadwal_distribusi_pupuk(
    req: BuatJadwalDistribusiRequest,
    user=Depends(require_role("admin")),
):
    """Buat event jadwal distribusi pupuk (nama acara, tanggal, lokasi) beserta detail pupuk."""
    if not req.items or len(req.items) == 0:
        raise HTTPException(status_code=400, detail="Detail pupuk wajib diisi")
    # Basic validation
    for it in req.items:
        if it.jumlah <= 0:
            raise HTTPException(status_code=400, detail="Jumlah pupuk harus > 0")
        if not it.satuan:
            raise HTTPException(status_code=400, detail="Satuan pupuk wajib diisi")

    with get_cursor(commit=True) as cur:
        # Validate pupuk IDs exist and optionally enforce satuan consistency
        cur.execute("SELECT id, satuan FROM stok_pupuk")
        stok_map = {row["id"]: row["satuan"] for row in cur.fetchall()}
        for it in req.items:
            if it.pupuk_id not in stok_map:
                raise HTTPException(
                    status_code=400, detail=f"Pupuk id {it.pupuk_id} tidak ditemukan"
                )
            # If FE provides satuan, ensure matches stok
            if stok_map[it.pupuk_id] and it.satuan != stok_map[it.pupuk_id]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Satuan tidak sesuai untuk pupuk id {it.pupuk_id}",
                )

        # Insert event with RETURNING to get created_at
        cur.execute(
            """
            INSERT INTO jadwal_distribusi_event (nama_acara, tanggal, lokasi, status)
            VALUES (%s, %s, %s, 'dijadwalkan')
            RETURNING id, created_at, status
            """,
            (req.nama_acara, req.tanggal, req.lokasi),
        )
        row = cur.fetchone()
        event_id = row["id"]
        created_at = row["created_at"]
        status = row["status"]

        # Insert items
        for it in req.items:
            cur.execute(
                """
                INSERT INTO jadwal_distribusi_item (event_id, pupuk_id, jumlah, satuan)
                VALUES (%s, %s, %s, %s)
                """,
                (event_id, it.pupuk_id, it.jumlah, it.satuan),
            )

    return {
        "id": event_id,
        "nama_acara": req.nama_acara,
        "tanggal": req.tanggal,
        "lokasi": req.lokasi,
        "status": status,
        "created_at": format_date_for_api(created_at),
        "items": req.items,
    }


class AcaraDistribusiItemResponse(BaseModel):
    pupuk_id: int
    nama_pupuk: str | None = None
    jumlah: int
    satuan: str


class AcaraDistribusiResponse(BaseModel):
    id: int
    nama_acara: str
    tanggal: datetime.date
    lokasi: str
    status: str
    created_at: str
    items: List[AcaraDistribusiItemResponse]


@router.get(
    "/jadwal_distribusi_pupuk",
    response_model=List[AcaraDistribusiResponse],
)
def list_jadwal_distribusi_pupuk(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(require_role("admin")),
):
    """List semua acara distribusi pupuk beserta itemnya (paged)."""
    offset = (page - 1) * page_size
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, nama_acara, tanggal, lokasi, status, created_at
            FROM jadwal_distribusi_event
            ORDER BY tanggal DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (page_size, offset),
        )
        events = [dict(r) for r in cur.fetchall()]

        result: List[dict] = []
        for ev in events:
            cur.execute(
                """
                SELECT i.pupuk_id, s.nama_pupuk, i.jumlah, i.satuan
                FROM jadwal_distribusi_item i
                JOIN stok_pupuk s ON s.id = i.pupuk_id
                WHERE i.event_id = %s
                ORDER BY i.id ASC
                """,
                (ev["id"],),
            )
            items = [
                {
                    "pupuk_id": row["pupuk_id"],
                    "nama_pupuk": row["nama_pupuk"],
                    "jumlah": row["jumlah"],
                    "satuan": row["satuan"],
                }
                for row in cur.fetchall()
            ]
            result.append(
                {
                    "id": ev["id"],
                    "nama_acara": ev["nama_acara"],
                    "tanggal": ev["tanggal"],
                    "lokasi": ev["lokasi"],
                    "status": ev["status"],
                    "created_at": format_date_for_api(ev["created_at"]),
                    "items": items,
                }
            )
    return result


@router.get(
    "/jadwal_distribusi_pupuk/{jadwal_id}",
    response_model=AcaraDistribusiResponse,
)
def detail_jadwal_distribusi_pupuk(
    jadwal_id: int,
    user=Depends(require_role("admin")),
):
    """Detail satu acara distribusi pupuk dengan itemnya."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, nama_acara, tanggal, lokasi, status, created_at FROM jadwal_distribusi_event WHERE id = %s",
            (jadwal_id,),
        )
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(
                status_code=404, detail="Jadwal distribusi tidak ditemukan"
            )

        cur.execute(
            """
            SELECT i.pupuk_id, s.nama_pupuk, i.jumlah, i.satuan
            FROM jadwal_distribusi_item i
            JOIN stok_pupuk s ON s.id = i.pupuk_id
            WHERE i.event_id = %s
            ORDER BY i.id ASC
            """,
            (jadwal_id,),
        )
        items = [
            {
                "pupuk_id": row["pupuk_id"],
                "nama_pupuk": row["nama_pupuk"],
                "jumlah": row["jumlah"],
                "satuan": row["satuan"],
            }
            for row in cur.fetchall()
        ]
        return {
            "id": ev["id"],
            "nama_acara": ev["nama_acara"],
            "tanggal": ev["tanggal"],
            "lokasi": ev["lokasi"],
            "status": ev["status"],
            "created_at": format_date_for_api(ev["created_at"]),
            "items": items,
        }

@router.patch("/jadwal_distribusi_pupuk/{jadwal_id}/selesai")
def selesaikan_jadwal_distribusi_pupuk(
    jadwal_id: int,
    user=Depends(require_role("admin")),
):
    """Selesaikan acara distribusi pupuk."""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, status FROM jadwal_distribusi_event WHERE id = %s",
            (jadwal_id,),
        )
        ev = cur.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Jadwal distribusi tidak ditemukan")
        if ev["status"] == "selesai":
            raise HTTPException(status_code=400, detail="Jadwal distribusi sudah selesai")

        cur.execute(
            "UPDATE jadwal_distribusi_event SET status = 'selesai' WHERE id = %s",
            (jadwal_id,),
        )
        
        # Also could update related pengajuan_pupuk status if needed, but not specified
        return {"status": "success", "message": "Jadwal distribusi berhasil diselesaikan"}

@router.get("/jadwal_distribusi_pupuk/{jadwal_id}/penerima")
def daftar_penerima_pupuk_event(
    jadwal_id: int,
    user=Depends(require_role("admin")),
):
    """Melihat daftar penerima pupuk di suatu event."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT id FROM jadwal_distribusi_event WHERE id = %s",
            (jadwal_id,),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Jadwal distribusi tidak ditemukan")

        cur.execute(
            """
            SELECT p.id as permohonan_id, prof.nama_lengkap AS nama_petani, 
                   s.nama_pupuk, p.jumlah_disetujui, p.status
            FROM pengajuan_pupuk p
            JOIN profile_petani prof ON p.petani_id = prof.user_id
            JOIN stok_pupuk s ON p.pupuk_id = s.id
            WHERE p.jadwal_event_id = %s
            ORDER BY prof.nama_lengkap ASC
            """,
            (jadwal_id,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]


@router.get("/list_event_jadwal_pengambilan_pupuk", response_model=List[AcaraDistribusiResponse])
def list_event_jadwal_pengambilan_pupuk(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(require_role("admin")),
):
    """Alias/Same as jadwal_distribusi_pupuk but usually for selection."""
    return list_jadwal_distribusi_pupuk(page=page, page_size=page_size, user=user)



# --- Stok Pupuk (Stock Management) ---


class StockChangeRequest(BaseModel):
    pupuk_id: int
    jumlah: int
    satuan: str
    catatan: str | None = None


class StockHistoryItem(BaseModel):
    id: int
    pupuk_id: int
    nama_pupuk: str
    tipe: str
    jumlah: int
    satuan: str
    catatan: str | None = None
    created_at: datetime.datetime


@router.get("/riwayat_stock_pupuk", response_model=List[StockHistoryItem])
def riwayat_stock_pupuk(
    pupuk_id: int | None = Query(None),
    tipe: str | None = Query(None, description="Filter tipe: tambah/kurangi"),
    created_from: str | None = Query(None, description="YYYY-MM-DD"),
    created_to: str | None = Query(None, description="YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user=Depends(require_role("admin")),
):
    offset = (page - 1) * page_size
    filters: list[str] = []
    params: list = []
    if pupuk_id is not None:
        filters.append("r.pupuk_id = %s")
        params.append(pupuk_id)
    if tipe in {"tambah", "kurangi"}:
        filters.append("r.tipe = %s")
        params.append(tipe)
    if created_from:
        filters.append("DATE(r.created_at) >= %s")
        params.append(created_from)
    if created_to:
        filters.append("DATE(r.created_at) <= %s")
        params.append(created_to)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    sql = f"""
        SELECT r.id, r.pupuk_id, s.nama_pupuk, r.tipe, r.jumlah, r.satuan, r.catatan, r.created_at
        FROM riwayat_stock_pupuk r
        JOIN stok_pupuk s ON s.id = r.pupuk_id
        {where}
        ORDER BY r.created_at DESC, r.id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    with get_cursor() as cur:
        cur.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


@router.post("/tambah_stock_pupuk")
def tambah_stock_pupuk(req: StockChangeRequest, user=Depends(require_role("admin"))):
    if req.jumlah <= 0:
        raise HTTPException(status_code=400, detail="Jumlah harus > 0")
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, jumlah_stok, satuan FROM stok_pupuk WHERE id = %s",
            (req.pupuk_id,),
        )
        stok = cur.fetchone()
        if not stok:
            raise HTTPException(status_code=404, detail="Pupuk tidak ditemukan")
        if stok["satuan"] and stok["satuan"] != req.satuan:
            raise HTTPException(
                status_code=400, detail="Satuan tidak sesuai dengan stok"
            )

        cur.execute(
            "UPDATE stok_pupuk SET jumlah_stok = jumlah_stok + %s WHERE id = %s",
            (req.jumlah, req.pupuk_id),
        )
        cur.execute(
            """
            INSERT INTO riwayat_stock_pupuk (pupuk_id, tipe, jumlah, satuan, catatan, admin_user_id)
            VALUES (%s, 'tambah', %s, %s, %s, %s)
            """,
            (req.pupuk_id, req.jumlah, req.satuan, req.catatan, None),
        )
    return {"status": "ok"}


@router.post("/kurangi_stock_pupuk")
def kurangi_stock_pupuk(req: StockChangeRequest, user=Depends(require_role("admin"))):
    if req.jumlah <= 0:
        raise HTTPException(status_code=400, detail="Jumlah harus > 0")
    with get_cursor(commit=True) as cur:
        cur.execute(
            "SELECT id, jumlah_stok, satuan FROM stok_pupuk WHERE id = %s",
            (req.pupuk_id,),
        )
        stok = cur.fetchone()
        if not stok:
            raise HTTPException(status_code=404, detail="Pupuk tidak ditemukan")
        if stok["satuan"] and stok["satuan"] != req.satuan:
            raise HTTPException(
                status_code=400, detail="Satuan tidak sesuai dengan stok"
            )
        if stok["jumlah_stok"] < req.jumlah:
            raise HTTPException(
                status_code=400, detail="Jumlah pengurangan melebihi stok tersedia"
            )

        cur.execute(
            "UPDATE stok_pupuk SET jumlah_stok = jumlah_stok - %s WHERE id = %s",
            (req.jumlah, req.pupuk_id),
        )
        cur.execute(
            """
            INSERT INTO riwayat_stock_pupuk (pupuk_id, tipe, jumlah, satuan, catatan, admin_user_id)
            VALUES (%s, 'kurangi', %s, %s, %s, %s)
            """,
            (req.pupuk_id, req.jumlah, req.satuan, req.catatan, None),
        )
    return {"status": "ok"}


# --- Laporan Rekap ---


class RekapHarianRow(BaseModel):
    jam: int
    by_pupuk: dict[str, int]
    penerima: int | None = None
    status: str | None = None


class LaporanRekapHarian(BaseModel):
    tanggal: datetime.date
    total_penyaluran_kg: int
    penerima_manfaat: int
    permohonan_aktif: int
    wilayah_terbanyak: str | None
    rekapitulasi: List[RekapHarianRow]


@router.get(
    "/laporan_rekap_harian",
    response_model=LaporanRekapHarian,
    summary="Laporan rekap harian distribusi pupuk",
    description="Ringkasan harian: total penyaluran (Kg), penerima manfaat, permohonan aktif, wilayah terbanyak, dan rekap per jam berdasarkan riwayat pengurangan stok.",
)
def laporan_rekap_harian(
    tanggal: datetime.date = Query(...),
    user=Depends(require_role("admin")),
):
    with get_cursor() as cur:
        # total penyaluran from stock reductions (kurangi) on the given date
        cur.execute(
            """
            SELECT COALESCE(SUM(jumlah),0) AS total
            FROM riwayat_stock_pupuk
            WHERE tipe='kurangi' AND created_at >= %s AND created_at < %s AND lower(satuan) = 'kg'
            """,
            (tanggal, tanggal + datetime.timedelta(days=1)),
        )
        total_penyaluran_kg = int(cur.fetchone()["total"] or 0)

        # penerima manfaat (approx): verified petani count
        cur.execute(
            "SELECT COUNT(*) AS c FROM profile_petani WHERE status_verifikasi = TRUE"
        )
        penerima_manfaat = int(cur.fetchone()["c"])

        # permohonan aktif: pending/terverifikasi/dijadwalkan
        cur.execute(
            """
            SELECT COUNT(*) AS c
            FROM pengajuan_pupuk
            WHERE status IN ('pending','terverifikasi','dijadwalkan')
            """
        )
        permohonan_aktif = int(cur.fetchone()["c"])

        # wilayah terbanyak: most frequent lokasi in jadwal on the date
        cur.execute(
            """
            SELECT lokasi, COUNT(*) AS c
            FROM jadwal_distribusi_event
            WHERE tanggal = %s
            GROUP BY lokasi
            ORDER BY c DESC
            LIMIT 1
            """,
            (tanggal,),
        )
        row = cur.fetchone()
        wilayah_terbanyak = row["lokasi"] if row else None

        # rekap per hour using stock history - retrieve all records and group in Python
        cur.execute(
            """
            SELECT r.created_at, s.nama_pupuk, r.jumlah
            FROM riwayat_stock_pupuk r
            JOIN stok_pupuk s ON s.id = r.pupuk_id
            WHERE r.tipe='kurangi' AND r.created_at >= %s AND r.created_at < %s AND lower(r.satuan) = 'kg'
            ORDER BY r.created_at
            """,
            (tanggal, tanggal + datetime.timedelta(days=1)),
        )
        by_hour: dict[int, dict[str, int]] = {}
        for rec in cur.fetchall():
            # Extract hour in Python instead of SQL
            jam = extract_hour_from_datetime(rec["created_at"])
            if jam is not None:
                by_hour.setdefault(jam, {})
                by_hour[jam][rec["nama_pupuk"]] = by_hour[jam].get(rec["nama_pupuk"], 0) + int(rec["jumlah"])

        rekapitulasi = [
            RekapHarianRow(jam=jam, by_pupuk=vals, penerima=None, status="OPTIMAL")
            for jam, vals in sorted(by_hour.items())
        ]

    return LaporanRekapHarian(
        tanggal=tanggal,
        total_penyaluran_kg=total_penyaluran_kg,
        penerima_manfaat=penerima_manfaat,
        permohonan_aktif=permohonan_aktif,
        wilayah_terbanyak=wilayah_terbanyak,
        rekapitulasi=rekapitulasi,
    )


class RekapAggregatedRow(BaseModel):
    tanggal: datetime.date
    by_pupuk: dict[str, int]


class LaporanRekapBulanan(BaseModel):
    tahun: int
    bulan: int
    total_penyaluran_kg: int
    rekap_per_hari: List[RekapAggregatedRow]


@router.get(
    "/laporan_rekap_bulanan",
    response_model=LaporanRekapBulanan,
    summary="Laporan rekap bulanan distribusi pupuk",
    description="Ringkasan bulanan: total penyaluran (Kg) dan rekap per hari per jenis pupuk berdasarkan riwayat pengurangan stok.",
)
def laporan_rekap_bulanan(
    tahun: int = Query(..., ge=2000),
    bulan: int = Query(..., ge=1, le=12),
    user=Depends(require_role("admin")),
):
    # Use Python date boundaries
    start_date, end_date = get_month_boundaries(tahun, bulan)
    
    with get_cursor() as cur:
        # total penyaluran for month
        cur.execute(
            """
            SELECT COALESCE(SUM(jumlah),0) AS total
            FROM riwayat_stock_pupuk
            WHERE tipe='kurangi' AND created_at >= %s AND created_at < %s AND lower(satuan)='kg'
            """,
            (start_date, end_date),
        )
        total_penyaluran_kg = int(cur.fetchone()["total"] or 0)

        # per-day per-pupuk totals
        cur.execute(
            """
            SELECT r.created_at, s.nama_pupuk, r.jumlah
            FROM riwayat_stock_pupuk r
            JOIN stok_pupuk s ON s.id = r.pupuk_id
            WHERE r.tipe='kurangi' AND r.created_at >= %s AND r.created_at < %s AND lower(r.satuan)='kg'
            ORDER BY r.created_at
            """,
            (start_date, end_date),
        )
        by_day: dict[datetime.date, dict[str, int]] = {}
        for rec in cur.fetchall():
            # Extract date in Python
            tgl = extract_date_from_datetime(rec["created_at"])
            if tgl:
                by_day.setdefault(tgl, {})
                by_day[tgl][rec["nama_pupuk"]] = by_day[tgl].get(rec["nama_pupuk"], 0) + int(rec["jumlah"])
        
        rekap_per_hari = [
            RekapAggregatedRow(tanggal=t, by_pupuk=vals)
            for t, vals in sorted(by_day.items())
        ]

    return LaporanRekapBulanan(
        tahun=tahun,
        bulan=bulan,
        total_penyaluran_kg=total_penyaluran_kg,
        rekap_per_hari=rekap_per_hari,
    )


class LaporanRekapTahunan(BaseModel):
    tahun: int
    total_penyaluran_kg: int
    rekap_per_bulan: List[dict]


@router.get(
    "/laporan_rekap_tahunan",
    response_model=LaporanRekapTahunan,
    summary="Laporan rekap tahunan distribusi pupuk",
    description="Ringkasan tahunan: total penyaluran (Kg) dan rekap per bulan per jenis pupuk berdasarkan riwayat pengurangan stok.",
)
def laporan_rekap_tahunan(
    tahun: int = Query(..., ge=2000),
    user=Depends(require_role("admin")),
):
    # Use Python date boundaries
    start_date, end_date = get_year_boundaries(tahun)
    
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(jumlah),0) AS total
            FROM riwayat_stock_pupuk
            WHERE tipe='kurangi' AND created_at >= %s AND created_at < %s AND lower(satuan)='kg'
            """,
            (start_date, end_date),
        )
        total_penyaluran_kg = int(cur.fetchone()["total"] or 0)

        cur.execute(
            """
            SELECT r.created_at, s.nama_pupuk, r.jumlah
            FROM riwayat_stock_pupuk r
            JOIN stok_pupuk s ON s.id = r.pupuk_id
            WHERE r.tipe='kurangi' AND r.created_at >= %s AND r.created_at < %s AND lower(r.satuan)='kg'
            ORDER BY r.created_at
            """,
            (start_date, end_date),
        )
        month_map: dict[int, dict[str, int]] = {}
        for rec in cur.fetchall():
            # Extract month in Python
            bln = extract_month_from_date(rec["created_at"])
            if bln:
                month_map.setdefault(bln, {})
                month_map[bln][rec["nama_pupuk"]] = month_map[bln].get(rec["nama_pupuk"], 0) + int(rec["jumlah"])
        
        rekap_per_bulan = [
            {"bulan": bln, "by_pupuk": vals} for bln, vals in sorted(month_map.items())
        ]

    return LaporanRekapTahunan(
        tahun=tahun,
        total_penyaluran_kg=total_penyaluran_kg,
        rekap_per_bulan=rekap_per_bulan,
    )


@router.get(
    "/download_laporan_rekap",
    summary="Unduh CSV laporan rekap",
    description="Unduh laporan rekap dalam format CSV untuk harian/bulanan/tahunan berdasarkan riwayat pengurangan stok.",
)
def download_laporan_rekap(
    tipe: str = Query(..., description="harian|bulanan|tahunan"),
    tanggal: datetime.date | None = Query(None),
    tahun: int | None = Query(None),
    bulan: int | None = Query(None),
    user=Depends(require_role("admin")),
):
    """Generate CSV recap for the requested scope."""
    import io, csv

    output = io.StringIO()
    writer = csv.writer(output)

    with get_cursor() as cur:
        if tipe == "harian" and tanggal:
            start_dt, end_dt = get_day_boundaries(tanggal)
            writer.writerow(["Tanggal", str(tanggal)])
            writer.writerow(["Jam", "Pupuk", "Jumlah (Kg)"])
            cur.execute(
                """
                SELECT r.created_at, s.nama_pupuk, r.jumlah
                FROM riwayat_stock_pupuk r
                JOIN stok_pupuk s ON s.id = r.pupuk_id
                WHERE r.tipe='kurangi' AND r.created_at >= %s AND r.created_at < %s AND lower(r.satuan)='kg'
                ORDER BY r.created_at
                """,
                (start_dt, end_dt),
            )
            # Group by hour in Python
            by_hour = {}
            for rec in cur.fetchall():
                jam = extract_hour_from_datetime(rec["created_at"])
                if jam is not None:
                    key = (jam, rec["nama_pupuk"])
                    by_hour[key] = by_hour.get(key, 0) + int(rec["jumlah"])
            
            for (jam, pupuk_nama), total in sorted(by_hour.items()):
                writer.writerow([jam, pupuk_nama, total])
                
        elif tipe == "bulanan" and tahun and bulan:
            start_date, end_date = get_month_boundaries(tahun, bulan)
            writer.writerow(["Periode", f"{tahun}-{bulan:02d}"])
            writer.writerow(["Tanggal", "Pupuk", "Jumlah (Kg)"])
            cur.execute(
                """
                SELECT r.created_at, s.nama_pupuk, r.jumlah
                FROM riwayat_stock_pupuk r
                JOIN stok_pupuk s ON s.id = r.pupuk_id
                WHERE r.tipe='kurangi' AND r.created_at >= %s AND r.created_at < %s AND lower(r.satuan)='kg'
                ORDER BY r.created_at
                """,
                (start_date, end_date),
            )
            # Group by date in Python
            by_day = {}
            for rec in cur.fetchall():
                tgl = extract_date_from_datetime(rec["created_at"])
                if tgl:
                    key = (tgl, rec["nama_pupuk"])
                    by_day[key] = by_day.get(key, 0) + int(rec["jumlah"])
            
            for (tgl, pupuk_nama), total in sorted(by_day.items()):
                writer.writerow([tgl, pupuk_nama, total])
                
        elif tipe == "tahunan" and tahun:
            start_date, end_date = get_year_boundaries(tahun)
            writer.writerow(["Tahun", str(tahun)])
            writer.writerow(["Bulan", "Pupuk", "Jumlah (Kg)"])
            cur.execute(
                """
                SELECT r.created_at, s.nama_pupuk, r.jumlah
                FROM riwayat_stock_pupuk r
                JOIN stok_pupuk s ON s.id = r.pupuk_id
                WHERE r.tipe='kurangi' AND r.created_at >= %s AND r.created_at < %s AND lower(r.satuan)='kg'
                ORDER BY r.created_at
                """,
                (start_date, end_date),
            )
            # Group by month in Python
            by_month = {}
            for rec in cur.fetchall():
                bln = extract_month_from_date(rec["created_at"])
                if bln:
                    key = (bln, rec["nama_pupuk"])
                    by_month[key] = by_month.get(key, 0) + int(rec["jumlah"])
            
            for (bln, pupuk_nama), total in sorted(by_month.items()):
                writer.writerow([bln, pupuk_nama, total])
        else:
            raise HTTPException(
                status_code=400, detail="Parameter tidak valid untuk tipe laporan"
            )

    csv_data = output.getvalue().encode("utf-8")
    from fastapi.responses import Response

    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=laporan_rekap.csv"},
    )
