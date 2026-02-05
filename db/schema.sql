-- SIPUPUK Phase 1 schema (PostgreSQL)
-- Safe to run multiple times (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  username VARCHAR NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('petani', 'admin', 'distributor', 'super_admin')),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile_petani (
  user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  nama_lengkap VARCHAR NOT NULL,
  nik VARCHAR(16) NOT NULL UNIQUE,
  alamat TEXT NOT NULL,
  no_hp VARCHAR NOT NULL,
  url_ktp TEXT,
  url_kartu_tani TEXT,
  status_verifikasi BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS stok_pupuk (
  id BIGSERIAL PRIMARY KEY,
  nama_pupuk VARCHAR NOT NULL UNIQUE,
  jumlah_stok INTEGER NOT NULL DEFAULT 0,
  satuan VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS pengajuan_pupuk (
  id BIGSERIAL PRIMARY KEY,
  petani_id BIGINT NOT NULL REFERENCES profile_petani(user_id) ON DELETE RESTRICT,
  pupuk_id BIGINT NOT NULL REFERENCES stok_pupuk(id) ON DELETE RESTRICT,
  jumlah_diminta INTEGER NOT NULL,
  jumlah_disetujui INTEGER,
  status TEXT NOT NULL CHECK (status IN ('pending', 'terverifikasi', 'dijadwalkan', 'dikirim', 'selesai', 'ditolak', 'dibatalkan')),
  alasan TEXT,
  url_dokumen_pendukung TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  jadwal_event_id BIGINT REFERENCES jadwal_distribusi_event(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS jadwal_distribusi_pupuk (
  id BIGSERIAL PRIMARY KEY,
  permohonan_id BIGINT NOT NULL REFERENCES pengajuan_pupuk(id) ON DELETE CASCADE,
  tanggal_pengiriman DATE NOT NULL,
  lokasi TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('dijadwalkan', 'dikirim', 'selesai'))
);

CREATE TABLE IF NOT EXISTS hasil_tani (
  id BIGSERIAL PRIMARY KEY,
  petani_id BIGINT NOT NULL REFERENCES profile_petani(user_id) ON DELETE RESTRICT,
  jenis_tanaman TEXT NOT NULL,
  jumlah_hasil INTEGER NOT NULL,
  satuan TEXT NOT NULL,
  tanggal_panen DATE NOT NULL,
  status_verifikasi BOOLEAN NOT NULL DEFAULT FALSE,
  bukti_url TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Event-based distribution schedule
CREATE TABLE IF NOT EXISTS jadwal_distribusi_event (
  id BIGSERIAL PRIMARY KEY,
  nama_acara VARCHAR NOT NULL,
  tanggal DATE NOT NULL,
  lokasi TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS jadwal_distribusi_item (
  id BIGSERIAL PRIMARY KEY,
  event_id BIGINT NOT NULL REFERENCES jadwal_distribusi_event(id) ON DELETE CASCADE,
  pupuk_id BIGINT NOT NULL REFERENCES stok_pupuk(id) ON DELETE RESTRICT,
  jumlah INTEGER NOT NULL,
  satuan VARCHAR NOT NULL
);

-- Preferred Indonesian naming (alias tables) for events
CREATE TABLE IF NOT EXISTS acara_distribusi_pupuk (
  id BIGSERIAL PRIMARY KEY,
  nama_acara VARCHAR NOT NULL,
  tanggal DATE NOT NULL,
  lokasi TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS acara_distribusi_item (
  id BIGSERIAL PRIMARY KEY,
  acara_id BIGINT NOT NULL REFERENCES acara_distribusi_pupuk(id) ON DELETE CASCADE,
  pupuk_id BIGINT NOT NULL REFERENCES stok_pupuk(id) ON DELETE RESTRICT,
  jumlah INTEGER NOT NULL,
  satuan VARCHAR NOT NULL
);

-- Riwayat perubahan stok pupuk
CREATE TABLE IF NOT EXISTS riwayat_stock_pupuk (
  id BIGSERIAL PRIMARY KEY,
  pupuk_id BIGINT NOT NULL REFERENCES stok_pupuk(id) ON DELETE RESTRICT,
  tipe VARCHAR NOT NULL CHECK (tipe IN ('tambah','kurangi')),
  jumlah INTEGER NOT NULL,
  satuan VARCHAR NOT NULL,
  catatan TEXT,
  admin_user_id BIGINT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);


-- Verifikasi penerima pupuk oleh distributor
CREATE TABLE IF NOT EXISTS verifikasi_penerima_pupuk (
  id BIGSERIAL PRIMARY KEY,
  permohonan_id BIGINT NOT NULL REFERENCES pengajuan_pupuk(id) ON DELETE CASCADE,
  distributor_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  bukti_foto_url TEXT,
  catatan TEXT,
  tanggal_verifikasi TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

