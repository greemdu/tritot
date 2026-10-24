
import json
from pathlib import Path

from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QFormLayout,
    QMessageBox, QDateEdit, QTimeEdit, QTextEdit
)

from gge import service


STATUSES = {
    "planned": "Запланирован",
    "completed": "Состоялся",
    "cancelled": "Отменён"
}

DATA_DIR = Path.home() / ".territoria_svoih"
DATA_FILE = DATA_DIR / "showings.json"


class ShowingDialog(QDialog):
    def __init__(self, properties, clients, parent=None):
        super().__init__(parent)

        self.properties = properties
        self.clients = clients
        self.result_data = None

        self.setWindowTitle("Назначить показ")
        self.setMinimumWidth(470)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)

        self.property_input = QComboBox()
        self.client_input = QComboBox()

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        self.date_input.setDate(QDate.currentDate())

        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setTime(QTime(12, 0))

        self.employee_input = QLineEdit()
        self.employee_input.setPlaceholderText("Ответственный сотрудник")

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Комментарий к показу")
        self.notes_input.setMaximumHeight(85)

        for prop in self.properties:
            self.property_input.addItem(
                f'{prop.get("title", "Объект")} — {prop.get("address", "")}',
                prop.get("id")
            )

        self.property_input.currentIndexChanged.connect(self.update_clients)
        self.update_clients()

        form.addRow("Объект:", self.property_input)
        form.addRow("Клиент:", self.client_input)
        form.addRow("Дата:", self.date_input)
        form.addRow("Время:", self.time_input)
        form.addRow("Ответственный:", self.employee_input)
        form.addRow("Комментарий:", self.notes_input)

        root.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("secondary")
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("Запланировать")
        save_button.setObjectName("primary")
        save_button.clicked.connect(self.save)

        for button in (cancel_button, save_button):
            button.setCursor(Qt.PointingHandCursor)
            button.setMinimumHeight(38)

        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        root.addLayout(buttons)

    def update_clients(self, *_):
        self.client_input.clear()

        property_id = self.property_input.currentData()
        prop = next(
            (
                item for item in self.properties
                if str(item.get("id")) == str(property_id)
            ),
            {}
        )
        owner_id = prop.get("ownerId")

        for client in self.clients:
            if client.get("status") == "archived":
                continue

            if (
                owner_id is not None
                and str(client.get("id")) == str(owner_id)
            ):
                continue

            self.client_input.addItem(
                f'{client.get("fullName", "Без имени")} — {client.get("phone", "")}',
                client.get("id")
            )

    def save(self):
        property_id = self.property_input.currentData()
        client_id = self.client_input.currentData()

        if property_id is None:
            QMessageBox.warning(
                self,
                "Нет объектов",
                "Нет доступных объектов для показа."
            )
            return

        if client_id is None:
            QMessageBox.warning(
                self,
                "Нет клиентов",
                "Добавьте активного клиента в разделе «Клиенты»."
            )
            return

        date_value = self.date_input.date()
        time_value = self.time_input.time()

        if date_value < QDate.currentDate() or (
            date_value == QDate.currentDate()
            and time_value < QTime.currentTime()
        ):
            QMessageBox.warning(
                self,
                "Неверные дата и время",
                "Показ нельзя назначить на прошедшее время."
            )
            return

        prop = next(
            (
                item for item in self.properties
                if str(item.get("id")) == str(property_id)
            ),
            {}
        )
        client = next(
            (
                item for item in self.clients
                if str(item.get("id")) == str(client_id)
            ),
            {}
        )

        date_text = date_value.toString("yyyy-MM-dd")
        time_text = time_value.toString("HH:mm")

        self.result_data = {
            "propertyId": property_id,
            "propertyTitle": prop.get("title", "Объект"),
            "propertyAddress": prop.get("address", ""),
            "clientId": client_id,
            "clientName": client.get("fullName", "Клиент"),
            "clientPhone": client.get("phone", ""),
            "date": date_text,
            "time": time_text,
            "datetime": f"{date_text} {time_text}",
            "employee": self.employee_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
            "status": "planned"
        }

        self.accept()


