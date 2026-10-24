
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QFormLayout, QMessageBox
)

from gge import service


CLIENT_TYPES = {
    "person": "Физическое лицо",
    "company": "Юридическое лицо",
}

CLIENT_STATUSES = {
    "active": "Активный",
    "archived": "В архиве",
}


class ClientDialog(QDialog):
    def __init__(self, token, parent=None, data=None):
        super().__init__(parent)

        self.token = token
        self.data = data or {}
        self.result_data = None

        self.setWindowTitle(
            "Редактирование клиента" if data else "Новый клиент"
        )
        self.setMinimumWidth(470)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.name_input = QLineEdit(
            str(self.data.get("fullName", ""))
        )
        self.name_input.setMinimumHeight(36)
        self.name_input.setPlaceholderText(
            "ФИО или наименование организации"
        )

        self.phone_input = QLineEdit(
            str(self.data.get("phone", ""))
        )
        self.phone_input.setMinimumHeight(36)
        self.phone_input.setPlaceholderText("Номер телефона")

        self.type_input = QComboBox()
        self.type_input.setMinimumHeight(36)

        for code, label in CLIENT_TYPES.items():
            self.type_input.addItem(label, code)

        current_type = self.data.get("type", "person")
        type_index = self.type_input.findData(current_type)
        self.type_input.setCurrentIndex(
            type_index if type_index >= 0 else 0
        )

        form.addRow("ФИО / организация:", self.name_input)
        form.addRow("Телефон:", self.phone_input)
        form.addRow("Тип клиента:", self.type_input)

        root.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("secondary")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.setMinimumHeight(38)
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton(
            "Сохранить" if data else "Добавить клиента"
        )
        save_button.setObjectName("primary")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.setMinimumHeight(38)
        save_button.clicked.connect(self.save)

        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        root.addLayout(buttons)

    def save(self):
        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        client_type = self.type_input.currentData()

        if not full_name:
            QMessageBox.warning(
                self,
                "Не указано имя",
                "Введите ФИО клиента или наименование организации."
            )
            self.name_input.setFocus()
            return

        if not phone:
            QMessageBox.warning(
                self,
                "Не указан телефон",
                "Введите номер телефона клиента."
            )
            self.phone_input.setFocus()
            return

        try:
            if self.data:
                self.result_data = service.updateClient(
                    self.token,
                    self.data.get("id"),
                    full_name,
                    phone,
                    client_type,
                )
            else:
                self.result_data = service.createClient(
                    self.token,
                    full_name,
                    phone,
                    client_type,
                )

            self.accept()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось сохранить клиента",
                str(error)
            )


