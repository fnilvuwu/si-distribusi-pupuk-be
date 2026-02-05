from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("role IN ('petani', 'admin', 'distributor', 'super_admin')"),
    )

    # Relationships
    profile_petani = relationship("ProfilePetani", back_populates="user", uselist=False)
    profile_distributor = relationship("ProfileDistributor", back_populates="user", uselist=False)
    profile_admin = relationship("ProfileAdmin", back_populates="user", uselist=False)
    profile_superadmin = relationship("ProfileSuperadmin", back_populates="user", uselist=False)

class ProfilePetani(Base):
    __tablename__ = "profile_petani"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    nama_lengkap = Column(String, nullable=False)
    nik = Column(String(16), unique=True, nullable=False)
    alamat = Column(Text, nullable=False)
    no_hp = Column(String, nullable=False)
    url_ktp = Column(Text)
    url_kartu_tani = Column(Text)
    status_verifikasi = Column(Boolean, default=False)

    # Relationship
    user = relationship("User", back_populates="profile_petani")
    permohonan_pupuk = relationship("PermohonanPupuk", back_populates="petani")

class ProfileDistributor(Base):
    __tablename__ = "profile_distributor"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    nama_lengkap = Column(String, nullable=False)
    perusahaan = Column(String, nullable=False)
    alamat = Column(Text, nullable=False)
    no_hp = Column(String, nullable=False)
    status_verifikasi = Column(Boolean, default=False)

    user = relationship("User", back_populates="profile_distributor")

class ProfileAdmin(Base):
    __tablename__ = "profile_admin"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    nama_lengkap = Column(String, nullable=False)
    alamat = Column(Text, nullable=False)
    no_hp = Column(String, nullable=False)

    user = relationship("User", back_populates="profile_admin")

class ProfileSuperadmin(Base):
    __tablename__ = "profile_superadmin"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    nama_lengkap = Column(String, nullable=False)
    alamat = Column(Text, nullable=False)
    no_hp = Column(String, nullable=False)

    user = relationship("User", back_populates="profile_superadmin")

class StokPupuk(Base):
    __tablename__ = "stok_pupuk"

    id = Column(Integer, primary_key=True, index=True)
    nama_pupuk = Column(String, unique=True, nullable=False)
    jumlah_stok = Column(Integer, default=0, nullable=False)
    satuan = Column(String, nullable=False)

    # Relationship
    permohonan_pupuk = relationship("PermohonanPupuk", back_populates="pupuk")
    riwayat_stock = relationship("RiwayatStockPupuk", back_populates="pupuk")


class RiwayatStockPupuk(Base):
    __tablename__ = "riwayat_stock_pupuk"

    id = Column(Integer, primary_key=True, index=True)
    pupuk_id = Column(Integer, ForeignKey("stok_pupuk.id", ondelete="RESTRICT"), nullable=False)
    tipe = Column(String, nullable=False)
    jumlah = Column(Integer, nullable=False)
    satuan = Column(String, nullable=False)
    catatan = Column(Text)
    admin_user_id = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("tipe IN ('tambah','kurangi')"),
    )

    pupuk = relationship("StokPupuk", back_populates="riwayat_stock")

class PermohonanPupuk(Base):
    __tablename__ = "pengajuan_pupuk"

    id = Column(Integer, primary_key=True, index=True)
    petani_id = Column(Integer, ForeignKey("profile_petani.user_id", ondelete="RESTRICT"), nullable=False)
    pupuk_id = Column(Integer, ForeignKey("stok_pupuk.id", ondelete="RESTRICT"), nullable=False)
    jumlah_diminta = Column(Integer, nullable=False)
    jumlah_disetujui = Column(Integer)
    status = Column(String, nullable=False)
    alasan = Column(Text)
    url_dokumen_pendukung = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'terverifikasi', 'dijadwalkan', 'dikirim', 'selesai', 'ditolak')"),
    )

    jadwal_event_id = Column(Integer, ForeignKey("jadwal_distribusi_event.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    petani = relationship("ProfilePetani", back_populates="permohonan_pupuk")
    pupuk = relationship("StokPupuk", back_populates="permohonan_pupuk")
    jadwal_distribusi = relationship("JadwalDistribusi", back_populates="permohonan", uselist=False)
    jadwal_event = relationship("JadwalDistribusiEvent")

class JadwalDistribusi(Base):
    __tablename__ = "jadwal_distribusi_pupuk"

    id = Column(Integer, primary_key=True, index=True)
    permohonan_id = Column(Integer, ForeignKey("pengajuan_pupuk.id", ondelete="CASCADE"), nullable=False)
    tanggal_pengiriman = Column(Date, nullable=False)
    lokasi = Column(Text, nullable=False)
    status = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('dijadwalkan', 'dikirim', 'selesai')"),
    )

    # Relationship
    permohonan = relationship("PermohonanPupuk", back_populates="jadwal_distribusi")

class HasilTani(Base):
    __tablename__ = "hasil_tani"

    id = Column(Integer, primary_key=True, index=True)
    petani_id = Column(Integer, ForeignKey("profile_petani.user_id", ondelete="RESTRICT"), nullable=False)
    jenis_tanaman = Column(Text, nullable=False)
    jumlah_hasil = Column(Integer, nullable=False)
    satuan = Column(Text, nullable=False)
    tanggal_panen = Column(Date, nullable=False)
    status_verifikasi = Column(Boolean, default=False)
    bukti_url = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class JadwalDistribusiEvent(Base):
    __tablename__ = "jadwal_distribusi_event"

    id = Column(Integer, primary_key=True, index=True)
    nama_acara = Column(String, nullable=False)
    tanggal = Column(Date, nullable=False)
    lokasi = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    items = relationship("JadwalDistribusiItem", back_populates="event")


class JadwalDistribusiItem(Base):
    __tablename__ = "jadwal_distribusi_item"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("jadwal_distribusi_event.id", ondelete="CASCADE"), nullable=False)
    pupuk_id = Column(Integer, ForeignKey("stok_pupuk.id", ondelete="RESTRICT"), nullable=False)
    jumlah = Column(Integer, nullable=False)
    satuan = Column(String, nullable=False)

    event = relationship("JadwalDistribusiEvent", back_populates="items")
    pupuk = relationship("StokPupuk")


class VerifikasiPenerimaPupuk(Base):
    __tablename__ = "verifikasi_penerima_pupuk"

    id = Column(Integer, primary_key=True, index=True)
    permohonan_id = Column(Integer, ForeignKey("pengajuan_pupuk.id", ondelete="CASCADE"), nullable=False)
    distributor_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    bukti_foto_url = Column(Text)
    catatan = Column(Text)
    tanggal_verifikasi = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    permohonan = relationship("PermohonanPupuk")
    distributor = relationship("User")