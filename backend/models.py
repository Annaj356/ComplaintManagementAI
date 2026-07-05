
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, func
)
from sqlalchemy.orm import relationship
from database import Base
import enum


class ComplaintStatus(str, enum.Enum):
    SUBMITTED = "Submitted"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    REJECTED = "Rejected"


class ComplaintPriority(str, enum.Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    category = Column(String(100), nullable=False, index=True)
    priority = Column(Enum(ComplaintPriority), nullable=False, default=ComplaintPriority.LOW, index=True)
    department = Column(String(100), nullable=False)
    status = Column(Enum(ComplaintStatus), nullable=False, default=ComplaintStatus.SUBMITTED, index=True)

    location = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Enables complaint.user.name, complaint.user.email, etc.
    user = relationship("User", back_populates="complaints")

    def __repr__(self):
        return f"<Complaint id={self.id} title={self.title!r} status={self.status}>"
    
    class User(Base):
      __tablename__ = "users"
      id = Column(Integer, primary_key=True, index=True)
      name = Column(String(100))
      email = Column(String(150), unique=True)
      password_hash = Column(String(255))
      role = Column(String(50), default="user")

