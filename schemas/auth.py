from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    role: str
    full_name: str | None = None

class RegisterRequest(BaseModel):
    username: str
    password: str
    nama_lengkap: str
    nik: str
    alamat: str
    no_hp: str
