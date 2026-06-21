from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    api_keys: dict
    notify_configs: dict
    preferences: dict

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    api_keys: dict | None = None
    notify_configs: dict | None = None
    preferences: dict | None = None
