from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from datetime import date, datetime
from pydantic import BaseModel
from typing import Optional
import shutil
import os
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form

from core.dependencies import require_role
from db.db_base import get_cursor

router = APIRouter()

# ============== Schemas ==============
class JadwalDistribusiResponse(BaseModel):
    id: int
    permohonan_id: int
    tanggal_pengiriman: str
    lokasi: str
    status: str
    tahap: Optional[str] = None

class PenerimaItemResponse(BaseModel):
    id: int
    permohonan_id: int
    nama_petani: str
    nik: str
    jenis_pupuk: str
    jumlah_disetujui: int
    satuan: str
    no_hp: str
    status_distribusi: str
    verified_at: Optional[str] = None

class JadwalDetailResponse(BaseModel):
    jadwal_id: int
    permohonan_id: int
    tanggal_pengiriman: str
    lokasi: str
    jadwal_status: str
    tahap: Optional[str] = None
    penerima_list: list[PenerimaItemResponse]

    permohonan_id: int
    bukti_penerima_url: Optional[str] = None
    catatan: Optional[str] = None

class VerifikasiPenerimaPupukResponse(BaseModel):
    message: str
    permohonan_id: int
    status_baru: str


class RiwayatDistribusiItem(BaseModel):
    jadwal_id: int
    permohonan_id: int
    tanggal_pengiriman: str
    lokasi: str
    status: str
    total_penerima_terverifikasi: int
    total_volume: int | None = None
    satuan: str | None = None

class JadwalStatusUpdate(BaseModel):
    status: str

# ============== Endpoints ==============

@router.get("/jadwal-distribusi-pupuk", response_model=list[JadwalDistribusiResponse])
def get_jadwal_distribusi(
    lokasi: Optional[str] = Query(None),
    tanggal: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user=Depends(require_role("distributor"))
):
    """
    Get all distribution schedules (Jadwal Distribusi Pupuk Bersubsidi).
    
    Query Parameters:
    - lokasi: Filter by location
    - tanggal: Filter by date (YYYY-MM-DD)
    - status: Filter by status (dijadwalkan, dikirim)
    """
    with get_cursor() as cur:
        query = """
            SELECT 
                j.id,
                j.permohonan_id,
                CAST(j.tanggal_pengiriman AS TEXT) AS tanggal_pengiriman,
                j.lokasi,
                j.status
            FROM jadwal_distribusi_pupuk j
            WHERE 1=1
        """
        params = []

        if lokasi:
            query += " AND j.lokasi ILIKE %s"
            params.append(f"%{lokasi}%")

        if tanggal:
            query += " AND j.tanggal_pengiriman = %s"
            params.append(tanggal)

        if status:
            query += " AND j.status = %s"
            params.append(status)

        query += " ORDER BY j.tanggal_pengiriman DESC"

        cur.execute(query, params)
        rows = cur.fetchall()

        return [
            {
                "id": row["id"],
                "permohonan_id": row["permohonan_id"],
                "tanggal_pengiriman": str(row["tanggal_pengiriman"]),
                "lokasi": row["lokasi"],
                "status": row["status"],
            }
            for row in rows
        ]

