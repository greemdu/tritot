import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine as createEngine, event, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from models import Base

roles = {"admin": "Администратор", "agent": "Агент",
         "accountant": "Бухгалтер", "lawyer": "Юрист"}
access = {"admin": ["users", "logs", "backup"],
          "agent": ["clients", "properties", "deals", "documents"],
          "accountant": ["deals", "documents"], "lawyer": ["deals", "documents"]}
statuses = {"active": "активен", "pending": "ожидает подтверждения", "blocked": "заблокирован"}

dbPath = Path(os.environ.get("AGENCY_DB", Path(__file__).with_name("data.db"))).resolve()
engine = createEngine("sqlite:///" + dbPath.as_posix(),
                      connect_args={"check_same_thread": False, "timeout": 10})
dbSession = sessionmaker(bind=engine, expire_on_commit=False)


class AppError(Exception):
    """если что это заглушка для определения, а не коммент, а так прикольный вечер, я выпил уже 4 кружку кофе"""

@event.listens_for(engine, "connect")
def configure(connection, record):
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=10000")


def initDb():
    dbPath.parent.mkdir(parents=True, exist_ok=True)
    with engine.connect() as db:
        db.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)


@contextmanager
def openDb(write=False):
    with dbSession() as db:
        try:
            if write:
                db.execute(text("BEGIN IMMEDIATE"))
            yield db
            if write:
                db.commit()
        except IntegrityError:
            db.rollback()
            raise AppError("Запись уже существует") from None
        except OperationalError:
            db.rollback()
            raise AppError("База временно недоступна") from None
        except Exception:
            db.rollback()
            raise

def hashPassword(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"pbkdf2_sha256$600000${salt.hex()}${digest.hex()}"

def verifyPassword(password, stored):
    try:
        method, iterations, salt, expected = stored.split("$")
        if method != "pbkdf2_sha256" or not 100_000 <= int(iterations) <= 2_000_000:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError, AttributeError):
        return False

def tokenHash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def copyDatabase():
    folder = dbPath.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = folder / f"agency-{stamp}.db"
    try:
        with closing(sqlite3.connect(str(dbPath))) as source:
            with closing(sqlite3.connect(str(target))) as destination:
                source.backup(destination)
                result = destination.execute("PRAGMA quick_check").fetchone()[0]
                if result != "ok":
                    raise AppError("Не удалось проверить бекап((((")
    except (OSError, sqlite3.Error, AppError):
        target.unlink(missing_ok=True)
        raise AppError("Не удалось создать бекап") from None
    return target

if __name__ == "__main__":
    initDb()
    print(f"База готова: {dbPath}")
