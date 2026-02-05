ADMIN
[🛠️] endpoint untuk admin acc pupuk itu harus ada atur jadwal pengambilan pupuk dimana dipilih dari admin/jadwal_distribusi_pupuk?page=1&page_size=50

saat ini masih hanya seperti ini belum ada event_id atau jadwal_id yang diambil dari admin/jadwal_distribusi_pupuk?page=1&page_size=50
[
  {
    "id": 2,
    "nama_acara": "Pembagian Pupuk Berkualitas Tinggi untuk Petani",
    "tanggal": "2026-02-25",
    "lokasi": "Balai Desa Makmur Jaya",
    "items": [
      {
        "pupuk_id": 4,
        "nama_pupuk": "NPK 16:16:16",
        "jumlah": 800,
        "satuan": "kg"
      },
      {
        "pupuk_id": 5,
        "nama_pupuk": "Pupuk Organik Kompos",
        "jumlah": 600,
        "satuan": "kg"
      }
    ]
  },
  {
    "id": 1,
    "nama_acara": "Pembagian Pupuk Musim Tanam Musim Hujan",
    "tanggal": "2026-02-15",
    "lokasi": "Lapangan Desa Suka Maju",
    "items": [
      {
        "pupuk_id": 1,
        "nama_pupuk": "Urea",
        "jumlah": 1000,
        "satuan": "kg"
      },
      {
        "pupuk_id": 2,
        "nama_pupuk": "TSP (Triple Super Phosphate)",
        "jumlah": 500,
        "satuan": "kg"
      }
    ]
  }
]

seharusnya jadi saling berelasi
[
  {
    "id": 0,
    "nama_petani": "string",
    "nama_pupuk": "string",
    "pupuk_id": 0,
    "jumlah_diminta": 0,
    "status": "string",
    "created_at": "string"
    "jadwal_id": 0,
  }
]

[ ] endpoint untuk edit admin profile