class ShowingsPage(QWidget):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.properties = []
        self.clients = []
        self.showings = []

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(18)

        top = QHBoxLayout()
        titles = QVBoxLayout()

        title = QLabel("Показы недвижимости")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #24352c;"
        )

        subtitle = QLabel(
            "Планирование встреч с клиентами и просмотров объектов"
        )
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet("font-size: 13px; color: #7b877f;")

        titles.addWidget(title)
        titles.addWidget(subtitle)

        top.addLayout(titles)
        top.addStretch()

        self.add_button = QPushButton("+ Назначить показ")
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumHeight(40)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_showing)

        top.addWidget(self.add_button)
        root.addLayout(top)

        filters = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText(
            "Поиск по объекту, адресу или клиенту..."
        )
        self.search_input.textChanged.connect(self.fill_table)

        self.status_filter = QComboBox()
        self.status_filter.setMinimumHeight(38)
        self.status_filter.addItem("Все статусы", "all")

        for code, label in STATUSES.items():
            self.status_filter.addItem(label, code)

        self.status_filter.currentIndexChanged.connect(self.fill_table)

        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.status_filter, 1)
        root.addLayout(filters)

        panel = QFrame()
        panel.setObjectName("panel")

        inside = QVBoxLayout(panel)
        inside.setContentsMargins(18, 18, 18, 18)
        inside.setSpacing(14)

        toolbar = QHBoxLayout()

        self.count_label = QLabel("Показов: 0")
        self.count_label.setObjectName("section_title")
        self.count_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #24352c;"
        )

        toolbar.addWidget(self.count_label)
        toolbar.addStretch()

        self.complete_button = QPushButton("Отметить состоявшимся")
        self.cancel_button = QPushButton("Отменить показ")
        self.refresh_button = QPushButton("Обновить")

        for button in (
            self.complete_button,
            self.cancel_button,
            self.refresh_button
        ):
            button.setObjectName("secondary")
            button.setMinimumHeight(38)
            button.setCursor(Qt.PointingHandCursor)
            toolbar.addWidget(button)

        self.complete_button.clicked.connect(self.complete_showing)
        self.cancel_button.clicked.connect(self.cancel_showing)
        self.refresh_button.clicked.connect(self.refresh_data)

        inside.addLayout(toolbar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "Время", "Объект",
            "Адрес", "Клиент", "Ответственный", "Статус"
        ])

        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        header = self.table.horizontalHeader()

        for column in (1, 2, 6, 7):
            header.setSectionResizeMode(
                column, QHeaderView.ResizeToContents
            )

        for column in (0, 3, 4, 5):
            header.setSectionResizeMode(column, QHeaderView.Stretch)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

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

        self.table.itemSelectionChanged.connect(self.update_action_buttons)
        self.table.cellClicked.connect(self.select_table_row)

        inside.addWidget(self.table)
        root.addWidget(panel, 1)

        self.update_action_buttons()

    def select_table_row(self, row, column):
        self.table.selectRow(row)
        self.update_action_buttons()

    def load_showings(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            if not DATA_FILE.exists():
                DATA_FILE.write_text("[]", encoding="utf-8")

            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            self.showings = [
                item for item in data if isinstance(item, dict)
            ] if isinstance(data, list) else []

        except (OSError, json.JSONDecodeError) as error:
            self.showings = []
            QMessageBox.warning(
                self,
                "Не удалось загрузить показы",
                str(error)
            )

    def save_showings(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            DATA_FILE.write_text(
                json.dumps(
                    self.showings,
                    ensure_ascii=False,
                    indent=2
                ),
                encoding="utf-8"
            )
            return True

        except OSError as error:
            QMessageBox.critical(
                self,
                "Не удалось сохранить показ",
                str(error)
            )
            return False

    def refresh_data(self, *_):
        if not self.token:
            self.properties = []
            self.clients = []
            self.load_showings()
            self.fill_table()
            return

        try:
            self.properties = [
                prop
                for prop in (service.getProperties(self.token) or [])
                if prop.get("status") == "available"
            ]

            self.clients = [
                client
                for client in (service.getClients(self.token) or [])
                if client.get("status") != "archived"
            ]

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось загрузить объекты и клиентов",
                str(error)
            )

        self.load_showings()
        self.fill_table()

    def fill_table(self, *_):
        search = self.search_input.text().strip().casefold()
        wanted_status = self.status_filter.currentData()
        selected_id = self.selected_showing_id()
        rows = []

        for showing in self.showings:
            searchable_text = " ".join(
                str(showing.get(key, ""))
                for key in (
                    "propertyTitle",
                    "propertyAddress",
                    "clientName",
                    "employee"
                )
            ).casefold()

            if search and search not in searchable_text:
                continue

            if (
                wanted_status != "all"
                and showing.get("status") != wanted_status
            ):
                continue

            rows.append(showing)

        rows.sort(
            key=lambda item: (
                item.get("date", ""),
                item.get("time", "")
            )
        )

        self.table.setRowCount(0)

        for row_index, showing in enumerate(rows):
            self.table.insertRow(row_index)

            date_text = QDate.fromString(
                showing.get("date", ""), "yyyy-MM-dd"
            ).toString("dd.MM.yyyy")

            values = [
                showing.get("id", ""),
                date_text,
                showing.get("time", ""),
                showing.get("propertyTitle", ""),
                showing.get("propertyAddress", ""),
                showing.get("clientName", ""),
                showing.get("employee", "") or "—",
                STATUSES.get(showing.get("status"), "—")
            ]

            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)

                if column in (0, 1, 2, 7):
                    cell.setTextAlignment(Qt.AlignCenter)

                if column == 7 and showing.get("status") == "cancelled":
                    cell.setForeground(QBrush(QColor("#8a6b6b")))

                self.table.setItem(row_index, column, cell)

            self.table.setRowHeight(row_index, 44)

        self.count_label.setText(f"Найдено показов: {len(rows)}")

        if selected_id is not None:
            for row_index in range(self.table.rowCount()):
                cell = self.table.item(row_index, 0)
                if cell and cell.text() == str(selected_id):
                    self.table.selectRow(row_index)
                    break

        self.update_action_buttons()

    def selected_showing_id(self):
        row = self.table.currentRow() if hasattr(self, "table") else -1

        if row < 0:
            return None

        cell = self.table.item(row, 0)
        if cell is None:
            return None

        try:
            return int(cell.text())
        except (ValueError, TypeError):
            return None

    def selected_showing(self):
        showing_id = self.selected_showing_id()

        if showing_id is None:
            QMessageBox.information(
                self,
                "Показ не выбран",
                "Сначала выберите показ в таблице."
            )
            return None

        return next(
            (
                item for item in self.showings
                if str(item.get("id")) == str(showing_id)
            ),
            None
        )

    def update_action_buttons(self):
        self.complete_button.setEnabled(bool(self.token))
        self.cancel_button.setEnabled(bool(self.token))

    def add_showing(self):
        if not self.token:
            QMessageBox.warning(
                self,
                "Не выполнен вход",
                "Для назначения показа необходимо авторизоваться."
            )
            return

        try:
            properties = [
                prop
                for prop in (service.getProperties(self.token) or [])
                if prop.get("status") == "available"
            ]

            clients = [
                client
                for client in (service.getClients(self.token) or [])
                if client.get("status") != "archived"
            ]

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось загрузить данные",
                str(error)
            )
            return

        if not properties:
            QMessageBox.information(
                self,
                "Нет доступных объектов",
                "Сначала добавьте объект со статусом «Доступен»."
            )
            return

        if not clients:
            QMessageBox.information(
                self,
                "Нет активных клиентов",
                "Сначала добавьте клиента в разделе «Клиенты»."
            )
            return

        dialog = ShowingDialog(properties, clients, self)

        if dialog.exec_() != QDialog.Accepted:
            return

        new_item = dialog.result_data

        conflict = any(
            old.get("status") == "planned"
            and str(old.get("propertyId")) == str(new_item["propertyId"])
            and old.get("datetime") == new_item["datetime"]
            for old in self.showings
        )

        if conflict:
            QMessageBox.warning(
                self,
                "Время занято",
                "На этот объект уже назначен показ в выбранное время."
            )
            return

        new_item["id"] = max(
            (int(item.get("id", 0)) for item in self.showings),
            default=0
        ) + 1

        self.showings.append(new_item)

        if self.save_showings():
            self.fill_table()
            QMessageBox.information(
                self,
                "Готово",
                "Показ успешно запланирован."
            )

    def change_status(self, status, question, showing=None):
        if showing is None:
            showing = self.selected_showing()

        if showing is None:
            return

        if showing.get("status") != "planned":
            QMessageBox.information(
                self,
                "Действие недоступно",
                "Изменить можно только запланированный показ."
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение",
            question,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if answer != QMessageBox.Yes:
            return

        previous_status = showing.get("status")
        showing["status"] = status

        if not self.save_showings():
            showing["status"] = previous_status
            return

        self.fill_table()

        QMessageBox.information(
            self,
            "Готово",
            "Статус показа обновлён."
        )

    def complete_showing(self):
        showing = self.selected_showing()
        if showing is None:
            return

        self.change_status(
            "completed",
            f'Отметить показ «{showing.get("propertyTitle", "")}» '
            f'для клиента «{showing.get("clientName", "")}» '
            "как состоявшийся?",
            showing=showing
        )

    def cancel_showing(self):
        showing = self.selected_showing()
        if showing is None:
            return

        self.change_status(
            "cancelled",
            f'Отменить показ «{showing.get("propertyTitle", "")}» '
            f'для клиента «{showing.get("clientName", "")}»?',
            showing=showing
        )

    def set_token(self, token):
        self.token = token
        self.refresh_data()
