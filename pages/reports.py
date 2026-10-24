
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTabWidget, QFileDialog,
    QMessageBox,
)

from gge import service


ROLE_LABELS = {
    "admin": "Администратор",
    "agent": "Агент",
    "accountant": "Бухгалтер",
    "lawyer": "Юрист",
}

DEAL_KIND_LABELS = {"sale": "Продажа", "rent": "Аренда"}

DEAL_STATUS_LABELS = {
    "active": "В работе",
    "completed": "Оформлена",
    "cancelled": "Отменена",
    "ended": "Аренда завершена",
}

PROPERTY_STATUS_LABELS = {
    "available": "Свободен",
    "reserved": "Забронирован",
    "sold": "Продан",
    "rented": "Сдан в аренду",
    "archived": "В архиве",
}

CLIENT_TYPE_LABELS = {
    "person": "Физическое лицо",
    "company": "Юридическое лицо",
}

CLIENT_STATUS_LABELS = {
    "active": "Активен",
    "archived": "В архиве",
}

DOCUMENT_KIND_LABELS = {
    "contract": "Договор",
    "invoice": "Счёт",
    "act": "Акт",
}

DOCUMENT_STATUS_LABELS = {
    "draft": "Черновик",
    "approved": "Утверждён",
    "paid": "Оплачен",
}

USER_STATUS_LABELS = {
    "active": "Активен",
    "pending": "Ожидает подтверждения",
    "disabled": "Отключён",
}


class ReportMetric(QFrame):
    def __init__(self, label, value="—", hint="", parent=None):
        super().__init__(parent)

        self.setObjectName("report_metric")
        self.setMinimumHeight(112)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 15, 17, 15)
        layout.setSpacing(7)

        self.label = QLabel(label)
        self.label.setStyleSheet(
            "font-size: 12px; color: #738078; background: transparent;"
        )

        self.value = QLabel(str(value))
        self.value.setStyleSheet(
            "font-size: 23px; font-weight: 700; color: #24352c; "
            "background: transparent;"
        )
        self.value.setWordWrap(True)

        self.hint = QLabel(hint)
        self.hint.setStyleSheet(
            "font-size: 11px; color: #8a958e; background: transparent;"
        )
        self.hint.setWordWrap(True)

        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.hint)
        layout.addStretch()

        self.setStyleSheet("""
            QFrame#report_metric {
                background-color: white;
                border: 1px solid #e2e8e3;
                border-radius: 12px;
            }
        """)

    def set_values(self, value, hint=""):
        self.value.setText(str(value))
        self.hint.setText(str(hint))


