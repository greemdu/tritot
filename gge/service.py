import re
import secrets
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from .database import (AppError, access, copyDatabase, hashPassword, openDb, roles, statuses,
    tokenHash, verifyPassword)
from .models import (Account, AuditLog, AuthSession, Client, Deal, Document,
DocumentVersion, PropertyDetails, User, Xarakteristiki)

clientTypes = {"person": "Физическое лицо", "company": "Юридическое лицо"}
dealKinds = {"sale": "Продажа", "rent": "Аренда"}
docKinds = {"contract": "Договор", "invoice": "Счёт", "act": "Акт"}
dealStatuses = {"active": "В работе", "completed": "Оформлена",
                "cancelled": "Отменена", "ended": "Аренда завершена"}

class AuthError(AppError):
    """миф маф - пустое пространство"""
def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def validateCredentials(login, password):
    if not isinstance(login, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{3,40}", login.strip()):
        raise AppError("Логин: 3–40е")
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise AppError("Пароль должен содержать от 8 до 128 символов")
    return login.strip().lower()

def validatePerson(fullName, phone, login, password):
    login = validateCredentials(login, password)
    if not isinstance(fullName, str) or not 2 <= len(fullName.strip()) <= 150:
        raise AppError("ФИО должно содержать от 2 до 150 символов")
    return fullName.strip(), phoneValue(phone), login

def addLog(db, userId, event, entity="", detail=""):
    db.add(AuditLog(userId=userId, action=event, entity=str(entity), detail=detail))

def requireUser(db, token, permission=None):
    if not isinstance(token, str) or not token:
        raise AuthError("Войдите в учетку")
    session = db.get(AuthSession, tokenHash(token))
    if not session or session.expiresAt <= now():
        raise AuthError("Сессия завершена")
    user = db.get(User, session.userId)
    if not user or user.status != "active" or user.position not in roles:
        raise AuthError("Доступ отключен. Войдите заново после подтверждения администратора")
    if permission and permission not in access[user.position]:
        raise AppError("Недостаточно прав")
    return user

def userData(user):
    return {"id": user.id, "fullName": user.fullName, "role": user.position,
            "status": user.status, "sections": list(access.get(user.position, []))}

def createSession(db, user):
    token = secrets.token_urlsafe(32)
    db.execute(delete(AuthSession).where(AuthSession.expiresAt <= now()))
    db.add(AuthSession(tokenHash=tokenHash(token), userId=user.id,
                       expiresAt=now() + timedelta(hours=8)))
    return token
def addAccount(db, fullName, phone, login, password, role, status):
    user = User(fullName=fullName, phone=phone, position=role, status=status)
    db.add(user)
    db.flush()
    db.add(Account(userId=user.id, login=login, passwordHash=hashPassword(password)))
    return user

def needsSetup():
    with openDb() as db:
        return db.scalar(select(Account.id).limit(1)) is None

def createAdmin(fullName, phone, login, password):
    fullName, phone, login = validatePerson(fullName, phone, login, password)
    with openDb(write=True) as db:
        if db.scalar(select(Account.id).limit(1)) is not None:
            raise AppError("Первичная настройка уже выполнена")
        user = addAccount(db, fullName, phone, login, password, "admin", "active")
        addLog(db, user.id, "admin.created", user.id)
        token = createSession(db, user)
    return token

def registerUser(fullName, phone, login, password, role="agent"):
    fullName, phone, login = validatePerson(fullName, phone, login, password)
    if not isinstance(role, str) or role not in {"agent", "accountant", "lawyer"}:
        raise AppError("При регистрации доступны только агент, бухгалтер и юрист")
    with openDb(write=True) as db:
        if db.scalar(select(Account.id).limit(1)) is None:
            raise AppError("Сначала создайте администратора")
        user = addAccount(db, fullName, phone, login, password, role, "pending")
        addLog(db, user.id, "user.registered", user.id)
        userId = user.id
    return userId

def login(login, password):
    login = validateCredentials(login, password)
    error = None
    token = None
    with openDb(write=True) as db:
        account = db.scalar(select(Account).where(Account.login == login))
        if account and account.lockedUntil and account.lockedUntil > now():
            error = "Слишком много ошибок входа"
        elif not account or not verifyPassword(password, account.passwordHash):
            if account:
                if account.lockedUntil and account.lockedUntil <= now():
                    account.failures = 0
                account.failures += 1
                if account.failures >= 5:
                    account.lockedUntil = now() + timedelta(minutes=15)
            error = "Неверный логин или пароль"
        else:
            user = db.get(User, account.userId)
            account.failures = 0
            account.lockedUntil = None
            if not user or user.status != "active" or user.position not in roles:
                error = "Доступ должен подтвердить администратор"
            else:
                token = createSession(db, user)
                addLog(db, user.id, "auth.login", user.id)
        if error:
            userId = account.userId if account else None
            addLog(db, userId, "auth.failed")
    if error:
        raise AppError(error)
    return token

def getProfile(token):
    with openDb() as db:
        return userData(requireUser(db, token))

def logout(token):
    with openDb(write=True) as db:
        user = requireUser(db, token)
        db.execute(delete(AuthSession).where(AuthSession.tokenHash == tokenHash(token)))
        addLog(db, user.id, "auth.logout", user.id)

def getUsers(token):
    with openDb() as db:
        requireUser(db, token, "users")
        query = select(User, Account).outerjoin(Account, Account.userId == User.id).order_by(User.id)
        result = []
        for user, account in db.execute(query):
            data = userData(user)
            data["login"] = account.login if account else None
            data["phone"] = user.phone
            result.append(data)
        return result

def changeUser(token, userId, role, status):
    with openDb(write=True) as db:
        actor = requireUser(db, token, "users")
        if type(userId) is not int or userId < 1:
            raise AppError("ID должен быть целым +")
        if not isinstance(role, str) or role not in roles:
            raise AppError("Выберите одну рольку")
        if not isinstance(status, str) or status not in statuses:
            raise AppError("Выберите статус по нормальному")
        target = db.get(User, userId)
        if not target:
            raise AppError("Сотрудник не найден")
        account = db.scalar(select(Account).where(Account.userId == userId))
        if not account:
            raise AppError("Исходная запись без логина")
        isAdmin = target.position == "admin" and target.status == "active"
        removesAdmin = role != "admin" or status != "active"
        if isAdmin and removesAdmin:
            query = select(func.count(User.id)).join(Account, Account.userId == User.id)
            query = query.where(User.position == "admin", User.status == "active")
            if db.scalar(query) <= 1:
                raise AppError("Нельзя отключить последнего администратора")
        target.position = role
        target.status = status
        if status == "active":
            account.failures = 0
            account.lockedUntil = None
        db.execute(delete(AuthSession).where(AuthSession.userId == userId))
        addLog(db, actor.id, "user.permissions", userId, role + "/" + status)

def getLogs(token, action=None):
    with openDb() as db:
        requireUser(db, token, "logs")
        query = select(AuditLog).order_by(AuditLog.id.desc()).limit(200)
        if action:
            query = query.where(AuditLog.action == textValue(action, "Событие", 80))
        result = []
        for row in db.scalars(query):
            result.append({"id": row.id, "userId": row.userId, "action": row.action,
                           "entity": row.entity, "detail": row.detail,
                           "createdAt": row.createdAt.isoformat()})
        return result

def textValue(value, label, limit, empty=False):
    if not isinstance(value, str) or len(value.strip()) > limit:
        raise AppError(f"{label}: допустимо до {limit} символов")
    value = value.strip()
    if not value and not empty:
        raise AppError(f"Заполните поле «{label}»")
    return value

def phoneValue(phone):
    phone = textValue(phone, "Телефон", 20)
    digits = re.sub(r"\D", "", phone)
    if not re.fullmatch(r"[+\d][\d ()-]{5,19}", phone) or not 6 <= len(digits) <= 15:
        raise AppError("Неверный телефон")
    return phone

def numberValue(value, label, allowZero=False, maximum="9999999999.99"):
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or (number == 0 and not allowZero):
            raise ValueError()
        number = number.quantize(Decimal("0.01"), ROUND_HALF_UP)
        if number > Decimal(maximum) or (number == 0 and not allowZero):
            raise ValueError()
        return number
    except (InvalidOperation, ValueError, TypeError):
        raise AppError(f"{label}: укажите число в ПРЕДЕЛАХ ДИАПАЗОНА") from None

def choiceValue(value, choices, label):
    if not isinstance(value, str) or value not in choices:
        raise AppError(f"{label}: выберите значение из списка")
    return value

def needRecord(db, model, identity, label):
    if type(identity) is not int or identity < 1:
        raise AppError("ID должен быть целым положительным числом")
    record = db.get(model, identity)
    if record is None:
        raise AppError(f"{label}: запись не найдена")
    return record

def createUser(token, fullName, phone, login, password, role="agent"):
    with openDb(write=True) as db:
        actor = requireUser(db, token, "users")
        role = choiceValue(role, roles, "Роль")
        fullName, phone, login = validatePerson(fullName, phone, login, password)
        user = addAccount(db, fullName, phone, login, password, role, "active")
        addLog(db, actor.id, "user.created", user.id, role)
        return user.id

def changePassword(token, oldPassword, newPassword):
    with openDb(write=True) as db:
        user = requireUser(db, token)
        account = db.scalar(select(Account).where(Account.userId == user.id))
        validateCredentials(account.login, newPassword)
        if not verifyPassword(oldPassword, account.passwordHash):
            raise AppError("Текущий пароль указан неверно")
        account.passwordHash = hashPassword(newPassword)
        db.execute(delete(AuthSession).where(AuthSession.userId == user.id))
        addLog(db, user.id, "auth.password", user.id)

def resetPassword(token, userId, newPassword):
    with openDb(write=True) as db:
        actor = requireUser(db, token, "users")
        target = needRecord(db, User, userId, "Сотрудник")
        account = db.scalar(select(Account).where(Account.userId == target.id))
        if not account:
            raise AppError("У сотрудника нет учетки(")
        validateCredentials(account.login, newPassword)
        account.passwordHash = hashPassword(newPassword)
        account.failures = 0
        account.lockedUntil = None
        db.execute(delete(AuthSession).where(AuthSession.userId == userId))
        addLog(db, actor.id, "user.password", userId)

def createBackup(token):
    with openDb() as db:
        actorId = requireUser(db, token, "backup").id
    target = copyDatabase()
    with openDb(write=True) as db:
        addLog(db, actorId, "backup.created", target.name)
    return str(target)

def clientData(client):
    return {"id": client.id, "fullName": client.fullName, "phone": client.phone,
            "type": client.type, "status": client.status, "createdAt": client.createdAt.isoformat()}

def checkPhone(db, phone, skipId=None):
    key = re.sub(r"\D", "", phone)
    for client in db.scalars(select(Client)):
        if client.id != skipId and re.sub(r"\D", "", client.phone) == key:
            raise AppError(f"Клиент с таким телефоном уже существует: #{client.id}")

def getClients(token, search=""):
    with openDb() as db:
        requireUser(db, token, "clients")
        needle = textValue(search, "Поиск", 200, empty=True).casefold()
        rows = [clientData(row) for row in db.scalars(select(Client).order_by(Client.id))]
        return [row for row in rows if needle in (row["fullName"] + " " + row["phone"]).casefold()]

def createClient(token, fullName, phone, clientType="person"):
    with openDb(write=True) as db:
        user = requireUser(db, token, "clients")
        fullName = textValue(fullName, "Имя", 150)
        phone = phoneValue(phone)
        checkPhone(db, phone)
        client = Client(fullName=fullName, phone=phone,
                        type=choiceValue(clientType, clientTypes, "Тип клиента"), status="active")
        db.add(client)
        db.flush()
        addLog(db, user.id, "client.created", f"client:{client.id}")
        return clientData(client)

def updateClient(token, clientId, fullName, phone, clientType=None):
    with openDb(write=True) as db:
        user = requireUser(db, token, "clients")
        client = needRecord(db, Client, clientId, "Клиент")
        if client.status == "archived":
            raise AppError("Сначала верните клиента из архива")
        client.fullName = textValue(fullName, "Имя или наименование", 150)
        client.phone = phoneValue(phone)
        checkPhone(db, client.phone, client.id)
        if clientType is not None:
            client.type = choiceValue(clientType, clientTypes, "Тип клиента")
        addLog(db, user.id, "client.updated", f"client:{client.id}")
        return clientData(client)

def archiveClient(token, clientId, archived=True):
    with openDb(write=True) as db:
        user = requireUser(db, token, "clients")
        client = needRecord(db, Client, clientId, "Клиент")
        if type(archived) is not bool:
            raise AppError("Признак архива должен быть True или False")
        if archived:
            activeDeal = db.scalar(select(Deal.id).where(Deal.clientId == clientId, Deal.status == "active"))
            ownerProperty = db.scalar(select(PropertyDetails.propertyId).join(
                Xarakteristiki, Xarakteristiki.id == PropertyDetails.propertyId).where(
                PropertyDetails.ownerId == clientId, Xarakteristiki.status.in_(["available", "reserved", "rented"])))
            if activeDeal or ownerProperty:
                raise AppError("У клиента есть действующая сделка или неархивный объект")
        client.status = "archived" if archived else "active"
        addLog(db, user.id, "client.status", f"client:{clientId}", client.status)

def propertyData(record, details):
    return {"id": record.id, "title": record.title, "address": record.address,
            "type": record.type, "area": str(record.area), "price": str(record.price),
            "status": record.status, "ownerId": details.ownerId if details else None,
            "description": details.description if details else "", "createdAt": record.createdAt.isoformat()}

def propertyValues(db, title, address, area, price, ownerId, propertyType, description, skipId=None):
    owner = needRecord(db, Client, ownerId, "Собственник")
    if owner.status == "archived":
        raise AppError("Собственник находится в архиве")
    address = textValue(address, "Полный адрес с номером квартиры", 255)
    key = " ".join(address.casefold().split())
    for record in db.scalars(select(Xarakteristiki)):
        if record.id != skipId and " ".join(record.address.casefold().split()) == key:
            raise AppError(f"Объект по этому адресу уже существует: #{record.id}")
    return {"title": textValue(title, "Название", 200), "address": address,
            "type": textValue(propertyType, "Тип объекта", 30),
            "area": numberValue(area, "Площадь", maximum="999999.99"),
            "price": numberValue(price, "Цена"),
            "description": textValue(description, "Описание", 10000, empty=True)}

def getProperties(token, search="", status=None, minPrice=None, maxPrice=None):
    with openDb() as db:
        requireUser(db, token, "properties")
        needle = textValue(search, "Поиск", 200, empty=True).casefold()
        query = select(Xarakteristiki, PropertyDetails).outerjoin(
            PropertyDetails, PropertyDetails.propertyId == Xarakteristiki.id).order_by(Xarakteristiki.id)
        if status is not None:
            status = choiceValue(status, ["available", "reserved", "sold", "rented", "archived"], "Статус")
            query = query.where(Xarakteristiki.status == status)
        if minPrice is not None:
            query = query.where(Xarakteristiki.price >= numberValue(minPrice, "Минимальная цена", True))
        if maxPrice is not None:
            query = query.where(Xarakteristiki.price <= numberValue(maxPrice, "Максимальная цена", True))
        rows = [propertyData(record, details) for record, details in db.execute(query)]
        return [row for row in rows if needle in (row["title"] + " " + row["address"] + " " + row["type"]).casefold()]

def createProperty(token, title, address, area, price, ownerId, propertyType="Квартира", description=""):
    with openDb(write=True) as db:
        user = requireUser(db, token, "properties")
        values = propertyValues(db, title, address, area, price, ownerId, propertyType, description)
        description = values.pop("description")
        record = Xarakteristiki(**values, status="available")
        db.add(record)
        db.flush()
        details = PropertyDetails(propertyId=record.id, ownerId=ownerId, description=description)
        db.add(details)
        addLog(db, user.id, "property.created", f"property:{record.id}", f"price={record.price}")
        return propertyData(record, details)

def updateProperty(token, propertyId, title, address, area, price, ownerId,
                   propertyType="Квартира", description=""):
    with openDb(write=True) as db:
        user = requireUser(db, token, "properties")
        record = needRecord(db, Xarakteristiki, propertyId, "Объект")
        if record.status != "available":
            raise AppError("Изменять можно только свободный объект")
        values = propertyValues(db, title, address, area, price, ownerId,
                                propertyType, description, propertyId)
        oldPrice = record.price
        description = values.pop("description")
        for field, value in values.items():
            setattr(record, field, value)
        details = db.get(PropertyDetails, propertyId)
        if details is None:
            details = PropertyDetails(propertyId=propertyId, ownerId=ownerId, description=description)
            db.add(details)
        details.ownerId = ownerId
        details.description = description
        addLog(db, user.id, "property.updated", f"property:{propertyId}", f"price={oldPrice} -> {record.price}")
        return propertyData(record, details)

def archiveProperty(token, propertyId, archived=True):
    with openDb(write=True) as db:
        user = requireUser(db, token, "properties")
        record = needRecord(db, Xarakteristiki, propertyId, "Объект")
        if type(archived) is not bool or record.status not in {"available", "archived"}:
            raise AppError("В архив можно переносить только свободный объект")
        details = db.get(PropertyDetails, propertyId)
        if not archived and details and db.get(Client, details.ownerId).status == "archived":
            raise AppError("Сначала верните собственника из архива")
        record.status = "archived" if archived else "available"
        addLog(db, user.id, "property.status", f"property:{propertyId}", record.status)

def getPropertyHistory(token, propertyId):
    with openDb() as db:
        requireUser(db, token, "properties")
        needRecord(db, Xarakteristiki, propertyId, "Объект")
        query = select(AuditLog).where(AuditLog.entity == f"property:{propertyId}").order_by(AuditLog.id)
        return [{"action": row.action, "detail": row.detail, "userId": row.userId,
                 "createdAt": row.createdAt.isoformat()} for row in db.scalars(query)]

def requireDeal(db, user, dealId):
    deal = needRecord(db, Deal, dealId, "Сделка")
    if user.position == "agent" and deal.agentId != user.id:
        raise AppError("Нет доступа к сделке другого агента")
    return deal

def dealData(db, deal):
    return {"id": deal.id, "propertyId": deal.propertyId, "clientId": deal.clientId,
            "agentId": deal.agentId, "kind": deal.kind, "status": deal.status,
            "amount": str(deal.amount), "commission": str(deal.commission),
            "startDate": deal.startDate, "endDate": deal.endDate,
            "propertyTitle": db.get(Xarakteristiki, deal.propertyId).title,
            "clientName": db.get(Client, deal.clientId).fullName,
            "createdAt": deal.createdAt.isoformat(), "updatedAt": deal.updatedAt.isoformat()}

def getDeals(token):
    with openDb() as db:
        user = requireUser(db, token, "deals")
        query = select(Deal).order_by(Deal.id.desc())
        if user.position == "agent":
            query = query.where(Deal.agentId == user.id)
        return [dealData(db, row) for row in db.scalars(query)]

def createDeal(token, propertyId, clientId, kind="sale", amount=None, commission="0",
               startDate=None, endDate=None):
    with openDb(write=True) as db:
        user = requireUser(db, token, "properties")
        record = needRecord(db, Xarakteristiki, propertyId, "Объект")
        client = needRecord(db, Client, clientId, "Клиент")
        kind = choiceValue(kind, dealKinds, "Вид сделки")
        if record.status != "available" or client.status == "archived":
            raise AppError("Объект должен быть свободен, а клиент не должен быть в архивчике")
        details = db.get(PropertyDetails, propertyId)
        if details and db.get(Client, details.ownerId).status == "archived":
            raise AppError("Собственник находится в архиве")
        if details and details.ownerId == clientId:
            raise AppError("Собственник не может быть покупателем или арендатором своего объекта")
        amount = numberValue(record.price if amount is None else amount, "Сумма")
        commission = numberValue(commission, "Комиссия", True)
        if commission > amount:
            raise AppError("Комиссия не может превышать сумму сделки")
        if kind == "rent":
            try:
                start = datetime.strptime(startDate, "%Y-%m-%d").date()
                end = datetime.strptime(endDate, "%Y-%m-%d").date()
                if end <= start:
                    raise ValueError()
                startDate, endDate = start.isoformat(), end.isoformat()
            except (ValueError, TypeError):
                raise AppError("Аренда: укажите даты ГГГГ-ММ-ДД, окончание должно быть позже начала") from None
        else:
            startDate = endDate = None
        deal = Deal(propertyId=propertyId, clientId=clientId, agentId=user.id, kind=kind,
                    amount=amount, commission=commission, status="active",
                    startDate=startDate, endDate=endDate, updatedAt=now())
        db.add(deal)
        db.flush()
        record.status = "reserved"
        addLog(db, user.id, "deal.created", f"deal:{deal.id}", f"property={propertyId}; kind={kind}")
        addLog(db, user.id, "property.status", f"property:{propertyId}", f"reserved; deal={deal.id}")
        return dealData(db, deal)

def changeDealStatus(token, dealId, status):
    with openDb(write=True) as db:
        user = requireUser(db, token, "properties")
        deal = requireDeal(db, user, dealId)
        status = choiceValue(status, ["completed", "cancelled", "ended"], "Статус сделки")
        record = db.get(Xarakteristiki, deal.propertyId)
        if status == "ended":
            if deal.kind != "rent" or deal.status != "completed" or record.status != "rented":
                raise AppError("Завершить можно только действующую оформленную аренду")
            propertyStatus = "available"
        else:
            if deal.status != "active" or record.status != "reserved":
                raise AppError("Сделка уже закрыта или зарезерегана")
            propertyStatus = "available"
            if status == "completed":
                docs = {doc.kind: doc for doc in db.scalars(select(Document).where(Document.dealId == dealId))}
                if "contract" not in docs or docs["contract"].status != "approved":
                    raise AppError("Для завершения нужен договор юристика")
                if deal.commission > 0 and ("invoice" not in docs or docs["invoice"].status != "paid"):
                    raise AppError("Для завершения нужно отметить оплату счета")
                propertyStatus = "sold" if deal.kind == "sale" else "rented"
            elif db.scalar(select(Document.id).where(Document.dealId == dealId, Document.status == "paid")):
                raise AppError("Нельзя отменить сделку с оплаченной комиссией")
        deal.status = status
        deal.updatedAt = now()
        record.status = propertyStatus
        addLog(db, user.id, "deal.status", f"deal:{dealId}", status)
        addLog(db, user.id, "property.status", f"property:{record.id}", f"{propertyStatus}; deal={dealId}")
        return dealData(db, deal)

def allowedDocKinds(user):
    if user.position == "lawyer":
        return ["contract"]
    if user.position == "accountant":
        return ["invoice", "act"]
    return ["contract", "invoice", "act"]

def requireDocument(db, user, documentId, write=False):
    document = needRecord(db, Document, documentId, "Документ")
    deal = requireDeal(db, user, document.dealId)
    if document.kind not in allowedDocKinds(user) or (write and user.position == "agent"):
        raise AppError("Нет доступа к этому типу документа")
    if write and deal.status != "active":
        raise AppError("Документы закрытой сделки доступны только для чтения")
    return document

def documentData(document):
    return {"id": document.id, "dealId": document.dealId, "kind": document.kind,
            "number": f"{document.kind.upper()}-{document.id:06d}", "title": document.title,
            "body": document.body, "amount": str(document.amount), "status": document.status,
            "version": document.version, "authorId": document.authorId,
            "createdAt": document.createdAt.isoformat(), "updatedAt": document.updatedAt.isoformat()}


def saveVersion(db, document, user, action):
    document.version += 1
    document.authorId = user.id
    document.updatedAt = now()
    db.flush()
    db.add(DocumentVersion(documentId=document.id, version=document.version, title=document.title,
                           body=document.body, amount=document.amount, status=document.status, authorId=user.id))
    addLog(db, user.id, action, f"document:{document.id}", f"version={document.version}; status={document.status}")

def getDocuments(token, dealId=None):
    with openDb() as db:
        user = requireUser(db, token, "documents")
        query = select(Document).join(Deal, Deal.id == Document.dealId).where(
            Document.kind.in_(allowedDocKinds(user))).order_by(Document.id.desc())
        if user.position == "agent":
            query = query.where(Deal.agentId == user.id)
        if dealId is not None:
            requireDeal(db, user, dealId)
            query = query.where(Document.dealId == dealId)
        return [documentData(row) for row in db.scalars(query)]


def createDocument(token, dealId, kind, title, body):
    with openDb(write=True) as db:
        user = requireUser(db, token, "documents")
        kind = choiceValue(kind, docKinds, "Вид документа")
        deal = requireDeal(db, user, dealId)
        if user.position == "agent" or kind not in allowedDocKinds(user):
            raise AppError("Нет прав на создание этого типа документа")
        if deal.status != "active":
            raise AppError("Документы закрытой сделки доступны только для чтения")
        if db.scalar(select(Document.id).where(Document.dealId == dealId, Document.kind == kind)):
            raise AppError("Такой документ уже есть: создайте новую версию существующего")
        document = Document(dealId=dealId, kind=kind, title=textValue(title, "Заголовок", 200),
                            body=textValue(body, "Текст документа", 20000),
                            amount=deal.amount if kind == "contract" else deal.commission,
                            status="draft", version=0, authorId=user.id, updatedAt=now())
        db.add(document)
        saveVersion(db, document, user, "document.created")
        return documentData(document)

def reviseDocument(token, documentId, title, body):
    with openDb(write=True) as db:
        user = requireUser(db, token, "documents")
        document = requireDocument(db, user, documentId, write=True)
        if document.status == "paid":
            raise AppError("Оплаченный счёт нельзя изменять")
        document.title = textValue(title, "Заголовок", 200)
        document.body = textValue(body, "Текст документа", 20000)
        document.status = "draft"
        saveVersion(db, document, user, "document.revised")
        return documentData(document)

def approveDocument(token, documentId):
    with openDb(write=True) as db:
        user = requireUser(db, token, "documents")
        document = requireDocument(db, user, documentId, write=True)
        if document.status != "draft":
            raise AppError("Утвердить можно только черновик")
        document.status = "approved"
        saveVersion(db, document, user, "document.approved")
        return documentData(document)

def markPaid(token, documentId):
    with openDb(write=True) as db:
        user = requireUser(db, token, "documents")
        document = requireDocument(db, user, documentId, write=True)
        if user.position != "accountant" or document.kind != "invoice" or document.status != "approved":
            raise AppError("Бухгалтер может отметить оплату только когда утвердикли ччет")
        document.status = "paid"
        saveVersion(db, document, user, "invoice.paid")
        return documentData(document)

def getDocumentVersions(token, documentId):
    with openDb() as db:
        user = requireUser(db, token, "documents")
        requireDocument(db, user, documentId)
        query = select(DocumentVersion).where(DocumentVersion.documentId == documentId).order_by(DocumentVersion.version)
        return [{"version": row.version, "title": row.title, "body": row.body,
                 "amount": str(row.amount), "status": row.status, "authorId": row.authorId,
                 "createdAt": row.createdAt.isoformat()} for row in db.scalars(query)]

def getSummary(token):
    with openDb() as db:
        user = requireUser(db, token)
        if user.position == "admin":
            return {"users": db.scalar(select(func.count(User.id))),
                    "pending": db.scalar(select(func.count(User.id)).where(User.status == "pending"))}
        query = select(func.count(Deal.id)).where(Deal.status == "active")
        if user.position == "agent":
            query = query.where(Deal.agentId == user.id)
        result = {"activeDeals": db.scalar(query)}
        if user.position == "agent":
            result["availableProperties"] = db.scalar(select(func.count(Xarakteristiki.id)).where(
                Xarakteristiki.status == "available"))
        else:
            result["draftDocuments"] = db.scalar(select(func.count(Document.id)).where(
                Document.kind.in_(allowedDocKinds(user)), Document.status == "draft"))
        return result
