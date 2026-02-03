from fastapi import APIRouter, Depends, HTTPException, Query
from core.dependencies import require_role
from core.security import hash_password
from db.db_base import get_cursor
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(tags=["SuperAdmin"])

class UserListResponse(BaseModel):
    user_id: int
    username: str
    role: str
    nama_lengkap: str
    status: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str  # admin, distributor, super_admin
    nama_lengkap: str
    alamat: str
    no_hp: str
    perusahaan: Optional[str] = None  # Required for distributor

class CreateUserResponse(BaseModel):
    status: str
    message: str
    user_id: int
    username: str
    role: str
    nama_lengkap: str

class EditUserRequest(BaseModel):
    nama_lengkap: Optional[str] = None
    alamat: Optional[str] = None
    no_hp: Optional[str] = None
    perusahaan: Optional[str] = None  # For distributor
    password: Optional[str] = None  # Optional password change

class EditUserResponse(BaseModel):
    status: str
    message: str
    user_id: int
    updated_fields: dict

class DeleteUserResponse(BaseModel):
    status: str
    message: str
    user_id: int
    username: str

@router.get("/metrics")
def metrics(user=Depends(require_role("super_admin"))):
    return {
        "uptime": "99.9%",
        "total_users": 1284,
        "error_logs": 2
    }

@router.get("/users", response_model=list[UserListResponse])
def list_users(
    role: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(require_role("super_admin")),
):
    """
    List all users with optional role filtering.
    Roles: petani, admin, distributor, super_admin
    """
    offset = (page - 1) * page_size
    filters = []
    params = []
    
    if role:
        filters.append("u.role = %s")
        params.append(role)
    
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    
    sql = f"""
        SELECT 
            u.id as user_id,
            u.username,
            u.role,
            COALESCE(
                COALESCE(pp.nama_lengkap, pd.nama_lengkap),
                COALESCE(pa.nama_lengkap, ps.nama_lengkap)
            ) as nama_lengkap,
            CASE 
                WHEN u.role = 'petani' THEN CASE WHEN pp.status_verifikasi THEN 'Aktif' ELSE 'Non-Aktif' END
                ELSE 'Aktif'
            END as status
        FROM users u
        LEFT JOIN profile_petani pp ON u.id = pp.user_id
        LEFT JOIN profile_distributor pd ON u.id = pd.user_id
        LEFT JOIN profile_admin pa ON u.id = pa.user_id
        LEFT JOIN profile_superadmin ps ON u.id = ps.user_id
        {where}
        ORDER BY u.id DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    
    with get_cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        return [dict(row) for row in rows]

@router.get("/users/{user_id}", response_model=dict)
def get_user_detail(
    user_id: int,
    user=Depends(require_role("super_admin")),
):
    """
    Get detailed user information including profile.
    """
    sql = """
        SELECT 
            u.id as user_id,
            u.username,
            u.role,
            u.created_at,
            COALESCE(pp.nama_lengkap, pd.nama_lengkap, pa.nama_lengkap, ps.nama_lengkap) as nama_lengkap,
            COALESCE(pp.nik, '') as nik,
            COALESCE(pp.alamat, pd.alamat, pa.alamat, ps.alamat) as alamat,
            COALESCE(pp.no_hp, pd.no_hp, pa.no_hp, ps.no_hp) as no_hp,
            CASE 
                WHEN u.role = 'petani' THEN CASE WHEN pp.status_verifikasi THEN 'Aktif' ELSE 'Non-Aktif' END
                ELSE 'Aktif'
            END as status
        FROM users u
        LEFT JOIN profile_petani pp ON u.id = pp.user_id
        LEFT JOIN profile_distributor pd ON u.id = pd.user_id
        LEFT JOIN profile_admin pa ON u.id = pa.user_id
        LEFT JOIN profile_superadmin ps ON u.id = ps.user_id
        WHERE u.id = %s
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        return dict(row)

