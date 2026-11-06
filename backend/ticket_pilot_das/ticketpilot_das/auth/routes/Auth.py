"""FastAPI routes for auth."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ticketpilot_das.auth.db_operations import Auth as auth_ops
from ticketpilot_das.auth.entity.PydanticModels import LoginRequest, LoginResponse
from ticketpilot_das.utils.CommonEnums import UserRole
from ticketpilot_das.utils.Database import get_db
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("auth.routes.Auth")

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Function: login
    Description: One shared login for both principals TicketPilot knows
        about -- tries the User table (support manager) first, then the
        Customer table, by email. Whichever matches gets a JWT with the
        matching role claim; the frontend reads `role` back to decide
        where to send them (manager dashboard vs customer self-service).
    Inputs: email, password.
    Outputs: access_token, user_id (really "subject id" -- a U_Id or a
        C_Id depending on role), role, name (customers only).
    Happy Flow: credentials match a manager OR a customer -> JWT issued.
    Error Flow: no match in either table, or a customer row with no
        password backfilled yet -> 401 (same error regardless of which
        case, so we don't reveal which emails exist or in which table).
    """
    try:
        log.info("POST login -- email=%s", payload.email)

        try:
            user = auth_ops.authenticate(db, payload.email, payload.password)
            token = auth_ops.create_access_token(user.U_Id, user.U_Role)
            return LoginResponse(access_token=token, user_id=user.U_Id, role=user.U_Role)
        except ValueError:
            pass  # not a manager -- fall through and try the customer table

        customer = auth_ops.authenticate_customer(db, payload.email, payload.password)
        token = auth_ops.create_access_token(customer.C_Id, UserRole.CUSTOMER.value)
        return LoginResponse(
            access_token=token,
            user_id=customer.C_Id,
            role=UserRole.CUSTOMER.value,
            name=customer.C_Name,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    except Exception as exc:
        log.error("Unexpected error during login for '%s': %s", payload.email, exc)
        raise HTTPException(status_code=500, detail="Login failed unexpectedly.")
