import getpass
import sys
from sqlalchemy.exc import SQLAlchemyError

from .import service
from .database import AppError, initDb, roles, statuses

def pickOption(title, options, current=None):
    keys = list(options)
    print(title)
    for number, key in enumerate(keys, 1):
        print(f"{number} — {options[key]}")
    prompt = "Номер(Энтер): " if current else "Номер: "
    answer = input(prompt).strip()
    if not answer and current:
        return current
    if not answer.isdigit() or not 1 <= int(answer) <= len(keys):
        raise AppError("Укажите номер из списка")
    return keys[int(answer) - 1]

def readCredentials():
    login = input("Логин: ").strip()
    if sys.stdin.isatty():
        password = getpass.getpass("Пароль: ")
    else:
        password = input("Пароль: ")
    return {"login": login, "password": password}

def readPerson():
    fullName = input("ФИО: ").strip()
    phone = input("Телефон: ").strip()
    data = readCredentials()
    data["fullName"] = fullName
    data["phone"] = phone
    return data

def showUsers(token):
    users = service.getUsers(token)
    for user in users:
        role = roles.get(user["role"], user["role"])
        status = statuses.get(user["status"], user["status"])
        print(f"#{user['id']} {user['fullName']} | {user['login'] or 'без логина'} | {role} | {status}")
    return users

def editUser(token, me):
    users = showUsers(token)
    userId = int(input("ID сотрудника: "))
    target = None
    for user in users:
        if user["id"] == userId:
            target = user
            break
    if target is None:
        raise AppError("Сотрудник не найден")
    role = pickOption("Роль:", roles, target["role"])
    status = pickOption("Статус:", statuses, target["status"])
    service.changeUser(token, userId, role, status)
    print("Доступ изменин")
    if userId == me["id"]:
        return None
    return token

def showLogs(token):
    print("Последние 20 событий(ПО UTC!!!)")
    for row in service.getLogs(token)[:20]:
        print(f"#{row['id']} {row['createdAt']} | {row['userId'] or '—'} | "
              f"{row['action']} | {row['entity']} {row['detail']}")

def showRows(rows, fields):
    if not rows:
        print("Записей пока нет")
    for row in rows:
        print(" | ".join(f"{label}: {row.get(key, '—')}" for key, label in fields))

def selectRow(rows):
    identity = int(input("ID записи: "))
    for row in rows:
        if row["id"] == identity:
            return row
    raise AppError("Запись нетю(")

def clientMenu(token):
    rows = service.getClients(token)
    showRows(rows, [("id", "ID"), ("fullName", "Клиент"), ("phone", "Телефон"), ("status", "Статус")])
    print("1 Добавить 2 Изменить 3 В архив 4 Из архива 0 Назад")
    choice = input("> ").strip()
    if choice == "1":
        name = input("Имя: ")
        phone = input("Тел: ")
        kind = pickOption("Тип:", service.clientTypes)
        print(service.createClient(token, name, phone, kind))
    elif choice == "2":
        row = selectRow(rows)
        name = input(f"Имя (Энтер {row['fullName']}): ").strip() or row["fullName"]
        phone = input(f"Телефон (Энтер {row['phone']}): ").strip() or row["phone"]
        kind = pickOption("Тип:", service.clientTypes, row["type"] if row["type"] in service.clientTypes else None)
        print(service.updateClient(token, row["id"], name, phone, kind))
    elif choice in {"3", "4"}:
        service.archiveClient(token, selectRow(rows)["id"], choice == "3")
        print("Статус изм")

def readProperty(previous=None):
    previous = previous or {}
    values = {}
    fields = [("title", "Название"), ("address", "Полный адрес"),
              ("area", "Площадь"), ("price", "Цена"), ("ownerId", "ID собственника из клиентов"),
              ("type", "Тип объекта"), ("description", "Описание")]
    for field, label in fields:
        current = previous.get(field)
        hint = f" (Enter — {current})" if current is not None else ""
        values[field] = input(label + hint + ": ").strip() or current or ""
    values["ownerId"] = int(values["ownerId"])
    values["propertyType"] = values.pop("type") or "Квартира"
    return values

