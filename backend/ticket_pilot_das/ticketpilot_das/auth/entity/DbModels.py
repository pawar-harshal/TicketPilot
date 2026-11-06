"""SQLAlchemy model owned by auth: User (support manager logins)."""
from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.sql import func

from ticketpilot_das.utils.Database import Base


class User(Base):
    __tablename__ = "User"

    U_Id = Column(BigInteger, primary_key=True, autoincrement=True)
    U_Email = Column(String(255), nullable=False, unique=True)
    U_PasswordHash = Column(String(255), nullable=False)
    U_Role = Column(String(30), nullable=False, default="support_manager")
    U_CreatedDate = Column(DateTime, nullable=False, server_default=func.now())
