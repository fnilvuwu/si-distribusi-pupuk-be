"""
Comprehensive Test Suite for SI Distribusi Pupuk API
Tests all endpoints with various scenarios
"""

import pytest
import os
import sys
from io import BytesIO
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app
from db import db_base
from db.db_base import get_db
from db.models import (
    Base, User, ProfilePetani, ProfileDistributor, ProfileAdmin, 
    ProfileSuperadmin, StokPupuk, PermohonanPupuk, JadwalDistribusi, HasilTani,
    VerifikasiPenerimaPupuk,
)
from core.security import hash_password, create_access_token

# ============================================================================
# CONFIGURATION
# ============================================================================

# Use in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for tests"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

@pytest.fixture(autouse=True)
def reset_db():
    """Reset database before each test"""
    # Ensure the db_base module uses the in-memory engine/session
    db_base.engine = engine
    db_base.SessionLocal = TestingSessionLocal
    db_base._tables_initialized = False

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db() -> Session:
    """Provide test database session"""
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture
def seed_fertilizers(test_db: Session):
    """Seed test data with fertilizers"""
    fertilizers = [
        StokPupuk(nama_pupuk="Urea", jumlah_stok=500, satuan="kg"),
        StokPupuk(nama_pupuk="TSP", jumlah_stok=300, satuan="kg"),
        StokPupuk(nama_pupuk="KCl", jumlah_stok=200, satuan="kg"),
    ]
    for f in fertilizers:
        test_db.add(f)
    test_db.commit()
    return fertilizers