@router.post("/users/add", response_model=CreateUserResponse)
def create_user(
    req: CreateUserRequest,
    user=Depends(require_role("super_admin")),
):
    """
    Create a new user (Admin, Distributor, or Superadmin).
    Required fields for each role:
    - admin: username, password, role, nama_lengkap, alamat, no_hp
    - distributor: username, password, role, nama_lengkap, alamat, no_hp, perusahaan
    - super_admin: username, password, role, nama_lengkap, alamat, no_hp
    """
    # Validate role
    if req.role not in ["admin", "distributor", "super_admin"]:
        raise HTTPException(status_code=400, detail="Role harus: admin, distributor, atau super_admin")
    
    # Validate distributor requires perusahaan
    if req.role == "distributor" and not req.perusahaan:
        raise HTTPException(status_code=400, detail="Perusahaan wajib diisi untuk distributor")
    
    with get_cursor(commit=True) as cur:
        # Check if username already exists
        cur.execute("SELECT id FROM users WHERE username = %s", (req.username,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Username sudah terdaftar")
        
        # Hash password
        password_hash = hash_password(req.password)
        
        # Create user
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            (req.username, password_hash, req.role)
        )
        
        # Get the created user ID
        user_id = cur.lastrowid
        
        # Create profile based on role
        if req.role == "admin":
            cur.execute(
                """INSERT INTO profile_admin (user_id, nama_lengkap, alamat, no_hp)
                   VALUES (%s, %s, %s, %s)""",
                (user_id, req.nama_lengkap, req.alamat, req.no_hp)
            )
        elif req.role == "distributor":
            cur.execute(
                """INSERT INTO profile_distributor (user_id, nama_lengkap, perusahaan, alamat, no_hp, status_verifikasi)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, req.nama_lengkap, req.perusahaan, req.alamat, req.no_hp, False)
            )
        elif req.role == "super_admin":
            cur.execute(
                """INSERT INTO profile_superadmin (user_id, nama_lengkap, alamat, no_hp)
                   VALUES (%s, %s, %s, %s)""",
                (user_id, req.nama_lengkap, req.alamat, req.no_hp)
            )
        
        return {
            "status": "success",
            "message": f"User {req.username} berhasil dibuat sebagai {req.role}",
            "user_id": user_id,
            "username": req.username,
            "role": req.role,
            "nama_lengkap": req.nama_lengkap
        }
@router.put("/users/{user_id}", response_model=EditUserResponse)
def edit_user(
    user_id: int,
    req: EditUserRequest,
    user=Depends(require_role("super_admin")),
):
    """
    Edit user information.
    Can update: nama_lengkap, alamat, no_hp, perusahaan (for distributor), password
    """
    with get_cursor(commit=True) as cur:
        # Check if user exists and get role
        cur.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
        user_row = cur.fetchone()
        
        if not user_row:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        user_role = user_row["role"]
        updated_fields = {}
        
        # Update password if provided
        if req.password:
            password_hash = hash_password(req.password)
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (password_hash, user_id))
            updated_fields["password"] = "***"
        
        # Update profile based on role
        if user_role == "admin":
            profile_table = "profile_admin"
        elif user_role == "distributor":
            profile_table = "profile_distributor"
        elif user_role == "super_admin":
            profile_table = "profile_superadmin"
        elif user_role == "petani":
            profile_table = "profile_petani"
        else:
            raise HTTPException(status_code=400, detail="Role tidak valid")
        
        # Build update query for profile
        update_fields = []
        update_values = []
        
        if req.nama_lengkap:
            update_fields.append("nama_lengkap = %s")
            update_values.append(req.nama_lengkap)
            updated_fields["nama_lengkap"] = req.nama_lengkap
        
        if req.alamat:
            update_fields.append("alamat = %s")
            update_values.append(req.alamat)
            updated_fields["alamat"] = req.alamat
        
        if req.no_hp:
            update_fields.append("no_hp = %s")
            update_values.append(req.no_hp)
            updated_fields["no_hp"] = req.no_hp
        
        if req.perusahaan and user_role == "distributor":
            update_fields.append("perusahaan = %s")
            update_values.append(req.perusahaan)
            updated_fields["perusahaan"] = req.perusahaan
        
        # Execute update if there are fields to update
        if update_fields:
            update_values.append(user_id)
            query = f"UPDATE {profile_table} SET {', '.join(update_fields)} WHERE user_id = %s"
            cur.execute(query, tuple(update_values))
        
        return {
            "status": "success",
            "message": f"User berhasil diperbarui",
            "user_id": user_id,
            "updated_fields": updated_fields
        }

@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
def delete_user(
    user_id: int,
    user=Depends(require_role("super_admin")),
):
    """
    Delete a user and all associated profile data.
    """
    with get_cursor(commit=True) as cur:
        # Check if user exists
        cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
        user_row = cur.fetchone()
        
        if not user_row:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        
        username = user_row["username"]
        
        # Delete user (cascade will delete associated profiles)
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        return {
            "status": "success",
            "message": f"User {username} berhasil dihapus",
            "user_id": user_id,
            "username": username
        }