@router.get("/jadwal-distribusi-pupuk/{jadwal_id}", response_model=JadwalDetailResponse)
def get_jadwal_detail(
    jadwal_id: int,
    user=Depends(require_role("distributor"))
):
    """
    Get detailed information about a distribution schedule including all recipients.
    """
    with get_cursor() as cur:
        # Get jadwal details
        cur.execute("""
            SELECT 
                j.id,
                j.permohonan_id,
                CAST(j.tanggal_pengiriman AS TEXT) AS tanggal_pengiriman,
                j.lokasi,
                j.status
            FROM jadwal_distribusi_pupuk j
            WHERE j.id = %s
        """, [jadwal_id])
        
        jadwal_row = cur.fetchone()
        if not jadwal_row:
            raise HTTPException(status_code=404, detail="Jadwal distribusi not found")
        
        # Get all penerima (recipients) in this distribution
        cur.execute("""
            SELECT 
                pp.id AS permohonan_id,
                pf.nama_lengkap AS nama_petani,
                pf.nik,
                sp.nama_pupuk AS jenis_pupuk,
                COALESCE(pp.jumlah_disetujui, pp.jumlah_diminta) AS jumlah_disetujui,
                sp.satuan,
                pf.no_hp,
                pp.status AS status_distribusi,
                MAX(v.tanggal_verifikasi) as tanggal_verifikasi
            FROM pengajuan_pupuk pp
            JOIN profile_petani pf ON pf.user_id = pp.petani_id
            JOIN stok_pupuk sp ON sp.id = pp.pupuk_id
            LEFT JOIN verifikasi_penerima_pupuk v ON v.permohonan_id = pp.id
            WHERE pp.id = %s
            GROUP BY pp.id, pf.nama_lengkap, pf.nik, sp.nama_pupuk, pp.jumlah_disetujui, pp.jumlah_diminta, sp.satuan, pf.no_hp, pp.status
            ORDER BY pf.nama_lengkap
        """, [jadwal_row["permohonan_id"]])
        
        penerima_rows = cur.fetchall()
        
        penerima_list = [
            {
                "id": row["permohonan_id"],
                "permohonan_id": row["permohonan_id"],
                "nama_petani": row["nama_petani"],
                "nik": row["nik"],
                "jenis_pupuk": row["jenis_pupuk"],
                "jumlah_disetujui": row["jumlah_disetujui"],
                "satuan": row["satuan"],
                "no_hp": row["no_hp"],
                "status_distribusi": row["status_distribusi"],
                "verified_at": str(row["tanggal_verifikasi"]) if row["tanggal_verifikasi"] else None
            }
            for row in penerima_rows
        ]
        
        return {
            "jadwal_id": jadwal_row["id"],
            "permohonan_id": jadwal_row["permohonan_id"],
            "tanggal_pengiriman": jadwal_row["tanggal_pengiriman"],
            "lokasi": jadwal_row["lokasi"],
            "jadwal_status": jadwal_row["status"],
            "penerima_list": penerima_list
        }