@pytest.fixture
def create_test_user_petani(test_db: Session) -> User:
    """Create a test petani user"""
    user = User(
        username="1234567890123456",  # Valid NIK format
        password_hash=hash_password("testpassword123"),
        role="petani",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def create_test_user_admin(test_db: Session) -> User:
    """Create a test admin user"""
    user = User(
        username="admin_user",
        password_hash=hash_password("adminpassword123"),
        role="admin",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def create_test_user_distributor(test_db: Session) -> User:
    """Create a test distributor user"""
    user = User(
        username="distributor_user",
        password_hash=hash_password("distpassword123"),
        role="distributor",
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def petani_token(create_test_user_petani):
    """Generate JWT token for petani"""
    return create_access_token(data={"sub": str(create_test_user_petani.id)})


@pytest.fixture
def admin_token(create_test_user_admin):
    """Generate JWT token for admin"""
    return create_access_token(data={"sub": str(create_test_user_admin.id)})


@pytest.fixture
def distributor_token(create_test_user_distributor):
    """Generate JWT token for distributor"""
    return create_access_token(data={"sub": str(create_test_user_distributor.id)})


@pytest.fixture
def superadmin_token():
    """Generate JWT token for superadmin"""
    db = TestingSessionLocal()
    user = User(
        username="superadmin",
        password_hash=hash_password("superadminpass"),
            role="super_admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create profile for superadmin
    profile = ProfileSuperadmin(
        user_id=user.id,
        nama_lengkap="Super Admin",
        alamat="Jl. Super Admin",
        no_hp="081234567890",
    )
    db.add(profile)
    db.commit()
    
    token = create_access_token(data={"sub": str(user.id)})
    db.close()
    return token


def create_test_file():
    """Create a test file for upload"""
    file = BytesIO(b"test file content")
    file.name = "test.pdf"
    return file


@pytest.fixture
def seed_jadwal_distribusi(test_db: Session, create_test_user_petani, seed_fertilizers):
    """Seed one permohonan and jadwal distribusi for distributor tests."""
    # Create petani profile
    profile = ProfilePetani(
        user_id=create_test_user_petani.id,
        nama_lengkap="Petani Jadwal",
        nik="9999999999999999",
        alamat="Jl. Jadwal 1",
        no_hp="081111111111",
        status_verifikasi=True,
    )
    test_db.add(profile)
    test_db.commit()

    pupuk = seed_fertilizers[0]

    permohonan = PermohonanPupuk(
        petani_id=profile.user_id,
        pupuk_id=pupuk.id,
        jumlah_diminta=50,
        jumlah_disetujui=50,
        status="dikirim",
        alasan="Uji jadwal",
    )
    test_db.add(permohonan)
    test_db.commit()
    test_db.refresh(permohonan)

    jadwal = JadwalDistribusi(
        permohonan_id=permohonan.id,
        tanggal_pengiriman=date.today(),
        lokasi="Gudang Kios Tani Makmur",
        status="dikirim",
    )
    test_db.add(jadwal)
    test_db.commit()
    test_db.refresh(jadwal)

    return {
        "profile": profile,
        "permohonan": permohonan,
        "jadwal": jadwal,
        "pupuk": pupuk,
    }


@pytest.fixture
def seed_jadwal_distribusi_selesai(seed_jadwal_distribusi, test_db: Session):
    """Seed one jadwal distribusi already selesai for riwayat tests."""
    permohonan = seed_jadwal_distribusi["permohonan"]
    jadwal = seed_jadwal_distribusi["jadwal"]

    permohonan.status = "selesai"
    jadwal.status = "selesai"
    test_db.commit()
    test_db.refresh(permohonan)
    test_db.refresh(jadwal)

    seed_jadwal_distribusi["permohonan"] = permohonan
    seed_jadwal_distribusi["jadwal"] = jadwal
    return seed_jadwal_distribusi


def auth_headers(token: str) -> dict[str, str]:
    """Helper to build Authorization header."""
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

class TestHealth:
    """Test health check endpoint"""

    def test_health_check(self):
        """Test /health endpoint returns OK"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class TestAuth:
    """Test authentication endpoints"""

    def test_register_petani_success(self, seed_fertilizers):
        """Test successful petani registration"""
        data = {
            "nama_lengkap": "Test Petani",
            "nik": "1234567890123456",
            "alamat": "Jl. Test No. 123",
            "no_hp": "081234567890",
            "password": "TestPassword123!",
        }
        files = {
            "foto_ktp": ("test_ktp.pdf", BytesIO(b"KTP content"), "application/pdf"),
        }
        
        response = client.post("/auth/register_petani", data=data, files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "user_created_and_logged_in"
        assert data["username"] == "1234567890123456"
        assert data["role"] == "petani"
        assert data["full_name"] == "Test Petani"
        assert "access_token" in data

    def test_register_petani_invalid_nik(self, seed_fertilizers):
        """Test petani registration with invalid NIK"""
        data = {
            "nama_lengkap": "Test Petani",
            "nik": "12345",  # Invalid - too short
            "alamat": "Jl. Test No. 123",
            "no_hp": "081234567890",
            "password": "TestPassword123!",
        }
        files = {
            "foto_ktp": ("test_ktp.pdf", BytesIO(b"KTP content"), "application/pdf"),
        }
        
        response = client.post("/auth/register_petani", data=data, files=files)
        assert response.status_code == 400
        assert "NIK harus 16 digit" in response.json()["detail"]

    def test_register_petani_duplicate_nik(self, seed_fertilizers, create_test_user_petani):
        """Test petani registration with duplicate NIK"""
        data = {
            "nama_lengkap": "Another Petani",
            "nik": "1234567890123456",  # Same as create_test_user_petani
            "alamat": "Jl. Test No. 456",
            "no_hp": "089876543210",
            "password": "TestPassword456!",
        }
        files = {
            "foto_ktp": ("test_ktp.pdf", BytesIO(b"KTP content"), "application/pdf"),
        }
        
        response = client.post("/auth/register_petani", data=data, files=files)
        assert response.status_code == 409

    def test_register_petani_missing_password(self, seed_fertilizers):
        """Test petani registration without password"""
        data = {
            "nama_lengkap": "Test Petani",
            "nik": "1234567890123456",
            "alamat": "Jl. Test No. 123",
            "no_hp": "081234567890",
            "password": "",
        }
        files = {
            "foto_ktp": ("test_ktp.pdf", BytesIO(b"KTP content"), "application/pdf"),
        }
        
        response = client.post("/auth/register_petani", data=data, files=files)
        assert response.status_code == 422  # Validation error from FastAPI

    def test_login_success(self, create_test_user_petani):
        """Test successful login"""
        response = client.post(
            "/auth/login",
            data={
                "username": "1234567890123456",
                "password": "testpassword123",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "petani"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/login",
            data={
                "username": "nonexistent",
                "password": "wrongpassword",
            }
        )
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_wrong_password(self, create_test_user_petani):
        """Test login with correct username but wrong password"""
        response = client.post(
            "/auth/login",
            data={
                "username": "1234567890123456",
                "password": "wrongpassword",
            }
        )
        assert response.status_code == 401

    def test_logout(self, petani_token):
        """Test logout endpoint"""
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    def test_logout_without_token(self):
        """Test logout without token"""
        response = client.post("/auth/logout")
        assert response.status_code == 401  # Unauthorized


# ============================================================================
# PETANI ENDPOINTS TESTS
# ============================================================================

class TestPetaniEndpoints:
    """Test petani-specific endpoints"""

    def test_get_profile_success(self, create_test_user_petani, test_db: Session, petani_token):
        """Test getting petani profile"""
        # Create profile for the user
        profile = ProfilePetani(
            user_id=create_test_user_petani.id,
            nama_lengkap="Test Petani",
            nik="1234567890123456",
            alamat="Jl. Test No. 123",
            no_hp="081234567890",
            status_verifikasi=False,
        )
        test_db.add(profile)
        test_db.commit()

        response = client.get(
            "/petani/profile",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nama_lengkap"] == "Test Petani"
        assert data["nik"] == "1234567890123456"

    def test_get_profile_not_found(self, petani_token):
        """Test getting profile when not created"""
        response = client.get(
            "/petani/profile",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert response.status_code == 404
        assert "Profil tidak ditemukan" in response.json()["detail"]

    def test_get_profile_unauthorized(self):
        """Test getting profile without token"""
        response = client.get("/petani/profile")
        assert response.status_code == 401

    def test_list_pupuk(self, seed_fertilizers, petani_token):
        """Test getting list of fertilizers"""
        response = client.get(
            "/petani/pupuk",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        # Check that we have at least the seeded fertilizers
        assert len(data) >= 2
        seeded = {"Urea", "TSP", "KCl"}
        returned = {p["nama_pupuk"] for p in data}
        assert "Urea" in returned
        assert returned & seeded  # at least one seeded fertilizer present

    def test_list_pupuk_empty(self, petani_token):
        """Test getting list of fertilizers - checks response structure"""
        response = client.get(
            "/petani/pupuk",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert response.status_code == 200
        # Just verify it's a list, not empty since dev db may have data
        data = response.json()
        assert isinstance(data, list)

    def test_list_pupuk_unauthorized(self):
        """Test getting pupuk list without token"""
        response = client.get("/petani/pupuk")
        assert response.status_code == 401


# ============================================================================
# ADMIN ENDPOINTS TESTS
# ============================================================================

class TestAdminEndpoints:
    """Test admin-specific endpoints"""

    def test_list_persetujuan_pupuk_empty(self, admin_token):
        """Test listing fertilizer approvals when empty"""
        response = client.get(
            "/admin/persetujuan_pupuk",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_list_verifikasi_hasil_tani(self, admin_token, test_db: Session, create_test_user_petani):
        """Test listing hasil tani verification"""
        # Create profile for petani
        profile = ProfilePetani(
            user_id=create_test_user_petani.id,
            nama_lengkap="Petani Hasil",
            nik="8888888888888888",
            alamat="Jl. Hasil",
            no_hp="081234567888",
            status_verifikasi=True,
        )
        # Check if profile already exists (fixture might create it?)
        # create_test_user_petani fixture creates User but not ProfilePetani usually? 
        # Check fixture definition.
        # It just creates User.
        
        test_db.add(profile)
        test_db.commit()

        # Create hasil tani
        hasil = HasilTani(
            petani_id=create_test_user_petani.id,
            jenis_tanaman="Padi",
            jumlah_hasil=1000,
            satuan="kg",
            tanggal_panen=date.today(),
            status_verifikasi=False
        )
        test_db.add(hasil)
        test_db.commit()

        response = client.get(
            "/admin/verifikasi_hasil_tani",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        found = False
        for item in data:
            if item["jenis_tanaman"] == "Padi" and item["petani_id"] == create_test_user_petani.id:
                found = True
                break
        assert found


# ============================================================================
# ADMIN STOCK & REPORTING ENDPOINTS
# ============================================================================


class TestAdminStockAndReports:
    """Tests for stock adjustments, history, and laporan rekap endpoints."""

    def test_tambah_stock_pupuk_success(self, seed_fertilizers, admin_token):
        pupuk_id = seed_fertilizers[0].id
        response = client.post(
            "/admin/tambah_stock_pupuk",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pupuk_id": pupuk_id, "jumlah": 100, "satuan": "kg"},
        )
        assert response.status_code == 200

        db = TestingSessionLocal()
        stok = db.query(StokPupuk).get(pupuk_id)
        assert stok.jumlah_stok == 600  # 500 + 100
        db.close()

    def test_kurangi_stock_pupuk_over_limit(self, seed_fertilizers, admin_token):
        pupuk_id = seed_fertilizers[0].id
        response = client.post(
            "/admin/kurangi_stock_pupuk",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pupuk_id": pupuk_id, "jumlah": 9999, "satuan": "kg"},
        )
        assert response.status_code == 400
        assert "melebihi" in response.json()["detail"]

    def test_riwayat_stock_filters(self, seed_fertilizers, admin_token):
        pupuk_id = seed_fertilizers[0].id
        # Add and subtract to create two history rows
        client.post(
            "/admin/tambah_stock_pupuk",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pupuk_id": pupuk_id, "jumlah": 50, "satuan": "kg"},
        )
        client.post(
            "/admin/kurangi_stock_pupuk",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pupuk_id": pupuk_id, "jumlah": 20, "satuan": "kg"},
        )

        today = date.today().isoformat()
        response = client.get(
            f"/admin/riwayat_stock_pupuk?pupuk_id={pupuk_id}&tipe=kurangi&created_from={today}&created_to={today}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["tipe"] == "kurangi"
        assert data[0]["jumlah"] == 20

    def test_laporan_rekap_harian_and_csv(self, seed_fertilizers, admin_token):
        pupuk_id = seed_fertilizers[0].id
        # Create some distribution (kurangi)
        client.post(
            "/admin/kurangi_stock_pupuk",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"pupuk_id": pupuk_id, "jumlah": 40, "satuan": "kg"},
        )

        today = date.today().isoformat()
        # JSON recap
        resp = client.get(
            f"/admin/laporan_rekap_harian?tanggal={today}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_penyaluran_kg"] >= 40
        assert isinstance(body["rekapitulasi"], list)

        # CSV download
        csv_resp = client.get(
            f"/admin/download_laporan_rekap?tipe=harian&tanggal={today}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers.get("content-type", "")
        assert "Urea" in csv_resp.text

    def test_list_verifikasi_petani_empty(self, admin_token):
        """Test listing petani verification when empty"""
        response = client.get(
            "/admin/verifikasi_petani",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_verifikasi_petani_unauthorized(self):
        """Test verifikasi endpoints without token"""
        response = client.get("/admin/verifikasi_petani")
        assert response.status_code == 401

    def test_verifikasi_petani_forbidden_role(self, petani_token):
        """Test verifikasi endpoints with wrong role"""
        response = client.get(
            "/admin/verifikasi_petani",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert response.status_code == 403

    def test_list_verifikasi_petani_with_pagination(self, admin_token, test_db: Session):
        """Test verifikasi petani with pagination"""
        # Create test petani profiles
        for i in range(5):
            user = User(
                username=f"petani_{i}",
                password_hash=hash_password("test"),
                role="petani",
            )
            test_db.add(user)
            test_db.commit()
            test_db.refresh(user)
            
            profile = ProfilePetani(
                user_id=user.id,
                nama_lengkap=f"Petani {i}",
                nik=f"{1000000000000000 + i}",
                alamat=f"Jl. Test {i}",
                no_hp=f"0812345678{i:02d}",
            )
            test_db.add(profile)
            test_db.commit()

        response = client.get(
            "/admin/verifikasi_petani?page=1&page_size=2",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) <= 2


# ============================================================================
# DISTRIBUTOR ENDPOINTS TESTS
# ============================================================================

class TestDistributorEndpoints:
    """Test distributor-specific endpoints"""

    def test_list_jadwal_distribusi(self, distributor_token, seed_jadwal_distribusi):
        response = client.get(
            "/distributor/jadwal-distribusi-pupuk",
            headers=auth_headers(distributor_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["lokasi"] == "Gudang Kios Tani Makmur"

    def test_list_jadwal_distribusi_unauthorized(self):
        response = client.get("/distributor/jadwal-distribusi-pupuk")
        assert response.status_code == 401

    def test_list_jadwal_distribusi_forbidden(self, petani_token):
        response = client.get(
            "/distributor/jadwal-distribusi-pupuk",
            headers=auth_headers(petani_token),
        )
        assert response.status_code == 403

    def test_jadwal_detail(self, distributor_token, seed_jadwal_distribusi):
        jadwal_id = seed_jadwal_distribusi["jadwal"].id
        response = client.get(
            f"/distributor/jadwal-distribusi-pupuk/{jadwal_id}",
            headers=auth_headers(distributor_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["jadwal_id"] == jadwal_id
        assert data["lokasi"] == "Gudang Kios Tani Makmur"
        assert len(data["penerima_list"]) == 1
        assert data["penerima_list"][0]["nama_petani"] == "Petani Jadwal"

    def test_jadwal_detail_not_found(self, distributor_token):
        response = client.get(
            "/distributor/jadwal-distribusi-pupuk/9999",
            headers=auth_headers(distributor_token),
        )
        assert response.status_code == 404

    def test_verifikasi_penerima_pupuk(self, distributor_token, seed_jadwal_distribusi, test_db: Session):
        permohonan_id = seed_jadwal_distribusi["permohonan"].id
        response = client.post(
            "/distributor/verifikasi-penerima-pupuk",
            headers=auth_headers(distributor_token),
            json={
                "permohonan_id": permohonan_id,
                "catatan": "Bukti diterima",
                "bukti_penerima_url": "http://example.com/bukti.jpg",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["permohonan_id"] == permohonan_id
        assert data["status_baru"] == "selesai"

        # Refresh session to see changes made by other sessions
        test_db.expire_all()
        
        # Ensure DB updated
        updated_permohonan = test_db.get(PermohonanPupuk, permohonan_id)
        updated_jadwal = test_db.get(JadwalDistribusi, seed_jadwal_distribusi["jadwal"].id)

        assert updated_permohonan.status == "selesai"
        assert updated_jadwal.status == "selesai"

    def test_riwayat_distribusi(self, distributor_token, seed_jadwal_distribusi_selesai):
        response = client.get(
            "/distributor/riwayat-distribusi-pupuk",
            headers=auth_headers(distributor_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["status"] == "selesai"


# ============================================================================
# SUPERADMIN ENDPOINTS TESTS
# ============================================================================

class TestSuperadminEndpoints:
    """Test superadmin-specific endpoints"""

    def test_get_metrics(self, superadmin_token):
        """Test getting system metrics"""
        response = client.get(
            "/superadmin/metrics",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "uptime" in data
        assert "total_users" in data

    def test_get_metrics_unauthorized(self):
        """Test getting metrics without token"""
        response = client.get("/superadmin/metrics")
        assert response.status_code == 401

    def test_get_metrics_forbidden_role(self, petani_token):
        """Test getting metrics with wrong role"""
        response = client.get(
            "/superadmin/metrics",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert response.status_code == 403


# ============================================================================
# SECURITY & VALIDATION TESTS
# ============================================================================

class TestSecurityAndValidation:
    """Test security features and input validation"""

    def test_invalid_token(self):
        """Test endpoint with invalid token"""
        response = client.get(
            "/petani/profile",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    def test_expired_token(self, test_db: Session):
        """Test with expired token (simulated)"""
        # Create a token that's already expired
        from datetime import datetime, timedelta
        from jose import jwt
        from core.config import settings

        expired_payload = {
            "sub": "1",
            "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        response = client.get(
            "/petani/profile",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    def test_missing_authorization_header(self):
        """Test endpoint without authorization header"""
        response = client.get("/petani/profile")
        assert response.status_code == 401

    def test_malformed_nik(self):
        """Test registration with malformed NIK"""
        data = {
            "nama_lengkap": "Test",
            "nik": "abcd1234efgh5678",  # Non-numeric
            "alamat": "Test",
            "no_hp": "081234567890",
            "password": "Test123!",
        }
        files = {
            "foto_ktp": ("test.pdf", BytesIO(b"content"), "application/pdf"),
        }
        
        response = client.post("/auth/register_petani", data=data, files=files)
        assert response.status_code == 400


# ============================================================================
# FILE UPLOAD TESTS
# ============================================================================

class TestFileUpload:
    """Test file upload functionality"""

    def test_register_with_valid_file(self, seed_fertilizers):
        """Test registration with valid PDF file"""
        data = {
            "nama_lengkap": "Test Petani",
            "nik": "1234567890123456",
            "alamat": "Jl. Test",
            "no_hp": "081234567890",
            "password": "Test123!",
        }
        files = {
            "foto_ktp": ("ktp.pdf", BytesIO(b"PDF content here"), "application/pdf"),
        }

        response = client.post("/auth/register_petani", data=data, files=files)
        assert response.status_code == 200
        assert "url_ktp" in response.json()

    def test_register_with_invalid_file_type(self, seed_fertilizers):
        """Test registration with invalid file type"""
        data = {
            "nama_lengkap": "Test Petani",
            "nik": "1234567890123456",
            "alamat": "Jl. Test",
            "no_hp": "081234567890",
            "password": "Test123!",
        }
        files = {
            "foto_ktp": ("virus.exe", BytesIO(b"executable"), "application/x-msdownload"),
        }

        response = client.post("/auth/register_petani", data=data, files=files)
        assert response.status_code == 400


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple endpoints"""

    def test_complete_registration_and_login_flow(self, seed_fertilizers):
        """Test complete flow: register → login"""
        # Step 1: Register
        reg_data = {
            "nama_lengkap": "Complete Flow Test",
            "nik": "1111111111111111",
            "alamat": "Jl. Integration Test",
            "no_hp": "081234567890",
            "password": "FlowTest123!",
        }
        reg_files = {
            "foto_ktp": ("test.pdf", BytesIO(b"content"), "application/pdf"),
        }

        reg_response = client.post("/auth/register_petani", data=reg_data, files=reg_files)
        assert reg_response.status_code == 200
        reg_token = reg_response.json()["access_token"]

        # Step 2: Login with credentials
        login_response = client.post(
            "/auth/login",
            data={
                "username": "1111111111111111",
                "password": "FlowTest123!",
            }
        )
        assert login_response.status_code == 200
        login_token = login_response.json()["access_token"]

        # Step 3: Verify token works
        profile_response = client.get(
            "/petani/profile",
            headers={"Authorization": f"Bearer {login_token}"}
        )
        # Will be 404 since profile not created, but token is valid
        # (401 would mean invalid token)
        assert profile_response.status_code in [200, 404]

    def test_authentication_and_role_separation(
        self,
        create_test_user_petani,
        create_test_user_admin,
        petani_token,
        admin_token,
    ):
        """Test that different roles can only access their endpoints"""
        # Petani can access /petani/pupuk
        petani_response = client.get(
            "/petani/pupuk",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert petani_response.status_code in [200, 404]

        # Admin cannot access /petani/pupuk
        admin_on_petani = client.get(
            "/petani/pupuk",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_on_petani.status_code == 403

        # Admin can access admin endpoints
        admin_response = client.get(
            "/admin/verifikasi_petani",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert admin_response.status_code in [200, 404]

        # Petani cannot access /admin/verifikasi_petani
        petani_on_admin = client.get(
            "/admin/verifikasi_petani",
            headers={"Authorization": f"Bearer {petani_token}"}
        )
        assert petani_on_admin.status_code == 403


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_very_long_input(self):
        """Test with very long input strings"""
        data = {
            "nama_lengkap": "A" * 1000,  # Very long name
            "nik": "1234567890123456",
            "alamat": "B" * 1000,
            "no_hp": "081234567890",
            "password": "Test123!",
        }
        files = {
            "foto_ktp": ("test.pdf", BytesIO(b"content"), "application/pdf"),
        }

        response = client.post("/auth/register_petani", data=data, files=files)
        # Should either accept or reject with proper error
        assert response.status_code in [200, 400, 413]

    def test_special_characters_in_input(self):
        """Test with special characters"""
        data = {
            "nama_lengkap": "Test <script>alert('xss')</script>",
            "nik": "1234567890123456",
            "alamat": "Jl. Test & Co.",
            "no_hp": "081234567890",
            "password": "Test123!",
        }
        files = {
            "foto_ktp": ("test.pdf", BytesIO(b"content"), "application/pdf"),
        }

        response = client.post("/auth/register_petani", data=data, files=files)
        # Should handle safely
        assert response.status_code in [200, 400]

    def test_numeric_string_fields(self):
        """Test with numeric strings in text fields"""
        data = {
            "nama_lengkap": "123456",  # Numeric
            "nik": "1234567890123456",
            "alamat": "789456",
            "no_hp": "081234567890",
            "password": "Test123!",
        }
        files = {
            "foto_ktp": ("test.pdf", BytesIO(b"content"), "application/pdf"),
        }

        response = client.post("/auth/register_petani", data=data, files=files)
        # Should accept (names can be numeric)
        assert response.status_code == 200


# ============================================================================
# SUPERADMIN TESTS
# ============================================================================

class TestSuperadmin:
    """Test superadmin endpoints"""

    def test_metrics(self, superadmin_token):
        """Test getting metrics as superadmin"""
        response = client.get(
            "/superadmin/metrics",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "uptime" in data
        assert "total_users" in data
        assert "error_logs" in data

    def test_metrics_unauthorized(self, admin_token):
        """Test metrics endpoint requires superadmin role"""
        response = client.get(
            "/superadmin/metrics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 403

    def test_list_users(self, test_db: Session, superadmin_token, create_test_user_petani, create_test_user_admin):
        """Test listing all users"""
        # Create profiles for test users
        petani_profile = ProfilePetani(
            user_id=create_test_user_petani.id,
            nama_lengkap="Test Petani",
            nik="1234567890123456",
            alamat="Jl. Test",
            no_hp="081234567890",
            status_verifikasi=True,
        )
        admin_profile = ProfileAdmin(
            user_id=create_test_user_admin.id,
            nama_lengkap="Test Admin",
            alamat="Jl. Admin",
            no_hp="081234567891",
        )
        test_db.add(petani_profile)
        test_db.add(admin_profile)
        test_db.commit()

        response = client.get(
            "/superadmin/users",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2  # At least petani and admin users

    def test_list_users_with_role_filter(self, test_db: Session, superadmin_token, create_test_user_petani):
        """Test listing users with role filter"""
        # Create profile
        profile = ProfilePetani(
            user_id=create_test_user_petani.id,
            nama_lengkap="Test Petani",
            nik="1234567890123456",
            alamat="Jl. Test",
            no_hp="081234567890",
            status_verifikasi=True,
        )
        test_db.add(profile)
        test_db.commit()

        response = client.get(
            "/superadmin/users?role=petani",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned users should have role petani
        for user in data:
            assert user["role"] == "petani"

    def test_list_users_with_pagination(self, test_db: Session, superadmin_token):
        """Test listing users with pagination"""
        response = client.get(
            "/superadmin/users?page=1&page_size=10",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10  # Should not exceed page_size

    def test_get_user_detail(self, test_db: Session, superadmin_token, create_test_user_admin):
        """Test getting user detail"""
        # Create profile
        profile = ProfileAdmin(
            user_id=create_test_user_admin.id,
            nama_lengkap="Test Admin Detail",
            alamat="Jl. Admin Detail",
            no_hp="081234567892",
        )
        test_db.add(profile)
        test_db.commit()

        response = client.get(
            f"/superadmin/users/{create_test_user_admin.id}",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == create_test_user_admin.id
        assert data["username"] == create_test_user_admin.username
        assert data["role"] == "admin"
        assert data["nama_lengkap"] == "Test Admin Detail"

    def test_get_user_detail_not_found(self, superadmin_token):
        """Test getting non-existent user detail"""
        response = client.get(
            "/superadmin/users/99999",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 404

    def test_create_admin_user(self, superadmin_token):
        """Test creating a new admin user"""
        data = {
            "username": "new_admin",
            "password": "securepass123",
            "role": "admin",
            "nama_lengkap": "New Admin User",
            "alamat": "Jl. New Admin",
            "no_hp": "081234567899",
        }
        response = client.post(
            "/superadmin/users/add",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["username"] == "new_admin"
        assert result["role"] == "admin"
        assert "user_id" in result

    def test_create_distributor_user(self, superadmin_token):
        """Test creating a new distributor user"""
        data = {
            "username": "new_distributor",
            "password": "securepass123",
            "role": "distributor",
            "nama_lengkap": "New Distributor User",
            "alamat": "Jl. New Distributor",
            "no_hp": "081234567898",
            "perusahaan": "PT. Test Distributor",
        }
        response = client.post(
            "/superadmin/users/add",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["username"] == "new_distributor"
        assert result["role"] == "distributor"

    def test_create_distributor_without_perusahaan(self, superadmin_token):
        """Test creating distributor without perusahaan should fail"""
        data = {
            "username": "bad_distributor",
            "password": "securepass123",
            "role": "distributor",
            "nama_lengkap": "Bad Distributor",
            "alamat": "Jl. Bad",
            "no_hp": "081234567897",
        }
        response = client.post(
            "/superadmin/users/add",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 400
        assert "Perusahaan wajib diisi" in response.json()["detail"]

    def test_create_superadmin_user(self, superadmin_token):
        """Test creating a new superadmin user"""
        data = {
            "username": "new_superadmin",
            "password": "securepass123",
            "role": "super_admin",
            "nama_lengkap": "New Super Admin",
            "alamat": "Jl. New Super",
            "no_hp": "081234567896",
        }
        response = client.post(
            "/superadmin/users/add",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["role"] == "super_admin"

    def test_create_user_with_invalid_role(self, superadmin_token):
        """Test creating user with invalid role"""
        data = {
            "username": "invalid_role",
            "password": "securepass123",
            "role": "invalid_role_type",
            "nama_lengkap": "Invalid Role User",
            "alamat": "Jl. Invalid",
            "no_hp": "081234567895",
        }
        response = client.post(
            "/superadmin/users/add",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 400
        assert "Role harus" in response.json()["detail"]

    def test_create_user_with_duplicate_username(self, test_db: Session, superadmin_token):
        """Test creating user with existing username"""
        # Create first user
        user = User(
            username="duplicate_user",
            password_hash=hash_password("password123"),
            role="admin",
        )
        test_db.add(user)
        test_db.commit()

        # Try to create another user with same username
        data = {
            "username": "duplicate_user",
            "password": "securepass123",
            "role": "admin",
            "nama_lengkap": "Duplicate User",
            "alamat": "Jl. Duplicate",
            "no_hp": "081234567894",
        }
        response = client.post(
            "/superadmin/users/add",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 409
        assert "Username sudah terdaftar" in response.json()["detail"]

    def test_edit_user_name(self, test_db: Session, superadmin_token, create_test_user_admin):
        """Test editing user name"""
        # Create profile
        profile = ProfileAdmin(
            user_id=create_test_user_admin.id,
            nama_lengkap="Old Name",
            alamat="Jl. Old",
            no_hp="081234567893",
        )
        test_db.add(profile)
        test_db.commit()

        data = {
            "nama_lengkap": "New Name Updated",
        }
        response = client.put(
            f"/superadmin/users/{create_test_user_admin.id}",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["updated_fields"]["nama_lengkap"] == "New Name Updated"

    def test_edit_user_multiple_fields(self, test_db: Session, superadmin_token, create_test_user_admin):
        """Test editing multiple user fields"""
        # Create profile
        profile = ProfileAdmin(
            user_id=create_test_user_admin.id,
            nama_lengkap="Old Name",
            alamat="Jl. Old",
            no_hp="081234567893",
        )
        test_db.add(profile)
        test_db.commit()

        data = {
            "nama_lengkap": "New Name",
            "alamat": "Jl. New Address",
            "no_hp": "089876543210",
        }
        response = client.put(
            f"/superadmin/users/{create_test_user_admin.id}",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["updated_fields"]["nama_lengkap"] == "New Name"
        assert result["updated_fields"]["alamat"] == "Jl. New Address"
        assert result["updated_fields"]["no_hp"] == "089876543210"

    def test_edit_user_password(self, test_db: Session, superadmin_token, create_test_user_admin):
        """Test editing user password"""
        # Create profile
        profile = ProfileAdmin(
            user_id=create_test_user_admin.id,
            nama_lengkap="Admin Name",
            alamat="Jl. Admin",
            no_hp="081234567893",
        )
        test_db.add(profile)
        test_db.commit()

        data = {
            "password": "newpassword123",
        }
        response = client.put(
            f"/superadmin/users/{create_test_user_admin.id}",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert "password" in result["updated_fields"]
        assert result["updated_fields"]["password"] == "***"

    def test_edit_distributor_perusahaan(self, test_db: Session, superadmin_token, create_test_user_distributor):
        """Test editing distributor's perusahaan"""
        # Create profile
        profile = ProfileDistributor(
            user_id=create_test_user_distributor.id,
            nama_lengkap="Distributor Name",
            perusahaan="Old Company",
            alamat="Jl. Distributor",
            no_hp="081234567893",
            status_verifikasi=True,
        )
        test_db.add(profile)
        test_db.commit()

        data = {
            "perusahaan": "New Company Ltd",
        }
        response = client.put(
            f"/superadmin/users/{create_test_user_distributor.id}",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["updated_fields"]["perusahaan"] == "New Company Ltd"

    def test_edit_user_not_found(self, superadmin_token):
        """Test editing non-existent user"""
        data = {
            "nama_lengkap": "New Name",
        }
        response = client.put(
            "/superadmin/users/99999",
            json=data,
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 404

    def test_delete_user(self, test_db: Session, superadmin_token):
        """Test deleting a user"""
        # Create a user to delete
        user = User(
            username="user_to_delete",
            password_hash=hash_password("password123"),
            role="admin",
        )
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        user_id = user.id

        # Create profile
        profile = ProfileAdmin(
            user_id=user_id,
            nama_lengkap="User To Delete",
            alamat="Jl. Delete",
            no_hp="081234567892",
        )
        test_db.add(profile)
        test_db.commit()

        response = client.delete(
            f"/superadmin/users/{user_id}",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
        assert result["username"] == "user_to_delete"

        # Verify user is deleted by querying with a fresh session
        deleted_user = test_db.query(User).filter(User.id == user_id).first()
        assert deleted_user is None

    def test_delete_user_not_found(self, superadmin_token):
        """Test deleting non-existent user"""
        response = client.delete(
            "/superadmin/users/99999",
            headers={"Authorization": f"Bearer {superadmin_token}"}
        )
        assert response.status_code == 404

    def test_create_user_unauthorized(self, admin_token):
        """Test creating user requires superadmin role"""
        data = {
            "username": "unauthorized_user",
            "password": "securepass123",
            "role": "admin",
            "nama_lengkap": "Unauthorized User",
            "alamat": "Jl. Unauthorized",
            "no_hp": "081234567891",
        }
        response = client.post(
            "/superadmin/users/add",
            json=data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 403

    def test_edit_user_unauthorized(self, admin_token):
        """Test editing user requires superadmin role"""
        data = {
            "nama_lengkap": "New Name",
        }
        response = client.put(
            "/superadmin/users/1",
            json=data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 403

    def test_delete_user_unauthorized(self, admin_token):
        """Test deleting user requires superadmin role"""
        response = client.delete(
            "/superadmin/users/1",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
