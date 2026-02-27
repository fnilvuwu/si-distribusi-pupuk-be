import os
import uuid
import logging
from pathlib import Path
from fastapi import HTTPException, UploadFile

logger = logging.getLogger(__name__)

# Allowed file extensions for security
ALLOWED_EXTENSIONS = {
    "ktp": {".jpg", ".jpeg", ".png", ".pdf"},
    "kartu_tani": {".jpg", ".jpeg", ".png", ".pdf"},
    "pengajuan_pupuk": {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"},
}


def save_upload_file(file: UploadFile, subdir: str) -> str:
    """
    Save uploaded file to the specified subdirectory.
    Includes security checks and proper error handling.

    Args:
        file: The uploaded file
        subdir: Subdirectory under 'uploads/' (e.g., 'ktp', 'kartu_tani')

    Returns:
        URL path to access the file

    Raises:
        HTTPException: If file is invalid or cannot be saved
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="File tidak valid")

    # Validate file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_exts = ALLOWED_EXTENSIONS.get(subdir, {".pdf", ".jpg", ".jpeg", ".png"})
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Tipe file tidak didukung. Izinkan: {', '.join(allowed_exts)}",
        )

    # Create directory
    if os.getenv("VERCEL"):
        uploads_root = Path("/tmp/uploads") / subdir
    else:
        uploads_root = Path("tmp/uploads") / subdir
    try:
        uploads_root.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating upload directory: {str(e)}")
        raise HTTPException(status_code=500, detail="Gagal membuat direktori upload")

    # Generate unique filename to avoid collisions
    # Format: <timestamp>_<uuid4>_<original_name>
    stem = os.path.splitext(file.filename)[0]
    # Remove special characters from original name
    safe_stem = "".join(c for c in stem if c.isalnum() or c in "._-").strip()
    if not safe_stem:
        safe_stem = "file"

    unique_id = str(uuid.uuid4())[:8]
    out_filename = f"{safe_stem}_{unique_id}{file_ext}"
    out_path = uploads_root / out_filename

    # Save file with error handling
    try:
        with out_path.open("wb") as f:
            content = file.file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="File kosong")
            f.write(content)

        logger.info(f"File saved successfully: {out_path}")
        return f"/uploads/{subdir}/{out_filename}"

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        # Cleanup partial file
        try:
            if out_path.exists():
                out_path.unlink()
        except:
            pass
        raise HTTPException(status_code=500, detail="Gagal menyimpan file")
