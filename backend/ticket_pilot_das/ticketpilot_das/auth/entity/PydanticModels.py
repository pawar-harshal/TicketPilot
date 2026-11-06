from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    # Customer.C_Name when role="customer" -- lets the frontend greet
    # them by name without a separate lookup. Managers have no display
    # name on the User row today, so this is None for role="support_manager".
    name: Optional[str] = None