class ReportsPage(QWidget):
    def __init__(self, token, role=None, parent=None):
        super().__init__(parent)

        self.token = token
        self.role = role
        self.profile = {}
        self.summary = {}

        self.records = {
            "deals": [],
            "documents": [],
            "properties": [],
            "clients": [],
            "users": [],
        }

        self.tables = {}
        self.tab_keys = {}
        self.load_errors = []

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(17)

        header = QHBoxLayout()
        title_layout = QVBoxLayout()
        title_layout.setSpacing(5)

        title = QLabel("Отчёты")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #24352c;"
        )

        subtitle = QLabel(
            "Сводные показатели и выгрузка данных по доступным разделам"
        )
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet("font-size: 13px; color: #7b877f;")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        header.addLayout(title_layout)
        header.addStretch()

        self.period_filter = QComboBox()
        self.period_filter.setMinimumHeight(38)
        self.period_filter.addItem("Всё время", "all")
        self.period_filter.addItem("Последние 7 дней", "7d")
        self.period_filter.addItem("Последние 30 дней", "30d")
        self.period_filter.addItem("Этот месяц", "month")
        self.period_filter.addItem("Этот год", "year")
        self.period_filter.currentIndexChanged.connect(
            self.rebuild_report
        )

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondary")
        self.refresh_button.setMinimumHeight(38)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(
            lambda checked=False: self.refresh_data()
        )

        self.export_button = QPushButton("Экспортировать CSV")
        self.export_button.setObjectName("primary")
        self.export_button.setMinimumHeight(38)
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.clicked.connect(
            lambda checked=False: self.export_current_report()
        )

        header.addWidget(self.period_filter)
        header.addWidget(self.refresh_button)
        header.addWidget(self.export_button)

        root.addLayout(header)

        self.metrics_layout = QGridLayout()
        self.metrics_layout.setSpacing(13)

        self.metrics = [
            ReportMetric("Записей в отчёте"),
            ReportMetric("Сделки в работе"),
            ReportMetric("Общая сумма сделок"),
            ReportMetric("Документы на утверждении"),
        ]

        for column, metric in enumerate(self.metrics):
            self.metrics_layout.addWidget(metric, 0, column)

        root.addLayout(self.metrics_layout)

        self.access_note = QLabel("")
        self.access_note.setWordWrap(True)
        self.access_note.setStyleSheet(
            "font-size: 12px; color: #78869B; padding: 2px 1px;"
        )
        root.addWidget(self.access_note)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8e3;
                border-radius: 10px;
                background: white;
                top: -1px;
            }
            QTabBar::tab {
                background: #f0f3f0;
                color: #65736a;
                padding: 10px 17px;
                border-radius: 7px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #29466D;
                color: white;
            }
        """)

        root.addWidget(self.tabs, 1)

    @staticmethod
    def _money(value):
        try:
            number = Decimal(str(value or "0"))
            text = (
                f"{number:,.2f}"
                .replace(",", " ")
                .replace(".", ",")
            )
            return f"{text} ₽"
        except (InvalidOperation, ValueError, TypeError):
            return f"{value or 0} ₽"

    @staticmethod
    def _date_text(value):
        if not value:
            return "—"

        text = str(value)

        try:
            parsed = datetime.fromisoformat(
                text.replace("Z", "+00:00")
            )
            if "T" in text:
                return parsed.strftime("%d.%m.%Y %H:%M")
            return parsed.strftime("%d.%m.%Y")

        except (ValueError, TypeError):
            try:
                parsed_date = date.fromisoformat(text[:10])
                return parsed_date.strftime("%d.%m.%Y")
            except (ValueError, TypeError):
                return text[:16].replace("T", " ")

    @staticmethod
    def _record_date(item):
        value = item.get("createdAt") or item.get("updatedAt")

        if not value:
            return None

        try:
            return datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            ).date()

        except (ValueError, TypeError):
            try:
                return date.fromisoformat(str(value)[:10])
            except (ValueError, TypeError):
                return None

    def _filter_by_period(self, records):
        period = self.period_filter.currentData()

        if period == "all":
            return list(records)

        today = date.today()

        if period == "7d":
            start = today - timedelta(days=6)
        elif period == "30d":
            start = today - timedelta(days=29)
        elif period == "month":
            start = today.replace(day=1)
        elif period == "year":
            start = today.replace(month=1, day=1)
        else:
            return list(records)

        result = []

        for item in records:
            record_date = self._record_date(item)

            if (
                record_date is not None
                and start <= record_date <= today
            ):
                result.append(item)

        return result

    def refresh_data(self, *_):
        if not self.token:
            self.records = {key: [] for key in self.records}
            self.summary = {}
            self.profile = {}
            self.load_errors = [
                "Нет активной сессии. Войдите в приложение заново."
            ]
            self.rebuild_report()
            return

        self.load_errors = []
        self.profile = {}

        try:
            self.profile = service.getProfile(self.token) or {}
            self.role = self.profile.get("role", self.role)
        except Exception as error:
            self.load_errors.append(f"Профиль: {error}")

        try:
            self.summary = service.getSummary(self.token) or {}
        except Exception as error:
            self.summary = {}
            self.load_errors.append(f"Сводка: {error}")

        self.records = {key: [] for key in self.records}

        # Запрашиваем только разделы, доступные текущей роли.
        role_sources = {
            "agent": ("deals", "documents", "properties", "clients"),
            "accountant": ("deals", "documents"),
            "lawyer": ("deals", "documents"),
            "admin": ("users",),
        }

        sources = role_sources.get(self.role, ())

        loaders = {
            "deals": service.getDeals,
            "documents": service.getDocuments,
            "properties": service.getProperties,
            "clients": service.getClients,
            "users": service.getUsers,
        }

        for key in sources:
            try:
                self.records[key] = loaders[key](self.token) or []
            except Exception as error:
                self.records[key] = []
                self.load_errors.append(
                    f"{self._tab_title(key)}: {error}"
                )

        self.rebuild_report()

    @staticmethod
    def _tab_title(key):
        return {
            "deals": "Сделки",
            "documents": "Документы",
            "properties": "Объекты",
            "clients": "Клиенты",
            "users": "Сотрудники",
        }.get(key, key)

    def _active_records(self, key):
        records = self.records.get(key, [])

        if key == "users":
            return list(records)

        return self._filter_by_period(records)

    def rebuild_report(self, *_):
        deals = self._active_records("deals")
        documents = self._active_records("documents")
        properties = self._active_records("properties")
        clients = self._active_records("clients")
        users = self._active_records("users")

        if self.role == "admin":
            active_users = sum(
                1 for item in users
                if item.get("status") == "active"
            )
            pending_users = sum(
                1 for item in users
                if item.get("status") == "pending"
            )
            disabled_users = sum(
                1 for item in users
                if item.get("status") not in ("active", "pending")
            )

            self.metrics[0].label.setText("Всего сотрудников")
            self.metrics[0].set_values(
                len(users), f"Активных: {active_users}"
            )

            self.metrics[1].label.setText("Заявки на подтверждение")
            self.metrics[1].set_values(
                pending_users, "Ожидают решения администратора"
            )

            self.metrics[2].label.setText(
                "Отключённые учётные записи"
            )
            self.metrics[2].set_values(
                disabled_users, "По данным списка сотрудников"
            )

            self.metrics[3].label.setText("Доступный отчёт")
            self.metrics[3].set_values(
                "Сотрудники", "Пользователи и статусы учётных записей"
            )

        else:
            active_deals = sum(
                1 for item in deals
                if item.get("status") == "active"
            )

            total_amount = sum(
                (
                    Decimal(str(item.get("amount", "0") or "0"))
                    for item in deals
                ),
                Decimal("0"),
            )

            draft_docs = sum(
                1 for item in documents
                if item.get("status") == "draft"
            )

            self.metrics[0].label.setText("Сделки за период")
            self.metrics[0].set_values(
                len(deals), "По доступным данным сервера"
            )

            self.metrics[1].label.setText("Сделки в работе")
            self.metrics[1].set_values(
                active_deals, "Статус «В работе»"
            )

            self.metrics[2].label.setText("Сумма сделок")
            self.metrics[2].set_values(
                self._money(total_amount),
                "Сумма записей за выбранный период",
            )

            self.metrics[3].label.setText("Документы-черновики")
            self.metrics[3].set_values(
                draft_docs, "Ожидают утверждения"
            )

        if self.role == "agent":
            self.access_note.setText(
                f"Дополнительно доступно: клиентов — {len(clients)}, "
                f"объектов — {len(properties)}. Период применяется к "
                "записям с датой создания."
            )
        elif self.role == "admin":
            self.access_note.setText(
                "В текущей конфигурации сервера администратору доступен "
                "отчёт по сотрудникам. Для отчётов по сделкам и документам "
                "понадобятся дополнительные разрешения backend."
            )
        else:
            self.access_note.setText(
                "Отчёт построен по сделкам и документам, доступным вашей "
                "роли. Сумма сделок — справочный показатель, а не "
                "бухгалтерская выручка."
            )

        self.tabs.clear()
        self.tables.clear()
        self.tab_keys.clear()

        visible_keys = {
            "admin": ("users",),
            "agent": ("deals", "documents", "properties", "clients"),
            "accountant": ("deals", "documents"),
            "lawyer": ("deals", "documents"),
        }.get(self.role, ())

        for key in visible_keys:
            self._add_report_tab(key)

        if not visible_keys:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)

            message = QLabel(
                "Нет доступных отчётов для этой учётной записи."
            )
            message.setAlignment(Qt.AlignCenter)
            message.setStyleSheet(
                "color: #78869B; padding: 35px;"
            )

            empty_layout.addWidget(message)
            self.tabs.addTab(empty, "Нет данных")

        if self.load_errors:
            self.access_note.setText(
                self.access_note.text()
                + "\nНекоторые данные не загрузились: "
                + " | ".join(self.load_errors)
            )

        self.export_button.setEnabled(bool(self.tab_keys))

    def _add_report_tab(self, key):
        config = self._report_config(key)

        if not config:
            return

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        help_label = QLabel(config["description"])
        help_label.setStyleSheet(
            "color: #7b877f; font-size: 12px;"
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        table = QTableWidget(0, len(config["headers"]))
        table.setHorizontalHeaderLabels(config["headers"])
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(42)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)

        table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #f7f9f7;
                border: 1px solid #e2e8e3;
                border-radius: 8px;
                color: #28372e;
                font-size: 12px;
                selection-background-color: #dcefe2;
                selection-color: #24352c;
            }
            QHeaderView::section {
                background-color: #f3f6f3;
                color: #65736a;
                border: none;
                border-bottom: 1px solid #e2e8e3;
                padding: 9px 7px;
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 6px;
            }
        """)

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        for column in config.get("stretch", []):
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.Stretch
            )

        layout.addWidget(table, 1)

        self.tabs.addTab(page, self._tab_title(key))
        self.tables[key] = table
        self.tab_keys[self.tabs.count() - 1] = key

        self._populate_report_table(key)

    def _report_config(self, key):
        configs = {
            "deals": {
                "headers": [
                    "ID", "Объект", "Клиент", "Тип", "Сумма",
                    "Комиссия", "Статус", "Создана",
                ],
                "description": (
                    "Сделки, доступные вашей учётной записи. "
                    "Суммы не означают фактически полученную выручку."
                ),
                "stretch": [1, 2],
            },
            "documents": {
                "headers": [
                    "ID", "Тип", "Название", "Сделка", "Сумма",
                    "Статус", "Версия", "Дата",
                ],
                "description": (
                    "Документы, которые сервер разрешает "
                    "просматривать вашей роли."
                ),
                "stretch": [2],
            },
            "properties": {
                "headers": [
                    "ID", "Объект", "Адрес", "Тип", "Площадь, м²",
                    "Цена", "Статус", "Создан",
                ],
                "description": "Объекты недвижимости за выбранный период.",
                "stretch": [1, 2],
            },
            "clients": {
                "headers": [
                    "ID", "Клиент", "Телефон", "Тип", "Статус", "Создан",
                ],
                "description": "Клиенты за выбранный период.",
                "stretch": [1],
            },
            "users": {
                "headers": [
                    "ID", "Сотрудник", "Логин", "Телефон", "Роль", "Статус",
                ],
                "description": (
                    "Список сотрудников и состояние их учётных записей."
                ),
                "stretch": [1],
            },
        }

        return configs.get(key)

    def _populate_report_table(self, key):
        table = self.tables.get(key)

        if table is None:
            return

        table.setRowCount(0)
        records = self._active_records(key)

        for row_index, record in enumerate(records):
            if key == "deals":
                values = [
                    record.get("id", "—"),
                    record.get("propertyTitle", "—"),
                    record.get("clientName", "—"),
                    DEAL_KIND_LABELS.get(
                        record.get("kind"),
                        record.get("kind", "—"),
                    ),
                    self._money(record.get("amount", "0")),
                    self._money(record.get("commission", "0")),
                    DEAL_STATUS_LABELS.get(
                        record.get("status"),
                        record.get("status", "—"),
                    ),
                    self._date_text(record.get("createdAt")),
                ]

            elif key == "documents":
                values = [
                    record.get("id", "—"),
                    DOCUMENT_KIND_LABELS.get(
                        record.get("kind"),
                        record.get("kind", "—"),
                    ),
                    record.get("title", "—"),
                    record.get("dealId", "—"),
                    self._money(record.get("amount", "0")),
                    DOCUMENT_STATUS_LABELS.get(
                        record.get("status"),
                        record.get("status", "—"),
                    ),
                    record.get("version", "—"),
                    self._date_text(record.get("createdAt")),
                ]

            elif key == "properties":
                values = [
                    record.get("id", "—"),
                    record.get("title", "—"),
                    record.get("address", "—"),
                    record.get("type", "—"),
                    record.get("area", "—"),
                    self._money(record.get("price", "0")),
                    PROPERTY_STATUS_LABELS.get(
                        record.get("status"),
                        record.get("status", "—"),
                    ),
                    self._date_text(record.get("createdAt")),
                ]

            elif key == "clients":
                values = [
                    record.get("id", "—"),
                    record.get("fullName", "—"),
                    record.get("phone", "—"),
                    CLIENT_TYPE_LABELS.get(
                        record.get("type"),
                        record.get("type", "—"),
                    ),
                    CLIENT_STATUS_LABELS.get(
                        record.get("status"),
                        record.get("status", "—"),
                    ),
                    self._date_text(record.get("createdAt")),
                ]

            elif key == "users":
                values = [
                    record.get("id", "—"),
                    record.get("fullName", "—"),
                    record.get("login", "—") or "—",
                    record.get("phone", "—") or "—",
                    ROLE_LABELS.get(
                        record.get("role"),
                        record.get("role", "—"),
                    ),
                    USER_STATUS_LABELS.get(
                        record.get("status"),
                        record.get("status", "—"),
                    ),
                ]

            else:
                continue

            table.insertRow(row_index)

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                if column == 0:
                    item.setTextAlignment(Qt.AlignCenter)

                if (
                    key == "deals"
                    and column == 6
                    and record.get("status") == "completed"
                ):
                    item.setForeground(Qt.darkGreen)

                if key == "documents" and column == 5:
                    if record.get("status") == "approved":
                        item.setForeground(Qt.darkGreen)
                    elif record.get("status") == "paid":
                        item.setForeground(Qt.darkBlue)

                if (
                    key == "users"
                    and column == 5
                    and record.get("status") == "pending"
                ):
                    item.setForeground(Qt.darkYellow)

                table.setItem(row_index, column, item)

            table.setRowHeight(row_index, 42)

    def export_current_report(self):
        current_index = self.tabs.currentIndex()
        key = self.tab_keys.get(current_index)
        config = self._report_config(key) if key else None

        if not key or not config:
            QMessageBox.information(
                self,
                "Нет отчёта",
                "Выберите вкладку с данными для экспорта.",
            )
            return

        default_name = (
            f"otchet_{key}_{date.today().isoformat()}.csv"
        )

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт",
            str(Path.home() / default_name),
            "CSV-файл (*.csv)",
        )

        if not path:
            return

        if not path.lower().endswith(".csv"):
            path += ".csv"

        table = self.tables.get(key)

        try:
            with open(
                path, "w", newline="", encoding="utf-8-sig"
            ) as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow(config["headers"])

                for row in range(table.rowCount()):
                    writer.writerow([
                        table.item(row, column).text()
                        if table.item(row, column)
                        else ""
                        for column in range(table.columnCount())
                    ])

            QMessageBox.information(
                self,
                "Отчёт сохранён",
                f"Файл сохранён:\n{path}",
            )

        except OSError as error:
            QMessageBox.warning(
                self,
                "Не удалось сохранить отчёт",
                str(error),
            )

    def set_token(self, token):
        self.token = token
        self.refresh_data()