def propertyMenu(token):
    search = input("Поиск по названию/адресу (Enter — все): ").strip()
    rows = service.getProperties(token, search)
    showRows(rows, [("id", "ID"), ("title", "Объект"), ("price", "Цена"),
                    ("status", "Статус"), ("ownerId", "Собственник")])
    print("1 Добавить 2 Изменить 3 В архив; 4 Из архива 5 История 0 Назад")
    choice = input("> ").strip()
    if choice == "1":
        print(service.createProperty(token, **readProperty()))
    elif choice == "2":
        row = selectRow(rows)
        print(service.updateProperty(token, row["id"], **readProperty(row)))
    elif choice in {"3", "4"}:
        service.archiveProperty(token, selectRow(rows)["id"], choice == "3")
        print("Статус объекта изменён")
    elif choice == "5":
        for event in service.getPropertyHistory(token, selectRow(rows)["id"]):
            print(event)

def dealMenu(token, canEdit=False):
    rows = service.getDeals(token)
    showRows(rows, [("id", "ID"), ("propertyTitle", "Объект"), ("clientName", "Клиент"),
                    ("kind", "Вид"), ("status", "Статус"), ("commission", "Комиссия")])
    if not canEdit:
        return
    print("1 Создать и зарез 2 Завершить сделку 3 Отменить 4 Завершить аренду 0 Назад")
    choice = input("> ").strip()
    if choice == "1":
        propertyId = int(input("ID объекта: "))
        clientId = int(input("ID покупателя-арендатора: "))
        kind = pickOption("Вид сделки:", service.dealKinds)
        amount = input("Сумма/ставка: ").strip() or None
        commission = input("Комиссия агентства: ").strip() or "0"
        start = input("Начало аренды ГГГГ-ММ-ДД: ").strip() if kind == "rent" else None
        end = input("Конец аренды ГГГГ-ММ-ДД: ").strip() if kind == "rent" else None
        print(service.createDeal(token, propertyId, clientId, kind, amount, commission, start, end))
    elif choice in {"2", "3", "4"}:
        status = {"2": "completed", "3": "cancelled", "4": "ended"}[choice]
        print(service.changeDealStatus(token, selectRow(rows)["id"], status))

def documentMenu(token, role):
    rows = service.getDocuments(token)
    showRows(rows, [("id", "ID"), ("number", "Номер"), ("dealId", "Сделка"),
                    ("title", "Документ"), ("amount", "Сумма"), ("status", "Статус"), ("version", "Версия")])
    if role != "agent":
        print("1 Создать 2 Утвердить 3 Новая версия 6 Отметить оплату счёта")
    print("4 История версий 5 Текст документа 0 Назад")
    choice = input("> ").strip()
    if choice == "1" and role != "agent":
        dealId = int(input("ID сделки: "))
        kinds = {key: value for key, value in service.docKinds.items()
                 if (key == "contract") == (role == "lawyer")}
        kind = pickOption("Документ:", kinds)
        print(service.createDocument(token, dealId, kind, input("Заголовок: "), input("Текст: ")))
    elif choice == "2" and role != "agent":
        print(service.approveDocument(token, selectRow(rows)["id"]))
    elif choice == "3" and role != "agent":
        row = selectRow(rows)
        title = input(f"Заголовок (Энтер {row['title']}): ").strip() or row["title"]
        print(service.reviseDocument(token, row["id"], title, input("Новый текст: ")))
    elif choice == "4":
        for version in service.getDocumentVersions(token, selectRow(rows)["id"]):
            print(version)
    elif choice == "5":
        print(selectRow(rows)["body"])
    elif choice == "6" and role == "accountant":
        print(service.markPaid(token, selectRow(rows)["id"]))

