from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTextEdit,
)

from gge import service


ROLE_LABELS = {
    "admin": "Администратор",
    "agent": "Агент",
    "accountant": "Бухгалтер",
    "lawyer": "Юрист",
}

PROPERTY_TYPES = {
    "Квартира": "Жилое помещение в многоквартирном доме.",
    "Дом": "Отдельный жилой дом.",
    "Студия": "Жилое помещение со свободной планировкой.",
    "Коммерческая недвижимость": "Помещения для коммерческого использования.",
    "Земельный участок": "Земельный участок для разрешённого использования.",
}

PROPERTY_STATUSES = {
    "available": ("Свободен", "Объект доступен для новой сделки."),
    "reserved": ("Забронирован", "Объект зарезервирован в рамках сделки."),
    "sold": ("Продан", "Объект продан."),
    "rented": ("Сдан в аренду", "Объект сдан в аренду."),
    "archived": ("В архиве", "Объект исключён из активной работы."),
}

CLIENT_STATUSES = {
    "active": ("Активен", "Клиент доступен для работы."),
    "archived": ("В архиве", "Клиент архивирован."),
}

DOCUMENT_STATUSES = {
    "draft": ("Черновик", "Документ подготовлен, но ещё не утверждён."),
    "approved": ("Утверждён", "Документ утверждён ответственным сотрудником."),
    "paid": ("Оплачен", "Для счёта подтверждена оплата."),
}

ROLE_DESCRIPTIONS = {
    "admin": "Управляет учётными записями, журналом событий и резервными копиями.",
    "agent": "Работает с клиентами, объектами, сделками и документами своих сделок.",
    "accountant": "Работает со сделками и документами; подтверждает оплату счетов.",
    "lawyer": "Работает со сделками и документами, в том числе с договорами.",
}

PERMISSION_LABELS = {
    "users": "Сотрудники",
    "logs": "Журнал событий",
    "backup": "Резервное копирование",
    "clients": "Клиенты",
    "properties": "Объекты недвижимости",
    "deals": "Сделки",
    "documents": "Документы",
}


