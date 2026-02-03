"""
Comprehensive Test Suite for SI Distribusi Pupuk Database
Tests all entities, relationships, and database operations
"""

import pytest
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.models import (
    Base, User, ProfilePetani, ProfileDistributor, ProfileAdmin, 
    ProfileSuperadmin, StokPupuk, PermohonanPupuk, JadwalDistribusi, 
    HasilTani, JadwalDistribusiEvent, JadwalDistribusiItem, 
    RiwayatStockPupuk, VerifikasiPenerimaPupuk
)
from core.security import hash_password

# ============================================================================
# DATABASE SETUP
# ============================================================================

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    """Reset database before each test"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Session:
    """Provide test database session"""
    session = TestingSessionLocal()
    yield session
    session.close()


# ============================================================================
# HELPER FIXTURES - CREATE TEST DATA
# ============================================================================

@pytest.fixture
def users(db: Session):
    """Create test users with different roles"""
    users_list = [
        User(username="petani001", password_hash=hash_password("pass123"), role="petani"),
        User(username="petani002", password_hash=hash_password("pass123"), role="petani"),
        User(username="distributor001", password_hash=hash_password("pass123"), role="distributor"),
        User(username="admin001", password_hash=hash_password("pass123"), role="admin"),
        User(username="superadmin001", password_hash=hash_password("pass123"), role="super_admin"),
    ]
    db.add_all(users_list)
    db.commit()
    for user in users_list:
        db.refresh(user)
    return users_list


@pytest.fixture
def petani_profiles(db: Session, users):
    """Create petani profiles"""
    profiles = [
        ProfilePetani(
            user_id=users[0].id,
            nama_lengkap="Budi Santoso",
            nik="3201111234567890",
            alamat="Desa Suka Maju",
            no_hp="081234567890",
            status_verifikasi=True
        ),
        ProfilePetani(
            user_id=users[1].id,
            nama_lengkap="Siti Nurhaliza",
            nik="3201111234567891",
            alamat="Desa Makmur Jaya",
            no_hp="081234567891",
            status_verifikasi=False
        ),
    ]
    db.add_all(profiles)
    db.commit()
    for profile in profiles:
        db.refresh(profile)
    return profiles


@pytest.fixture
def distributor_profiles(db: Session, users):
    """Create distributor profiles"""
    profile = ProfileDistributor(
        user_id=users[2].id,
        nama_lengkap="Anto Kuswoyo",
        perusahaan="PT Pupuk Indonesia",
        alamat="Jl. Industri No. 123",
        no_hp="082234567890",
        status_verifikasi=True
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def admin_profile(db: Session, users):
    """Create admin profile"""
    profile = ProfileAdmin(
        user_id=users[3].id,
        nama_lengkap="Yudi Pranoto",
        alamat="Kantor Desa",
        no_hp="083234567890"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def superadmin_profile(db: Session, users):
    """Create superadmin profile"""
    profile = ProfileSuperadmin(
        user_id=users[4].id,
        nama_lengkap="Bambang Sutrisno",
        alamat="Kantor Pusat",
        no_hp="083234567899"
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def fertilizers(db: Session):
    """Create fertilizer items"""
    ferts = [
        StokPupuk(nama_pupuk="Urea", jumlah_stok=5000, satuan="kg"),
        StokPupuk(nama_pupuk="TSP", jumlah_stok=3000, satuan="kg"),
        StokPupuk(nama_pupuk="KCl", jumlah_stok=2500, satuan="kg"),
        StokPupuk(nama_pupuk="NPK 16:16:16", jumlah_stok=4000, satuan="kg"),
    ]
    db.add_all(ferts)
    db.commit()
    for fert in ferts:
        db.refresh(fert)
    return ferts


@pytest.fixture
def permohonan_list(db: Session, petani_profiles, fertilizers):
    """Create fertilizer requests"""
    requests = [
        PermohonanPupuk(
            petani_id=petani_profiles[0].user_id,
            pupuk_id=fertilizers[0].id,
            jumlah_diminta=300,
            jumlah_disetujui=280,
            status="terverifikasi",
            alasan="Kebutuhan musim tanam",
            created_at=datetime.now()
        ),
        PermohonanPupuk(
            petani_id=petani_profiles[1].user_id,
            pupuk_id=fertilizers[1].id,
            jumlah_diminta=200,
            jumlah_disetujui=None,
            status="pending",
            alasan="Pemupukan lanjutan",
            created_at=datetime.now()
        ),
    ]
    db.add_all(requests)
    db.commit()
    for req in requests:
        db.refresh(req)
    return requests


# ============================================================================
# TESTS: USER ENTITY
# ============================================================================

class TestUserEntity:
    """Test User model and creation"""
    
    def test_user_creation(self, db: Session):
        """Test creating a user"""
        user = User(
            username="testuser",
            password_hash=hash_password("password123"),
            role="petani"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == "petani"
        assert user.created_at is not None
    
    def test_user_unique_username(self, db: Session):
        """Test that username must be unique"""
        user1 = User(username="duplicate", password_hash=hash_password("pass1"), role="petani")
        user2 = User(username="duplicate", password_hash=hash_password("pass2"), role="admin")
        
        db.add(user1)
        db.commit()
        db.add(user2)
        
        with pytest.raises(Exception):  # IntegrityError
            db.commit()
    
    def test_user_role_validation(self, db: Session, users):
        """Test that only valid roles are allowed"""
        valid_roles = ["petani", "admin", "distributor", "super_admin"]
        
        for user in users:
            assert user.role in valid_roles


# ============================================================================
# TESTS: PETANI PROFILE
# ============================================================================

class TestPetaniProfile:
    """Test ProfilePetani model"""
    
    def test_petani_profile_creation(self, db: Session, users):
        """Test creating a petani profile"""
        profile = ProfilePetani(
            user_id=users[0].id,
            nama_lengkap="Budi Santoso",
            nik="3201111234567890",
            alamat="Desa Suka Maju",
            no_hp="081234567890",
            status_verifikasi=False
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        assert profile.user_id == users[0].id
        assert profile.nama_lengkap == "Budi Santoso"
        assert profile.status_verifikasi == False
    
    def test_petani_nik_unique(self, db: Session, users):
        """Test that NIK must be unique"""
        profile1 = ProfilePetani(
            user_id=users[0].id,
            nama_lengkap="Petani 1",
            nik="3201111234567890",
            alamat="Desa 1",
            no_hp="081234567890"
        )
        db.add(profile1)
        db.commit()
        
        profile2 = ProfilePetani(
            user_id=users[1].id,
            nama_lengkap="Petani 2",
            nik="3201111234567890",  # Duplicate NIK
            alamat="Desa 2",
            no_hp="081234567891"
        )
        db.add(profile2)
        
        with pytest.raises(Exception):  # IntegrityError
            db.commit()
    
    def test_petani_verification_status(self, db: Session, petani_profiles):
        """Test petani verification status"""
        verified = petani_profiles[0]
        unverified = petani_profiles[1]
        
        assert verified.status_verifikasi == True
        assert unverified.status_verifikasi == False
    
    def test_petani_permohonan_relationship(self, db: Session, permohonan_list, petani_profiles):
        """Test petani-permohonan relationship"""
        petani = db.query(ProfilePetani).filter_by(
            user_id=petani_profiles[0].user_id
        ).first()
        
        assert len(petani.permohonan_pupuk) > 0
        assert petani.permohonan_pupuk[0].pupuk_id == 1


# ============================================================================
# TESTS: FERTILIZER (STOK PUPUK)
# ============================================================================

class TestFertilizer:
    """Test StokPupuk model"""
    
    def test_fertilizer_creation(self, db: Session):
        """Test creating a fertilizer"""
        fert = StokPupuk(
            nama_pupuk="Urea",
            jumlah_stok=1000,
            satuan="kg"
        )
        db.add(fert)
        db.commit()
        db.refresh(fert)
        
        assert fert.id is not None
        assert fert.nama_pupuk == "Urea"
        assert fert.jumlah_stok == 1000
    
    def test_fertilizer_name_unique(self, db: Session):
        """Test that fertilizer name must be unique"""
        fert1 = StokPupuk(nama_pupuk="Urea", jumlah_stok=1000, satuan="kg")
        db.add(fert1)
        db.commit()
        
        fert2 = StokPupuk(nama_pupuk="Urea", jumlah_stok=500, satuan="kg")
        db.add(fert2)
        
        with pytest.raises(Exception):  # IntegrityError
            db.commit()
    
    def test_fertilizer_stock_update(self, db: Session, fertilizers):
        """Test updating fertilizer stock"""
        fert = fertilizers[0]
        initial_stock = fert.jumlah_stok
        
        fert.jumlah_stok = initial_stock - 100
        db.commit()
        
        db.refresh(fert)
        assert fert.jumlah_stok == initial_stock - 100
    
    def test_multiple_fertilizers(self, db: Session, fertilizers):
        """Test that multiple fertilizers can be stored"""
        count = db.query(StokPupuk).count()
        assert count == 4


# ============================================================================
# TESTS: PERMOHONAN PUPUK (REQUESTS)
# ============================================================================

class TestPermohonanPupuk:
    """Test PermohonanPupuk model"""
    
    def test_permohonan_creation(self, db: Session, petani_profiles, fertilizers):
        """Test creating a fertilizer request"""
        req = PermohonanPupuk(
            petani_id=petani_profiles[0].user_id,
            pupuk_id=fertilizers[0].id,
            jumlah_diminta=500,
            jumlah_disetujui=400,
            status="terverifikasi",
            alasan="Kebutuhan tanam"
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        
        assert req.id is not None
        assert req.jumlah_diminta == 500
        assert req.jumlah_disetujui == 400
    
    def test_permohonan_status_values(self, db: Session, permohonan_list):
        """Test that requests have valid status values"""
        valid_statuses = ["pending", "terverifikasi", "dijadwalkan", "dikirim", "selesai"]
        
        for req in permohonan_list:
            assert req.status in valid_statuses
    
    def test_permohonan_status_progression(self, db: Session, petani_profiles, fertilizers):
        """Test status progression through workflow"""
        req = PermohonanPupuk(
            petani_id=petani_profiles[0].user_id,
            pupuk_id=fertilizers[0].id,
            jumlah_diminta=100,
            status="pending"
        )
        db.add(req)
        db.commit()
        
        # Simulate status changes
        req.status = "terverifikasi"
        db.commit()
        
        req.status = "dijadwalkan"
        db.commit()
        
        req.status = "dikirim"
        db.commit()
        
        req.status = "selesai"
        db.commit()
        db.refresh(req)
        
        assert req.status == "selesai"
    
    def test_permohonan_relationships(self, db: Session, permohonan_list):
        """Test permohonan relationships with petani and pupuk"""
        req = permohonan_list[0]
        
        assert req.petani is not None
        assert req.pupuk is not None
        assert req.petani.nama_lengkap == "Budi Santoso"


# ============================================================================
# TESTS: JADWAL DISTRIBUSI
# ============================================================================

class TestJadwalDistribusi:
    """Test JadwalDistribusi model"""
    
    def test_jadwal_creation(self, db: Session, permohonan_list):
        """Test creating a distribution schedule"""
        jadwal = JadwalDistribusi(
            permohonan_id=permohonan_list[0].id,
            tanggal_pengiriman=date.today() + timedelta(days=5),
            lokasi="Gudang Desa",
            status="dijadwalkan"
        )
        db.add(jadwal)
        db.commit()
        db.refresh(jadwal)
        
        assert jadwal.id is not None
        assert jadwal.status == "dijadwalkan"
    
    def test_jadwal_status_values(self, db: Session):
        """Test that jadwal has valid status values"""
        valid_statuses = ["dijadwalkan", "dikirim", "selesai"]
        
        jadwal = JadwalDistribusi(
            permohonan_id=1,
            tanggal_pengiriman=date.today(),
            lokasi="Test",
            status="dijadwalkan"
        )
        
        assert jadwal.status in valid_statuses
    
    def test_jadwal_date_tracking(self, db: Session, permohonan_list):
        """Test that dates are properly tracked"""
        jadwal = JadwalDistribusi(
            permohonan_id=permohonan_list[0].id,
            tanggal_pengiriman=date(2025, 1, 31),
            lokasi="Test Location",
            status="dijadwalkan"
        )
        db.add(jadwal)
        db.commit()
        db.refresh(jadwal)
        
        assert jadwal.tanggal_pengiriman == date(2025, 1, 31)


# ============================================================================
# TESTS: HASIL TANI (HARVEST)
# ============================================================================

class TestHasilTani:
    """Test HasilTani model"""
    
    def test_hasil_tani_creation(self, db: Session, petani_profiles):
        """Test creating a harvest record"""
        hasil = HasilTani(
            petani_id=petani_profiles[0].user_id,
            jenis_tanaman="Padi",
            jumlah_hasil=5000,
            satuan="kg",
            tanggal_panen=date.today(),
            created_at=datetime.now()
        )
        db.add(hasil)
        db.commit()
        db.refresh(hasil)
        
        assert hasil.id is not None
        assert hasil.jenis_tanaman == "Padi"
        assert hasil.jumlah_hasil == 5000
    
    def test_harvest_multiple_crops(self, db: Session, petani_profiles):
        """Test recording multiple harvest types per petani"""
        crops = [
            HasilTani(
                petani_id=petani_profiles[0].user_id,
                jenis_tanaman="Padi",
                jumlah_hasil=5000,
                satuan="kg",
                tanggal_panen=date.today()
            ),
            HasilTani(
                petani_id=petani_profiles[0].user_id,
                jenis_tanaman="Jagung",
                jumlah_hasil=3000,
                satuan="kg",
                tanggal_panen=date.today()
            ),
        ]
        db.add_all(crops)
        db.commit()
        
        petani = db.query(ProfilePetani).filter_by(
            user_id=petani_profiles[0].user_id
        ).first()
        
        # Note: HasilTani doesn't have back_populates, so we query directly
        harvests = db.query(HasilTani).filter_by(petani_id=petani.user_id).all()
        assert len(harvests) == 2


# ============================================================================
# TESTS: RIWAYAT STOCK PUPUK
# ============================================================================

class TestRiwayatStockPupuk:
    """Test RiwayatStockPupuk model"""
    
    def test_stock_history_tambah(self, db: Session, fertilizers, users):
        """Test recording stock increase"""
        riwayat = RiwayatStockPupuk(
            pupuk_id=fertilizers[0].id,
            tipe="tambah",
            jumlah=1000,
            satuan="kg",
            catatan="Stock dari gudang pusat",
            admin_user_id=users[3].id
        )
        db.add(riwayat)
        db.commit()
        db.refresh(riwayat)
        
        assert riwayat.tipe == "tambah"
        assert riwayat.jumlah == 1000
    
    def test_stock_history_kurangi(self, db: Session, fertilizers, users):
        """Test recording stock decrease"""
        riwayat = RiwayatStockPupuk(
            pupuk_id=fertilizers[0].id,
            tipe="kurangi",
            jumlah=500,
            satuan="kg",
            catatan="Penyerahan untuk permohonan",
            admin_user_id=users[3].id
        )
        db.add(riwayat)
        db.commit()
        db.refresh(riwayat)
        
        assert riwayat.tipe == "kurangi"
        assert riwayat.jumlah == 500
    
    def test_stock_history_timeline(self, db: Session, fertilizers, users):
        """Test stock history timeline"""
        # Initial stock
        initial = RiwayatStockPupuk(
            pupuk_id=fertilizers[0].id,
            tipe="tambah",
            jumlah=5000,
            satuan="kg",
            admin_user_id=users[3].id
        )
        db.add(initial)
        db.commit()
        
        # Decrease
        decrease = RiwayatStockPupuk(
            pupuk_id=fertilizers[0].id,
            tipe="kurangi",
            jumlah=1000,
            satuan="kg",
            admin_user_id=users[3].id
        )
        db.add(decrease)
        db.commit()
        
        history = db.query(RiwayatStockPupuk).filter_by(
            pupuk_id=fertilizers[0].id
        ).order_by(RiwayatStockPupuk.created_at).all()
        
        assert len(history) == 2
        assert history[0].tipe == "tambah"
        assert history[1].tipe == "kurangi"


# ============================================================================
# TESTS: JADWAL DISTRIBUSI EVENT
# ============================================================================

class TestJadwalDistribusiEvent:
    """Test JadwalDistribusiEvent model"""
    
    def test_event_creation(self, db: Session):
        """Test creating an event"""
        event = JadwalDistribusiEvent(
            nama_acara="Pembagian Pupuk Musim Tanam",
            tanggal=date.today() + timedelta(days=10),
            lokasi="Lapangan Desa"
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        
        assert event.id is not None
        assert event.nama_acara == "Pembagian Pupuk Musim Tanam"
    
    def test_event_with_items(self, db: Session, fertilizers):
        """Test event with multiple items"""
        event = JadwalDistribusiEvent(
            nama_acara="Pembagian Pupuk",
            tanggal=date.today() + timedelta(days=10),
            lokasi="Lapangan Desa"
        )
        db.add(event)
        db.flush()
        
        items = [
            JadwalDistribusiItem(
                event_id=event.id,
                pupuk_id=fertilizers[0].id,
                jumlah=1000,
                satuan="kg"
            ),
            JadwalDistribusiItem(
                event_id=event.id,
                pupuk_id=fertilizers[1].id,
                jumlah=500,
                satuan="kg"
            ),
        ]
        db.add_all(items)
        db.commit()
        
        db.refresh(event)
        assert len(event.items) == 2


# ============================================================================
# TESTS: VERIFIKASI PENERIMA PUPUK
# ============================================================================

class TestVerifikasiPenerimaPupuk:
    """Test VerifikasiPenerimaPupuk model"""
    
    def test_verifikasi_creation(self, db: Session, permohonan_list, users):
        """Test creating a verification record"""
        verif = VerifikasiPenerimaPupuk(
            permohonan_id=permohonan_list[0].id,
            distributor_id=users[2].id,
            bukti_foto_url="https://example.com/bukti.jpg",
            catatan="Pupuk diterima dengan baik"
        )
        db.add(verif)
        db.commit()
        db.refresh(verif)
        
        assert verif.id is not None
        assert verif.catatan == "Pupuk diterima dengan baik"
        assert verif.tanggal_verifikasi is not None
    
    def test_verifikasi_relationships(self, db: Session, permohonan_list, users):
        """Test verification relationships"""
        verif = VerifikasiPenerimaPupuk(
            permohonan_id=permohonan_list[0].id,
            distributor_id=users[2].id,
            catatan="Test"
        )
        db.add(verif)
        db.commit()
        
        # Verify relationships work
        assert verif.permohonan is not None
        assert verif.distributor is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestDatabaseIntegration:
    """Integration tests for complete workflows"""
    
    def test_complete_request_workflow(self, db: Session, petani_profiles, fertilizers, users):
        """Test complete workflow from request to verification"""
        # 1. Create request
        req = PermohonanPupuk(
            petani_id=petani_profiles[0].user_id,
            pupuk_id=fertilizers[0].id,
            jumlah_diminta=300,
            jumlah_disetujui=280,
            status="pending"
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        
        # 2. Verify request
        req.status = "terverifikasi"
        db.commit()
        
        # 3. Schedule delivery
        req.status = "dijadwalkan"
        jadwal = JadwalDistribusi(
            permohonan_id=req.id,
            tanggal_pengiriman=date.today() + timedelta(days=5),
            lokasi="Gudang Desa",
            status="dijadwalkan"
        )
        db.add(jadwal)
        db.commit()
        db.refresh(jadwal)
        
        # 4. Record delivery
        req.status = "dikirim"
        jadwal.status = "dikirim"
        db.commit()
        
        # 5. Verify receipt
        verif = VerifikasiPenerimaPupuk(
            permohonan_id=req.id,
            distributor_id=users[2].id,
            bukti_foto_url="https://example.com/bukti.jpg",
            catatan="Diterima dengan baik"
        )
        db.add(verif)
        req.status = "selesai"
        jadwal.status = "selesai"
        db.commit()
        
        # Verify complete workflow
        db.refresh(req)
        assert req.status == "selesai"
        assert jadwal.status == "selesai"
        assert verif.id is not None
    
    def test_stock_tracking_workflow(self, db: Session, fertilizers, users):
        """Test stock tracking through operations"""
        initial_stock = fertilizers[0].jumlah_stok
        
        # Record stock history
        history = RiwayatStockPupuk(
            pupuk_id=fertilizers[0].id,
            tipe="tambah",
            jumlah=500,
            satuan="kg",
            admin_user_id=users[3].id
        )
        db.add(history)
        
        # Update stock
        fertilizers[0].jumlah_stok += 500
        db.commit()
        
        db.refresh(fertilizers[0])
        assert fertilizers[0].jumlah_stok == initial_stock + 500
    
    def test_data_count_verification(self, db: Session, users, petani_profiles, fertilizers, permohonan_list):
        """Verify all seeded data is properly stored"""
        user_count = db.query(User).count()
        petani_count = db.query(ProfilePetani).count()
        fert_count = db.query(StokPupuk).count()
        req_count = db.query(PermohonanPupuk).count()
        
        assert user_count > 0
        assert petani_count > 0
        assert fert_count > 0
        assert req_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
