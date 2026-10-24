from sqlalchemy import create_engine, String, select, Column, Integer, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, declarative_base, sessionmaker
from sqlalchemy.sql import func

engine = create_engine('sqlite:///data.db', echo=True)
Base = declarative_base()

class User(Base):
    __tablename__ = "user"    # сотрудники
    id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    position = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Client(Base):
    __tablename__ = "clients" #те кто хочет купить жилье

    id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(20), nullable=False)
    type = Column(String(20), nullable=False)
    status = Column(String(30), nullable=False, default="new")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Xarakteristiki(Base):
    __tablename__ = "xarakteristiki"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    address = Column(String(255), nullable=False)
    type = Column(String(30), nullable=False)
    area = Column(Numeric(8, 2), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    status = Column(String(30), nullable=False, default="available")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    def __repr__(self):
        return f"{self.id}: {self.name}"

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