class ReferencesPage(QWidget):
    def __init__(self, token, role=None, parent=None):
        super().__init__(parent)

        self.token = token
        self.role = role
        self.rows = []
        self.visible_rows = []

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(17)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(5)

        title = QLabel("Справочники")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #24352c;"
        )

        subtitle = QLabel(
            "Единые обозначения, статусы и правила работы агентства"
        )
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet("font-size: 13px; color: #7b877f;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondary")
        self.refresh_button.setMinimumHeight(38)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(
            lambda checked=False: self.refresh_data()
        )
        header.addWidget(self.refresh_button)
        root.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText(
            "Поиск по названию, коду или описанию..."
        )
        self.search_input.textChanged.connect(self.filter_rows)

        self.category_filter = QComboBox()
        self.category_filter.setMinimumHeight(38)
        self.category_filter.addItem("Все разделы", "all")
        self.category_filter.currentIndexChanged.connect(self.filter_rows)

        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.category_filter, 1)
        root.addLayout(filters)

        panel = QFrame()
        panel.setObjectName("panel")

        inside = QVBoxLayout(panel)
        inside.setContentsMargins(18, 18, 18, 18)
        inside.setSpacing(12)

        panel_header = QHBoxLayout()
        self.count_label = QLabel("Записей: 0")
        self.count_label.setObjectName("section_title")
        self.count_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #24352c;"
        )
        panel_header.addWidget(self.count_label)
        panel_header.addStretch()
        inside.addLayout(panel_header)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Раздел", "Наименование", "Код", "Описание",
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(43)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f7f9f7;
                border: 1px solid #e2e8e3;
                border-radius: 9px;
                color: #28372e;
                font-size: 13px;
                selection-background-color: #dcefe2;
                selection-color: #24352c;
            }
            QHeaderView::section {
                background-color: #f3f6f3;
                color: #65736a;
                border: none;
                border-bottom: 1px solid #e2e8e3;
                padding: 11px 8px;
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 7px;
                border-bottom: 1px solid #edf0ed;
            }
        """)
        self.table.itemSelectionChanged.connect(self.show_details)
        self.table.cellClicked.connect(self.select_row)
        inside.addWidget(self.table, 1)

        detail_title = QLabel("Описание выбранной записи")
        detail_title.setStyleSheet(
            "font-size: 14px; font-weight: 600; color: #24352c;"
        )
        inside.addWidget(detail_title)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(80)
        self.details.setMaximumHeight(115)
        self.details.setPlaceholderText(
            "Выберите запись в таблице, чтобы посмотреть описание."
        )
        inside.addWidget(self.details)

        root.addWidget(panel, 1)

    def build_rows(self):
        rows = []

        def add(category, label, code, description):
            rows.append({
                "category": category,
                "label": str(label),
                "code": str(code),
                "description": str(description),
            })

        roles = getattr(service, "roles", {})
        access = getattr(service, "access", {})
        statuses = getattr(service, "statuses", {})

        # Роли и разрешения берутся из серверных настроек, если они доступны.
        for code, server_label in roles.items():
            label = ROLE_LABELS.get(code, server_label)
            permissions = access.get(code, [])
            permission_names = [
                PERMISSION_LABELS.get(item, str(item))
                for item in permissions
            ]
            description = ROLE_DESCRIPTIONS.get(code, "Роль в системе.")
            if permission_names:
                description += " Доступ: " + ", ".join(permission_names) + "."
            add("Роли сотрудников", label, code, description)

        for code, label in getattr(service, "clientTypes", {}).items():
            add("Типы клиентов", label, code,
                "Категория клиента, выбираемая при создании или редактировании карточки.")

        for label, description in PROPERTY_TYPES.items():
            add("Типы объектов", label, "—", description + " Список используется интерфейсом.")

        for code, label in getattr(service, "dealKinds", {}).items():
            add("Типы сделок", label, code,
                "Вид сделки, указываемый при оформлении сделки с объектом.")

        for code, label in getattr(service, "dealStatuses", {}).items():
            add("Статусы сделок", label, code,
                "Текущий этап или итоговое состояние сделки.")

        for code, label in getattr(service, "docKinds", {}).items():
            add("Типы документов", label, code,
                "Вид документа, создаваемого для сделки.")

        for code, (label, description) in DOCUMENT_STATUSES.items():
            add("Статусы документов", label, code, description)

        for code, (label, description) in PROPERTY_STATUSES.items():
            add("Статусы объектов", label, code, description)

        for code, (label, description) in CLIENT_STATUSES.items():
            add("Статусы клиентов", label, code, description)

        for code, label in statuses.items():
            add("Статусы сотрудников", label, code,
                "Состояние учётной записи сотрудника.")

        if not statuses:
            for code, label, description in [
                ("active", "Активен", "Сотрудник может войти в систему."),
                ("pending", "Ожидает подтверждения", "Заявка сотрудника ещё не подтверждена."),
                ("disabled", "Отключён", "Доступ сотрудника отключён."),
            ]:
                add("Статусы сотрудников", label, code, description)

        add(
            "Общие правила", "Срок действия сессии", "8 часов",
            "Сервер создаёт сессию после входа и ограничивает её срок действия восемью часами.",
        )
        add(
            "Общие правила", "Длина логина", "3–40 символов",
            "Логин может содержать латинские буквы, цифры, точку, дефис и подчёркивание.",
        )
        add(
            "Общие правила", "Длина пароля", "8–128 символов",
            "Пароль должен содержать от 8 до 128 символов.",
        )

        return rows

    def refresh_data(self, *_):
        if self.token:
            try:
                profile = service.getProfile(self.token) or {}
                self.role = profile.get("role", self.role)
            except Exception:
                # Справочные значения могут быть показаны и без повторного запроса профиля.
                pass

        self.rows = self.build_rows()

        current_category = self.category_filter.currentData()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Все разделы", "all")

        categories = sorted({row["category"] for row in self.rows})
        for category in categories:
            self.category_filter.addItem(category, category)

        index = self.category_filter.findData(current_category)
        if index >= 0:
            self.category_filter.setCurrentIndex(index)
        self.category_filter.blockSignals(False)

        self.filter_rows()

    def filter_rows(self, *_):
        needle = self.search_input.text().strip().casefold()
        category = self.category_filter.currentData()

        self.visible_rows = [
            row for row in self.rows
            if (category == "all" or row["category"] == category)
            and (
                not needle
                or needle in " ".join(row.values()).casefold()
            )
        ]

        self.table.setRowCount(0)
        for row_index, record in enumerate(self.visible_rows):
            self.table.insertRow(row_index)
            values = [
                record["category"], record["label"],
                record["code"], record["description"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if column == 2:
                    item.setTextAlignment(Qt.AlignCenter)
                if record["category"] == "Общие правила":
                    item.setForeground(QBrush(QColor("#355987")))
                self.table.setItem(row_index, column, item)
            self.table.setRowHeight(row_index, 43)

        self.count_label.setText(
            f"Записей: {len(self.visible_rows)}"
        )

        if self.visible_rows:
            self.table.selectRow(0)
        else:
            self.details.clear()

    def select_row(self, row, column=0):
        if 0 <= row < self.table.rowCount():
            self.table.setCurrentCell(row, max(0, column))
            self.table.selectRow(row)
        self.show_details()

    def show_details(self, *_):
        row = self.table.currentRow()
        if row < 0 or row >= len(self.visible_rows):
            self.details.clear()
            return

        record = self.visible_rows[row]
        self.details.setPlainText(
            f'Раздел: {record["category"]}\n'
            f'Наименование: {record["label"]}\n'
            f'Код: {record["code"]}\n\n'
            f'{record["description"]}'
        )

    def set_token(self, token):
        self.token = token
        self.refresh_data()
