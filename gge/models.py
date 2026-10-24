
from sqlalchemy import (CheckConstraint, Column, DateTime, ForeignKey, Index,
                        Integer, Numeric, String, Text, UniqueConstraint)
from sqlalchemy.orm import declarative_base as declarativeBase
from sqlalchemy.sql import func

Base = declarativeBase()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    fullName = Column("full_name", String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    position = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    fullName = Column("full_name", String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    type = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False, default="new")
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())


class Xarakteristiki(Base):
    __tablename__ = "xarakteristiki"
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    address = Column(String(255), nullable=False)
    type = Column(String(30), nullable=False)
    area = Column(Numeric(8, 2), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    status = Column(String(30), nullable=False, default="available")
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())

    def __repr__(self):
        return f"{self.id}: {self.title}"


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    userId = Column("user_id", Integer, ForeignKey("user.id"), nullable=False, unique=True)
    login = Column(String(40), nullable=False, unique=True)
    passwordHash = Column("password_hash", String(200), nullable=False)
    failures = Column(Integer, nullable=False, default=0)
    lockedUntil = Column("locked_until", DateTime)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    tokenHash = Column("token_hash", String(64), primary_key=True)
    userId = Column("user_id", Integer, ForeignKey("user.id"), nullable=False)
    expiresAt = Column("expires_at", DateTime, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    userId = Column("user_id", Integer, ForeignKey("user.id"))
    action = Column(String(80), nullable=False)
    entity = Column(String(80), nullable=False, default="")
    detail = Column(Text, nullable=False, default="")
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())


# Дополнительные таблицы: исходные шесть таблиц и их столбцы не меняются.
class PropertyDetails(Base):
    __tablename__ = "agency_property_details"
    propertyId = Column("property_id", Integer, ForeignKey("xarakteristiki.id"), primary_key=True)
    ownerId = Column("owner_id", Integer, ForeignKey("clients.id"), nullable=False)
    description = Column(Text, nullable=False, default="")


class Deal(Base):
    __tablename__ = "agency_deals"
    id = Column(Integer, primary_key=True)
    propertyId = Column("property_id", Integer, ForeignKey("xarakteristiki.id"), nullable=False)
    clientId = Column("client_id", Integer, ForeignKey("clients.id"), nullable=False)
    agentId = Column("agent_id", Integer, ForeignKey("user.id"), nullable=False)
    kind = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    amount = Column(Numeric(12, 2), nullable=False)
    commission = Column(Numeric(12, 2), nullable=False, default=0)
    startDate = Column("start_date", String(10))
    endDate = Column("end_date", String(10))
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())
    updatedAt = Column("updated_at", DateTime, nullable=False, server_default=func.now())
    __table_args__ = (
        CheckConstraint("kind IN ('sale', 'rent')"),
        CheckConstraint("status IN ('active', 'completed', 'cancelled', 'ended')"),
        CheckConstraint("amount > 0 AND commission >= 0 AND commission <= amount"),
    )


Index("uq_agency_active_property", Deal.propertyId, unique=True,
      sqlite_where=Deal.status == "active")


class Document(Base):
    __tablename__ = "agency_documents"
    id = Column(Integer, primary_key=True)
    dealId = Column("deal_id", Integer, ForeignKey("agency_deals.id"), nullable=False)
    kind = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    version = Column(Integer, nullable=False, default=1)
    authorId = Column("author_id", Integer, ForeignKey("user.id"), nullable=False)
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())
    updatedAt = Column("updated_at", DateTime, nullable=False, server_default=func.now())
    __table_args__ = (
        UniqueConstraint("deal_id", "kind"),
        CheckConstraint("kind IN ('contract', 'invoice', 'act')"),
        CheckConstraint("status IN ('draft', 'approved', 'paid')"),
    )


class DocumentVersion(Base):
    __tablename__ = "agency_document_versions"
    id = Column(Integer, primary_key=True)
    documentId = Column("document_id", Integer, ForeignKey("agency_documents.id"), nullable=False)
    version = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), nullable=False)
    authorId = Column("author_id", Integer, ForeignKey("user.id"), nullable=False)
    createdAt = Column("created_at", DateTime, nullable=False, server_default=func.now())
    __table_args__ = (UniqueConstraint("document_id", "version"),)