@router.post("/verifikasi-penerima-pupuk", response_model=VerifikasiPenerimaPupukResponse)
def verify_penerima_pupuk(
    permohonan_id: int = Form(...),
    catatan: Optional[str] = Form(None),
    bukti_foto: Optional[UploadFile] = File(None),
    user=Depends(require_role("distributor"))
):
    """
    Verify that a recipient (Penerima Pupuk) has received the fertilizer.
    Updates the status to 'selesai' (completed) and saves the proof image.
    """
    with get_cursor(commit=True) as cur:
        # Get current status
        cur.execute("""
            SELECT id, status FROM pengajuan_pupuk WHERE id = %s
        """, [permohonan_id])
        
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Permohonan not found")
        
        permohonan_id = result["id"]
        current_status = result["status"]
        
        # Verify that the permohonan is in 'dikirim' status
        if current_status not in ['dikirim', 'dijadwalkan']:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot verify permohonan with status {current_status}. Must be 'dikirim' or 'dijadwalkan'"
            )
        
        # Update status to 'selesai'
        cur.execute("""
            UPDATE pengajuan_pupuk 
            SET status = 'selesai'
            WHERE id = %s
        """, [permohonan_id])
        
        # NOTE: Status jadwal_distribusi_pupuk TIDAK otomatis 'selesai'.
        # Distributor harus mengubahnya secara manual via endpoint update status.

        
        # Handle file upload
        file_path = None
        if bukti_foto:
            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bukti_{permohonan_id}_{timestamp}_{bukti_foto.filename}"
            file_path = os.path.join(upload_dir, filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(bukti_foto.file, buffer)

        # Check if already verified to prevent duplicates
        cur.execute("SELECT id FROM verifikasi_penerima_pupuk WHERE permohonan_id = %s", (permohonan_id,))
        existing_verif = cur.fetchone()
        if existing_verif:
             # Already verified, maybe just update?
             # Or skip insert.
             # Let's just update the photo/notes if needed, or do nothing.
             # User prompt implies duplication is bad.
             # We'll update the existing record to be safe.
             cur.execute("""
                UPDATE verifikasi_penerima_pupuk 
                SET bukti_foto_url = COALESCE(%s, bukti_foto_url), 
                    catatan = COALESCE(%s, catatan),
                    tanggal_verifikasi = CURRENT_TIMESTAMP
                WHERE id = %s
             """, (file_path, catatan, existing_verif["id"]))
        else:
             # Insert into verifikasi_penerima_pupuk table
             cur.execute("""
                INSERT INTO verifikasi_penerima_pupuk
                (permohonan_id, distributor_id, bukti_foto_url, catatan, tanggal_verifikasi)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
             """, [permohonan_id, user['id'], file_path, catatan])
        
        # Log the verification if needed (optional)
        cur.execute("""
            INSERT INTO riwayat_stock_pupuk 
            (pupuk_id, tipe, jumlah, satuan, catatan, admin_user_id, created_at)
            SELECT 
                pp.pupuk_id, 
                'kurangi' as tipe, 
                pp.jumlah_disetujui as jumlah,
                sp.satuan,
                %s,
                %s,
                CURRENT_TIMESTAMP
            FROM pengajuan_pupuk pp
            JOIN stok_pupuk sp ON sp.id = pp.pupuk_id
            WHERE pp.id = %s
        """, [catatan or f"Penerima verified by distributor. Bukti: {file_path}", user['id'], permohonan_id])
        
        return {
            "message": "Verifikasi penerima pupuk berhasil",
            "permohonan_id": permohonan_id,
            "status_baru": "selesai"
        }


@router.get("/riwayat-distribusi-pupuk", response_model=list[RiwayatDistribusiItem])
def get_riwayat_distribusi_pupuk(
    start_date: Optional[str] = Query(None, description="Filter mulai tanggal pengiriman (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter sampai tanggal pengiriman (YYYY-MM-DD)"),
    lokasi: Optional[str] = Query(None, description="Filter lokasi jadwal"),
    status: Optional[str] = Query("selesai", description="Status jadwal, default selesai"),
    user=Depends(require_role("distributor"))
):
    """
    Riwayat distribusi pupuk bersubsidi (jadwal yang sudah selesai).
    """
    with get_cursor() as cur:
        query = """
            SELECT 
                j.id AS jadwal_id,
                j.permohonan_id,
                CAST(j.tanggal_pengiriman AS TEXT) AS tanggal_pengiriman,
                j.lokasi,
                j.status,
                COALESCE(COUNT(v.id), 0) AS total_penerima_terverifikasi,
                COALESCE(SUM(pp.jumlah_disetujui), 0) AS total_volume,
                sp.satuan
            FROM jadwal_distribusi_pupuk j
            JOIN pengajuan_pupuk pp ON pp.id = j.permohonan_id
            JOIN stok_pupuk sp ON sp.id = pp.pupuk_id
            LEFT JOIN verifikasi_penerima_pupuk v ON v.permohonan_id = pp.id
            WHERE 1=1
        """
        params = []

        # Status filter (default selesai)
        if status:
            query += " AND j.status = %s"
            params.append(status)
        else:
            query += " AND j.status = 'selesai'"

        if start_date:
            query += " AND j.tanggal_pengiriman >= %s"
            params.append(start_date)

        if end_date:
            query += " AND j.tanggal_pengiriman <= %s"
            params.append(end_date)

        if lokasi:
            query += " AND j.lokasi ILIKE %s"
            params.append(f"%{lokasi}%")

        query += " GROUP BY j.id, j.permohonan_id, j.tanggal_pengiriman, j.lokasi, j.status, sp.satuan"
        query += " ORDER BY j.tanggal_pengiriman DESC"

        cur.execute(query, params)
        rows = cur.fetchall()

        return [
            {
                "jadwal_id": row["jadwal_id"],
                "permohonan_id": row["permohonan_id"],
                "tanggal_pengiriman": row["tanggal_pengiriman"],
                "lokasi": row["lokasi"],
                "status": row["status"],
                "total_penerima_terverifikasi": row["total_penerima_terverifikasi"],
                "total_volume": row["total_volume"],
                "satuan": row["satuan"],
            }
            for row in rows
        ]



@router.put("/jadwal-distribusi-pupuk/{jadwal_id}/status")
def update_status_jadwal(
    jadwal_id: int,
    req: JadwalStatusUpdate,
    user=Depends(require_role("distributor"))
):
    """
    Update status jadwal distribusi:
    - dijadwalkan -> mulai (disimpan sebagai 'dikirim')
    - dikirim -> selesai (validasi semua petani selesai/ditolak)
    """
    new_status = req.status.lower()
    print(f"DEBUG: update_status_jadwal id={jadwal_id} new_status={new_status} req={req}")
    
    # Validasi input status
    if new_status not in ["mulai", "selesai"]:
         print("DEBUG: Status validasi failed")
         raise HTTPException(status_code=400, detail="Status harus 'mulai' atau 'selesai'")

    with get_cursor(commit=True) as cur:
        # Get jadwal details
        cur.execute("SELECT id, permohonan_id, status FROM jadwal_distribusi_pupuk WHERE id = %s", [jadwal_id])
        jadwal = cur.fetchone()
        
        if not jadwal:
            raise HTTPException(status_code=404, detail="Jadwal distribusi not found")

        current_status = jadwal["status"]
        permohonan_id = jadwal["permohonan_id"]
        print(f"DEBUG: Found jadwal {jadwal_id}. Current status: {current_status}, Permohonan ID: {permohonan_id}")

        # Logic transition
        target_db_status = None

        if new_status == "mulai":
            # Idempotency
            if current_status == "dikirim":
                 return {"message": "Status updated to mulai (already active)", "new_status": "dikirim"}

            if current_status != "dijadwalkan":
                raise HTTPException(status_code=400, detail=f"Hanya bisa mulai jika status saat ini 'dijadwalkan'. Status sekarang: {current_status}")
            
            target_db_status = "dikirim"
            
            # Update jadwal
            cur.execute(
                "UPDATE jadwal_distribusi_pupuk SET status = %s WHERE id = %s",
                (target_db_status, jadwal_id)
            )
            # Update parent permohonan status to match logic if needed, 
            # usually permohonan follows jadwal status or vice versa.
            # Let's update permohonan status too to keep sync
            cur.execute(
                "UPDATE pengajuan_pupuk SET status = %s WHERE id = %s",
                (target_db_status, permohonan_id)
            )

        elif new_status == "selesai":
            # Idempotency
            if current_status == "selesai":
                return {"message": "Status updated to selesai (already done)", "new_status": "selesai"}
                
            if current_status != "dikirim": # 'dikirim' is the DB state for 'mulai'
                raise HTTPException(status_code=400, detail=f"Hanya bisa selesai jika status saat ini 'mulai' (sedang dikirim). Status sekarang: {current_status}")
            
            # Validate all recipients are done
            # We need to check INDIVIDUAL recipients if permohonan_id represents a GROUP request or Single?
            # Schema seems to link Jadwal -> 1 Permohonan. 
            # But get_jadwal_detail joins pengajuan_pupuk on id. 
            # Wait, PermohonanPupuk is single per user. 
            # ONE Jadwal per Permohonan?
            # Let's re-read models: JadwalDistribusi has permohonan_id. One-to-one or Many-to-one?
            # relationship in PermohonanPupuk: jadwal_distribusi = relationship(..., uselist=False) -> One-to-One.
            # So one Jadwal is for one Permohonan (which is one Petani + one Pupuk).
            
            # WAIT. The user prompt says "hanya bisa diselesaikan jika semua petani telah selesai".
            # This implies a Jadwal might cover MULTIPLE farmers?
            # Looking at `models.py`:
            # `JadwalDistribusiEvent` -> has `items` (JadwalDistribusiItem) -> linked to pupuk.
            # BUT `JadwalDistribusi` (used in distributor.py) links to `PermohonanPupuk`.
            # `PermohonanPupuk` is for ONE Petani.
            
            # HOWEVER, `get_jadwal_detail` query does:
            # `SELECT ... FROM pengajuan_pupuk pp WHERE pp.id = %s` (using jadwal_row["permohonan_id"])
            # It seems the `JadwalDistribusi` table is legacy or specific 1-to-1?
            
            # Let's look at `get_jadwal_detail` again in `distributor.py`.
            # querying `pengajuan_pupuk` by `id`.
            # If `PermohonanPupuk` is 1 row per request, then "all farmers" implies the endpoint might be for `JadwalDistribusiEvent`?
            # BUT `distributor.py` uses `JadwalDistribusi` table.
            
            # Maybe `permohonan_id` in `JadwalDistribusi` refers to a Group? No, `PermohonanPupuk` has `petani_id`.
            # Let's re-read the User Request:
            # { "id": 1, "permohonan_id": 1, ... } list of `JadwalDistribusi`.
            # And user says: "dijawab semua daftar petani penerimanya".
            # This implies `permohonan_id` might be confusingly named or I am missing something.
            
            # Let's check `get_jadwal_detail` logic:
            # It selects ONE permohonan.
            # `SELECT ... FROM pengajuan_pupuk pp ... WHERE pp.id = %s`.
            # So it returns ONE recipient list (size 1?).
            # BUT `penerima_rows` is fetchall().
            
            # Is it possible multiple farmers share `permohonan_id`? 
            # `id` is primary key of `pengajuan_pupuk`. So NO.
            
            # Wait, look at `get_jadwal_detail`...
            # `JOIN profile_petani ... JOIN stok_pupuk ...`
            # It joins on `pp.id`.
            # Unless `get_jadwal_detail` is somehow retrieving multiple rows?
            
            # AH! Maybe existing codebase is confusing `permohonan_id` with `jadwal_id` or something?
            # Or maybe `distributor.py` is working with the `JadwalDistribusi` model which links to ONE `PermohonanPupuk`.
            
            # User Prompt: "status": "dijadwalkan", jadi distributor hanya mampu mengubah statusnya dari dijadwalkan ke mulai lalu ke selesaikan, 
            # hanya bisa diselesaikan jika semua petani telah selesai ataupun ditolak tapi harus dijawab semua daftar petani penerimanya
            
            # IF this `JadwalDistribusi` is 1-to-1 with `PermohonanPupuk`, then "semua petani" is just "the one petani".
            # UNLESS `JadwalDistribusi` is supposed to be for a group?
            
            # Let's proceed assuming existing structure: One Jadwal = One Permohonan = One Petani.
            # So "semua petani" just means "check the status of the associated permohonan".
            # IF there is a separate "Event" based distribution (like `JadwalDistribusiEvent` which has items), 
            # that is in `admin.py`. `distributor.py` seems to use `JadwalDistribusi` (the 1-to-1 mapping).
            
            # I will stick to checking the status of the linked `PermohonanPupuk`.
            # If the user intended the "Event" one, they would have likely pointed to `JadwalDistribusiEvent`.
            # `distributor.py` imports `JadwalDistribusi`.
            
            # Wait, `get_jadwal_detail` implementation in `distributor.py` returns `penerima_list` as a list.
            # `cur.fetchall()` implies multiple rows could exist.
            # But the query is `WHERE pp.id = %s`. `pp.id` is PK. 
            # So it will always be 1 or 0 rows.
            # So `penerima_list` will have size 1.
            
            # SO: "Semua petani" = "The single petani".
            # Checking if `pp.status` is 'selesai' or 'ditolak'.
            
            # Query status of permohonan
            cur.execute("SELECT status FROM pengajuan_pupuk WHERE id = %s", [permohonan_id])
            
            # Wait, if we moved to `dikirim`, `pengajuan_pupuk` status is `dikirim`.
            # The 'petani' is finished if `verifikasi_penerima_pupuk` happened?
            # When `verify_penerima_pupuk` is called (POST verify), it updates `pengajuan_pupuk` to 'selesai'.
            
            # So here we just verify `pengajuan_pupuk.status` is 'selesai'.
            # And enable setting `JadwalDistribusi.status` to 'selesai'.
            
            pm = cur.fetchone()
            if not pm:
                 raise HTTPException(status_code=404, detail="Permohonan linked to jadwal not found")
            
            pm_status = pm["status"]
            if pm_status not in ['selesai', 'ditolak']:
                raise HTTPException(status_code=400, detail="Tidak dapat menyelesaikan jadwal. Petani belum selesai/ditolak.")
                
            target_db_status = "selesai"
            
            cur.execute(
                "UPDATE jadwal_distribusi_pupuk SET status = %s WHERE id = %s",
                (target_db_status, jadwal_id)
            )

        return {"message": f"Status updated to {new_status}", "new_status": target_db_status}
