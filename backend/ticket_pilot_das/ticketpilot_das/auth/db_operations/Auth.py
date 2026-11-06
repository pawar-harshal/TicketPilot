"""
Lightweight auth, living inside this same package rather than a separate
auth-server microservice (that was explicitly skipped as too much work for
a solo MVP -- see design doc). One shared JWT format and one shared
/auth/login endpoint cover TWO different kinds of principal, backed by
two different tables:
  - a support manager -- a User row, role "support_manager".
  - a customer -- a Customer row, role "customer".
login() (auth.routes.Auth) tries User by email first, then Customer, and
issues the same kind of token either way; only the "role" claim and which
table get_current_user/get_current_customer load from differ. Routes that
are manager-only depend on get_current_user; routes that are customer-only
depend on get_current_customer; a route that's public to BOTH kinds of
logged-in principal (none currently need that) would depend on whichever
one applies after checking the token's role claim itself.
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ticketpilot_das.auth.entity.DbModels import User
from ticketpilot_das.ticket_management.entity.DbModels import Customer
from ticketpilot_das.utils import Configuration
from ticketpilot_das.utils.CommonEnums import UserRole
from ticketpilot_das.utils.Database import get_db
from ticketpilot_das.utils.Logger import get_logger

log = get_logger("auth.db_operations.Auth")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Same scheme, but doesn't 401 on its own when there's no token -- for
# routes that behave differently depending on WHICH kind of principal is
# logged in (or whether anyone is), e.g. getTickets (manager sees
# everyone's tickets, a customer sees only their own). Those routes read
# the token themselves and call get_current_user/get_current_customer
# only once they've decided which applies.
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(plain_password: str) -> str:
    try:
        return pwd_context.hash(plain_password)
    except Exception as exc:
        log.error("Password hashing failed: %s", exc)
        raise


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception as exc:
        log.error("Password verification failed: %s", exc)
        raise


def authenticate(db: Session, email: str, password: str) -> User:
    """Support-manager login (User table)."""
    try:
        user = db.query(User).filter(User.U_Email == email).first()
        if user is None or not verify_password(password, user.U_PasswordHash):
            log.warning("Failed manager login attempt for email '%s'.", email)
            raise ValueError("Invalid email or password.")
        log.info("User %s (%s) logged in.", user.U_Id, email)
        return user
    except ValueError:
        raise
    except Exception as exc:
        log.error("Unexpected error while authenticating user '%s': %s", email, exc)
        raise


def authenticate_customer(db: Session, email: str, password: str) -> Customer:
    """Customer login (Customer table). A customer with no
    C_PasswordHash backfilled yet (nullable -- see DbModels.Customer)
    can never log in, same error as a wrong password so we don't leak
    which emails exist either way."""
    try:
        customer = db.query(Customer).filter(Customer.C_Email == email).first()
        if (
            customer is None
            or not customer.C_PasswordHash
            or not verify_password(password, customer.C_PasswordHash)
        ):
            log.warning("Failed customer login attempt for email '%s'.", email)
            raise ValueError("Invalid email or password.")
        log.info("Customer %s (%s) logged in.", customer.C_Id, email)
        return customer
    except ValueError:
        raise
    except Exception as exc:
        log.error("Unexpected error while authenticating customer '%s': %s", email, exc)
        raise


def create_access_token(subject_id: int, role: str) -> str:
    """Issues a token for EITHER kind of principal -- subject_id is a
    User.U_Id or a Customer.C_Id depending on `role`; the two id spaces
    are independent, so the role claim is what get_current_user/
    get_current_customer rely on to know which table to check, not just
    which one they'd prefer."""
    try:
        payload = {
            "sub": str(subject_id),
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=Configuration.JWT_EXPIRY_MINUTES),
        }
        token = jwt.encode(payload, Configuration.JWT_SECRET, algorithm=Configuration.JWT_ALGORITHM)
        log.debug("Issued access token for subject %s (role=%s), expires in %s minutes.",
                   subject_id, role, Configuration.JWT_EXPIRY_MINUTES)
        return token
    except Exception as exc:
        log.error("Failed to create access token for subject %s (role=%s): %s", subject_id, role, exc)
        raise


def _decode(token: str) -> tuple[int, str]:
    """Shared decode step for both get_current_user and
    get_current_customer -- returns (subject_id, role) or raises 401."""
    try:
        payload = jwt.decode(token, Configuration.JWT_SECRET, algorithms=[Configuration.JWT_ALGORITHM])
        return int(payload["sub"]), payload.get("role")
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        log.warning("Rejected invalid/expired token: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Manager-only dependency -- approval_engine and the manager-only
    branches of ticket_management depend on this. Explicitly checks the
    role claim (not just "does a User row with this id exist") because
    User.U_Id and Customer.C_Id are independent id spaces -- a customer
    token with sub=1 must NOT be treated as User #1 just because that
    row happens to exist."""
    subject_id, role = _decode(token)
    if role != UserRole.SUPPORT_MANAGER.value:
        log.warning("Token with role '%s' rejected for a manager-only endpoint.", role)
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    try:
        user = db.get(User, subject_id)
    except Exception as exc:
        log.error("Database error while loading user %s: %s", subject_id, exc)
        raise HTTPException(status_code=500, detail="Could not verify session.")

    if user is None:
        log.warning("Token referenced user_id %s, which no longer exists.", subject_id)
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return user


def get_current_customer(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Customer:
    """Customer-only dependency -- the customer-facing ticket_management
    endpoints (submitTicket, sendMessage, reopenTicket, and a customer's
    own getTickets/getTicket) depend on this. See get_current_user's
    docstring for why the role claim is checked explicitly."""
    subject_id, role = _decode(token)
    if role != UserRole.CUSTOMER.value:
        log.warning("Token with role '%s' rejected for a customer-only endpoint.", role)
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    try:
        customer = db.get(Customer, subject_id)
    except Exception as exc:
        log.error("Database error while loading customer %s: %s", subject_id, exc)
        raise HTTPException(status_code=500, detail="Could not verify session.")

    if customer is None:
        log.warning("Token referenced customer_id %s, which no longer exists.", subject_id)
        raise HTTPException(status_code=401, detail="Customer no longer exists.")
    return customer