def memberMenu(token):
    me = service.getProfile(token)
    print(f"\n{me['fullName']} — {roles[me['role']]}")
    if me["role"] == "admin":
        print("1 Сотрудники 2 Изменить доступ 3 Журнал 5 Создать сотрудника 6 Сбросить пароль 7 Резервная копия")
    elif me["role"] == "agent":
        print("1  Клиенты 2 Объекты 3 Мои сделки 5 Документы моих сделок")
    else:
        print("1 Сделки 2 Документы")
    print("8  Сводка 9  Изменить мой пароль")
    print("4  Мой профиль 0  Выйти из учётной записи")
    choice = input("> ").strip()
    if choice == "0":
        service.logout(token)
        return None
    if choice == "4":
        print(f"ID: {me['id']}; {me['fullName']}; {roles[me['role']]}; {statuses[me['status']]}")
    elif me["role"] == "admin" and choice == "1":
        showUsers(token)
    elif me["role"] == "admin" and choice == "2":
        return editUser(token, me)
    elif me["role"] == "admin" and choice == "3":
        showLogs(token)
    elif me["role"] == "admin" and choice == "5":
        data = readPerson()
        data["role"] = pickOption("Роль:", roles)
        print("Создан сотрудник #", service.createUser(token, **data))
    elif me["role"] == "admin" and choice == "6":
        userId = int(input("ID сотрудника: "))
        password = getpass.getpass("Новый пароль: ") if sys.stdin.isatty() else input("Новый пароль: ")
        service.resetPassword(token, userId, password)
        print("Пароль изм")
    elif me["role"] == "admin" and choice == "7":
        print("Создана копия:", service.createBackup(token))
    elif me["role"] == "agent" and choice == "1":
        clientMenu(token)
    elif me["role"] == "agent" and choice == "2":
        propertyMenu(token)
    elif me["role"] == "agent" and choice == "3":
        dealMenu(token, canEdit=True)
    elif me["role"] == "agent" and choice == "5":
        documentMenu(token, me["role"])
    elif me["role"] in {"accountant", "lawyer"} and choice == "1":
        dealMenu(token)
    elif me["role"] in {"accountant", "lawyer"} and choice == "2":
        documentMenu(token, me["role"])
    elif choice == "8":
        print(service.getSummary(token))
    elif choice == "9":
        old = getpass.getpass("Текущий пароль: ") if sys.stdin.isatty() else input("Текущий пароль: ")
        new = getpass.getpass("Новый пароль: ") if sys.stdin.isatty() else input("Новый пароль: ")
        service.changePassword(token, old, new)
        print("Пароль изме")
        return None
    else:
        print("Неизвестный пункт")
    return token

def main():
    token = None
    try:
        initDb()
        print("Агентство Твоя территория конфолька")
        while True:
            try:
                if token:
                    token = memberMenu(token)
                    continue
                if service.needsSetup():
                    print("\n1 Создать первого администратора 0 Закрыть программу")
                    choice = input("> ").strip()
                    if choice == "0":
                        break
                    if choice == "1":
                        token = service.createAdmin(**readPerson())
                        print("Админ создан")
                    else:
                        print("Неизвестный пункт")
                    continue
                print("\n1 Войти 2 Зарегистрироваться 0  Закрыть программу")
                choice = input("> ").strip()
                if choice == "0":
                    break
                if choice == "1":
                    token = service.login(**readCredentials())
                    print("Вход выполнен")
                elif choice == "2":
                    data = readPerson()
                    staffRoles = {key: label for key, label in roles.items() if key != "admin"}
                    data["role"] = pickOption("Роль:", staffRoles)
                    userId = service.registerUser(**data)
                    print(f"Заявка #{userId} создана. Дождитесь подтверждения админ")
                else:
                    print("Неизвестный пункт")
            except service.AuthError as error:
                token = None
                print(f"Ошибка: {error}")
            except AppError as error:
                print(f"Ошибка: {error}")
            except ValueError:
                print("Ошибка: ID должен быть целым числом")
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nРабота завершена")
        return 0
    except (SQLAlchemyError, OSError):
        print("Не удалось открыть SQLite.")
        return 1
    finally:
        if token:
            try:
                service.logout(token)
            except AppError:
                pass

if __name__ == "__main__":
    raise SystemExit(main())
