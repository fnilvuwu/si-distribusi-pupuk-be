from fastapi import APIRouter
from api.routes import auth, petani, admin, distributor, superadmin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
# Auth routes (prefix: /auth):
# - POST /register_petani - Register a new petani user account
# - POST /login - Authenticate user and get access token
# - POST /logout - Logout user (invalidate token)

# Petani routes (absolute paths per PRD):
# - GET /profile - Get current user's profile
# - POST /profile/update - Update user profile
# - GET /pupuk - Get available fertilizers
# - POST /pengajuan_pupuk - Submit fertilizer application
# - GET /pengajuan_pupuk/riwayat - Get application history
# - GET /pengambilan_pupuk/jadwal - Get fertilizer pickup schedule
# - POST /lapor_hasil_tani - Report harvest results
# - PATCH /pengajuan_pupuk/{permohonan_id}/konfirmasi - Confirm fertilizer application
api_router.include_router(petani.router, tags=["Petani"])

api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
# Admin routes (prefix: /admin):
# - GET /verifikasi_petani - List Verifikasi Petani
# - GET /verifikasi_petani/{petani_id} - Detail Verifikasi Petani
# - POST /verifikasi_petani/{petani_id}/approve - Approve Verifikasi Petani
# - POST /verifikasi_petani/{petani_id}/reject - Reject Verifikasi Petani
# - GET /verifikasi_hasil_tani - List Verifikasi Hasil Tani
# - GET /verifikasi_hasil_tani/{report_id} - Detail Verifikasi Hasil Tani
# - POST /verifikasi_hasil_tani/{report_id}/approve - Approve Verifikasi Hasil Tani
# - POST /verifikasi_hasil_tani/{report_id}/reject - Reject Verifikasi Hasil Tani

api_router.include_router(distributor.router, prefix="/distributor", tags=["Distributor"])
# Distributor routes (prefix: /distributor):
# - GET /jadwal-distribusi-pupuk - List jadwal distribusi pupuk
# - GET /jadwal-distribusi-pupuk/{jadwal_id} - Detail jadwal with penerima list
# - POST /verifikasi-penerima-pupuk - Verify penerima has received pupuk
# - GET /riwayat-distribusi-pupuk - Riwayat distribusi (default status selesai)

api_router.include_router(superadmin.router, prefix="/superadmin", tags=["SuperAdmin"])
# Superadmin routes (prefix: /superadmin):
# - GET /metrics - Get system metrics