class ClientsPage(QWidget):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.clients = []

        self.init_ui()
        self.refresh_table()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()

        title = QLabel("Клиенты")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #24352c;"
        )

        subtitle = QLabel(
            "Контакты клиентов и собственников недвижимости"
        )
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet(
            "font-size: 13px; color: #7b877f;"
        )

        titles.addWidget(title)
        titles.addWidget(subtitle)

        header.addLayout(titles)
        header.addStretch()

        self.add_button = QPushButton("+ Добавить клиента")
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumHeight(40)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_client)

        header.addWidget(self.add_button)
        root.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText(
            "Поиск по имени или телефону..."
        )
        self.search_input.textChanged.connect(self.refresh_table)

        self.type_filter = QComboBox()
        self.type_filter.setMinimumHeight(38)
        self.type_filter.addItem("Все типы", "all")

        for code, label in CLIENT_TYPES.items():
            self.type_filter.addItem(label, code)

        self.type_filter.currentIndexChanged.connect(self.fill_table)

        self.status_filter = QComboBox()
        self.status_filter.setMinimumHeight(38)
        self.status_filter.addItem("Все статусы", "all")

        for code, label in CLIENT_STATUSES.items():
            self.status_filter.addItem(label, code)

        self.status_filter.currentIndexChanged.connect(self.fill_table)

        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.type_filter, 1)
        filters.addWidget(self.status_filter, 1)

        root.addLayout(filters)

        panel = QFrame()
        panel.setObjectName("panel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(14)

        toolbar = QHBoxLayout()

        self.count_label = QLabel("Клиентов: 0")
        self.count_label.setObjectName("section_title")
        self.count_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #24352c;"
        )

        toolbar.addWidget(self.count_label)
        toolbar.addStretch()

        self.view_button = QPushButton("Просмотреть")
        self.edit_button = QPushButton("Редактировать")
        self.archive_button = QPushButton("В архив")
        self.refresh_button = QPushButton("Обновить")

        for button in (
            self.view_button,
            self.edit_button,
            self.archive_button,
            self.refresh_button,
        ):
            button.setObjectName("secondary")
            button.setMinimumHeight(38)
            button.setCursor(Qt.PointingHandCursor)
            toolbar.addWidget(button)

        self.view_button.clicked.connect(self.view_client)
        self.edit_button.clicked.connect(self.edit_client)
        self.archive_button.clicked.connect(self.archive_client)
        self.refresh_button.clicked.connect(self.refresh_table)

        panel_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Клиент",
            "Телефон",
            "Тип клиента",
            "Статус",
            "Дата добавления",
        ])

        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        header_view.setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )
        header_view.setSectionResizeMode(
            5, QHeaderView.ResizeToContents
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
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

        self.table.itemSelectionChanged.connect(
            self.update_action_buttons
        )
        self.table.cellClicked.connect(self.select_table_row)

        panel_layout.addWidget(self.table)
        root.addWidget(panel, 1)

        self.update_action_buttons()

    def select_table_row(self, row, _column):
        if 0 <= row < self.table.rowCount():
            self.table.selectRow(row)
            self.update_action_buttons()

    def refresh_table(self, *_):
        if not self.token:
            self.clients = []
            self.fill_table()
            self.count_label.setText("Нет активной сессии")
            return

        selected_id = self.selected_client_id(
            show_message=False
        )

        try:
            self.clients = service.getClients(
                self.token,
                search=self.search_input.text().strip(),
            ) or []

            self.fill_table(selected_id=selected_id)

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось загрузить клиентов",
                str(error)
            )

    def fill_table(self, *_args, selected_id=None):
        if selected_id is None:
            selected_id = self.selected_client_id(
                show_message=False
            )

        selected_type = self.type_filter.currentData()
        selected_status = self.status_filter.currentData()

        filtered = []

        for client in self.clients:
            if (
                selected_type != "all"
                and client.get("type") != selected_type
            ):
                continue

            if (
                selected_status != "all"
                and client.get("status") != selected_status
            ):
                continue

            filtered.append(client)

        self.table.setRowCount(0)

        for row, client in enumerate(filtered):
            self.table.insertRow(row)

            created_at = str(client.get("createdAt", ""))
            created_date = created_at[:10] if created_at else "—"

            values = [
                client.get("id", ""),
                client.get("fullName", "Без имени"),
                client.get("phone", "—"),
                CLIENT_TYPES.get(
                    client.get("type"),
                    client.get("type", "—")
                ),
                CLIENT_STATUSES.get(
                    client.get("status"),
                    client.get("status", "—")
                ),
                created_date,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(
                    item.flags() & ~Qt.ItemIsEditable
                )

                if column in (0, 3, 4, 5):
                    item.setTextAlignment(Qt.AlignCenter)

                if column == 0:
                    item.setData(
                        Qt.UserRole,
                        client.get("id")
                    )

                if (
                    column == 4
                    and client.get("status") == "archived"
                ):
                    item.setForeground(
                        QBrush(QColor("#8a6b6b"))
                    )

                self.table.setItem(row, column, item)

            self.table.setRowHeight(row, 44)

        self.count_label.setText(
            f"Найдено клиентов: {len(filtered)}"
        )

        if selected_id is not None:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)

                if (
                    item
                    and str(item.data(Qt.UserRole))
                    == str(selected_id)
                ):
                    self.table.selectRow(row)
                    break

        self.update_action_buttons()

    def selected_client_id(self, show_message=True):
        row = (
            self.table.currentRow()
            if hasattr(self, "table")
            else -1
        )

        if row < 0:
            selection = (
                self.table.selectionModel().selectedRows()
                if hasattr(self, "table")
                else []
            )
            if selection:
                row = selection[0].row()

        if row < 0:
            if show_message:
                QMessageBox.information(
                    self,
                    "Клиент не выбран",
                    "Сначала выберите клиента в таблице."
                )
            return None

        item = self.table.item(row, 0)

        if item is None:
            if show_message:
                QMessageBox.information(
                    self,
                    "Клиент не выбран",
                    "Не удалось определить выбранного клиента."
                )
            return None

        client_id = item.data(Qt.UserRole)

        if client_id is None:
            client_id = item.text()

        try:
            return int(client_id)
        except (TypeError, ValueError):
            return client_id

    def selected_client(self):
        client_id = self.selected_client_id()

        if client_id is None:
            return None

        client = next(
            (
                item for item in self.clients
                if str(item.get("id")) == str(client_id)
            ),
            None,
        )

        if client is None:
            QMessageBox.warning(
                self,
                "Клиент не найден",
                "Обновите список и выберите клиента ещё раз."
            )

        return client

    def update_action_buttons(self):
        enabled = bool(self.token)

        self.view_button.setEnabled(enabled)
        self.edit_button.setEnabled(enabled)
        self.archive_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)

        row = (
            self.table.currentRow()
            if hasattr(self, "table")
            else -1
        )

        if row < 0 and hasattr(self, "table"):
            selection = self.table.selectionModel().selectedRows()
            if selection:
                row = selection[0].row()

        if row >= 0 and self.table.item(row, 0):
            client_id = self.table.item(
                row, 0
            ).data(Qt.UserRole)

            client = next(
                (
                    item for item in self.clients
                    if str(item.get("id")) == str(client_id)
                ),
                None,
            )

            if client and client.get("status") == "archived":
                self.archive_button.setText("Вернуть из архива")
                self.edit_button.setEnabled(False)
            else:
                self.archive_button.setText("В архив")
                self.edit_button.setEnabled(enabled)
        else:
            self.archive_button.setText("В архив")
            self.edit_button.setEnabled(enabled)

    def add_client(self):
        if not self.token:
            QMessageBox.warning(
                self,
                "Не выполнен вход",
                "Для добавления клиента необходимо авторизоваться."
            )
            return

        dialog = ClientDialog(self.token, self)

        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()
            QMessageBox.information(
                self,
                "Готово",
                "Клиент добавлен в базу данных."
            )

    def view_client(self):
        client = self.selected_client()

        if not client:
            return

        created_at = client.get("createdAt", "—")

        if created_at and created_at != "—":
            created_at = str(created_at).replace("T", " ")[:19]

        QMessageBox.information(
            self,
            str(client.get("fullName", "Клиент")),
            f'ID: {client.get("id", "—")}\n'
            f'ФИО / организация: {client.get("fullName", "—")}\n'
            f'Телефон: {client.get("phone", "—")}\n'
            f'Тип: {CLIENT_TYPES.get(client.get("type"), client.get("type", "—"))}\n'
            f'Статус: {CLIENT_STATUSES.get(client.get("status"), client.get("status", "—"))}\n'
            f'Дата добавления: {created_at}',
        )

    def edit_client(self):
        client = self.selected_client()

        if not client:
            return

        if client.get("status") == "archived":
            QMessageBox.information(
                self,
                "Редактирование недоступно",
                "Сначала верните клиента из архива."
            )
            return

        dialog = ClientDialog(
            self.token,
            self,
            data=client
        )

        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()
            QMessageBox.information(
                self,
                "Готово",
                "Данные клиента обновлены."
            )

    def archive_client(self):
        client = self.selected_client()

        if not client:
            return

        currently_archived = client.get("status") == "archived"
        action = (
            "вернуть из архива"
            if currently_archived
            else "перенести в архив"
        )

        answer = QMessageBox.question(
            self,
            "Подтверждение",
            f'Вы действительно хотите {action} клиента '
            f'«{client.get("fullName", "Без имени")}»?\n\n'
            "Сервер не разрешит архивацию, если у клиента есть "
            "действующая сделка или неархивный объект.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        try:
            service.archiveClient(
                self.token,
                client.get("id"),
                archived=not currently_archived,
            )

            self.refresh_table()

            QMessageBox.information(
                self,
                "Готово",
                (
                    "Клиент возвращён из архива."
                    if currently_archived
                    else "Клиент перенесён в архив."
                ),
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось изменить статус клиента",
                str(error)
            )

    def set_token(self, token):
        self.token = token
        self.refresh_table()
