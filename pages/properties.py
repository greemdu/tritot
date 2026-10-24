
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QDialog, QFormLayout, QMessageBox, QDoubleSpinBox,
    QTextEdit
)

from gge import service


STATUS_LABELS = {
    "available": "Доступен",
    "reserved": "Забронирован",
    "sold": "Продан",
    "rented": "Сдан в аренду",
    "archived": "Архив"
}

PROPERTY_TYPES = [
    "Квартира",
    "Дом",
    "Студия",
    "Коммерческая недвижимость",
    "Земельный участок"
]


class PropertyDialog(QDialog):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.result_data = None

        self.setWindowTitle("Новый объект")
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Например, двухкомнатная квартира")

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Город, улица, дом, квартира")

        self.type_input = QComboBox()
        self.type_input.addItems(PROPERTY_TYPES)

        self.area_input = QDoubleSpinBox()
        self.area_input.setRange(0.01, 999999.99)
        self.area_input.setDecimals(2)
        self.area_input.setSuffix(" м²")

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 9999999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setSingleStep(100000)
        self.price_input.setSuffix(" ₽")

        self.owner_input = QComboBox()

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Описание объекта")
        self.description_input.setMaximumHeight(100)

        self.load_owners()

        form.addRow("Название:", self.title_input)
        form.addRow("Адрес:", self.address_input)
        form.addRow("Тип объекта:", self.type_input)
        form.addRow("Площадь:", self.area_input)
        form.addRow("Цена:", self.price_input)
        form.addRow("Собственник:", self.owner_input)
        form.addRow("Описание:", self.description_input)

        root.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("secondary")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("Сохранить")
        save_button.setObjectName("primary")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.clicked.connect(self.save)

        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        root.addLayout(buttons)

    def load_owners(self):
        try:
            clients = service.getClients(self.token) or []

            for client in clients:
                if client.get("status") != "archived":
                    client_id = client.get("id")
                    full_name = client.get("fullName", "Без имени")
                    phone = client.get("phone", "")

                    self.owner_input.addItem(
                        f"{full_name} — {phone}",
                        client_id
                    )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Ошибка загрузки собственников",
                str(error)
            )

    def save(self):
        title = self.title_input.text().strip()
        address = self.address_input.text().strip()

        if not title:
            QMessageBox.warning(
                self,
                "Не заполнено название",
                "Введите название объекта."
            )
            self.title_input.setFocus()
            return

        if not address:
            QMessageBox.warning(
                self,
                "Не заполнен адрес",
                "Введите полный адрес объекта."
            )
            self.address_input.setFocus()
            return

        owner_id = self.owner_input.currentData()

        if owner_id is None:
            QMessageBox.warning(
                self,
                "Не выбран собственник",
                "Сначала добавьте активного клиента в разделе «Клиенты»."
            )
            return

        try:
            self.result_data = service.createProperty(
                self.token,
                title,
                address,
                self.area_input.value(),
                self.price_input.value(),
                owner_id,
                self.type_input.currentText(),
                self.description_input.toPlainText().strip()
            )

            self.accept()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось сохранить объект",
                str(error)
            )


class PropertiesPage(QWidget):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.properties = []

        self.init_ui()
        self.refresh_table()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()

        title = QLabel("Объекты недвижимости")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #24352c;"
        )

        subtitle = QLabel("Каталог недвижимости агентства")
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet("font-size: 13px; color: #7b877f;")

        titles.addWidget(title)
        titles.addWidget(subtitle)

        header.addLayout(titles)
        header.addStretch()

        self.add_button = QPushButton("+ Добавить объект")
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumHeight(40)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_property)

        header.addWidget(self.add_button)
        root.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText(
            "Поиск по названию, адресу или типу..."
        )
        self.search_input.textChanged.connect(self.refresh_table)

        self.type_filter = QComboBox()
        self.type_filter.setMinimumHeight(38)
        self.type_filter.addItem("Все типы", "all")

        for property_type in PROPERTY_TYPES:
            self.type_filter.addItem(property_type, property_type)

        self.type_filter.currentIndexChanged.connect(self.refresh_table)

        self.status_filter = QComboBox()
        self.status_filter.setMinimumHeight(38)
        self.status_filter.addItem("Все статусы", "all")

        for code, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, code)

        self.status_filter.currentIndexChanged.connect(self.refresh_table)

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

        self.count_label = QLabel("Объектов: 0")
        self.count_label.setObjectName("section_title")
        self.count_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #24352c;"
        )

        toolbar.addWidget(self.count_label)
        toolbar.addStretch()

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondary")
        self.refresh_button.setMinimumHeight(38)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(self.refresh_table)

        toolbar.addWidget(self.refresh_button)
        panel_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Название",
            "Адрес",
            "Тип",
            "Площадь",
            "Цена",
            "Статус"
        ])

        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeToContents
        )

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

        panel_layout.addWidget(self.table)
        root.addWidget(panel, 1)

    def refresh_table(self, *_):
        if not self.token:
            self.properties = []
            self.table.setRowCount(0)
            self.count_label.setText("Нет активной сессии")
            return

        try:
            selected_status = self.status_filter.currentData()

            self.properties = service.getProperties(
                self.token,
                search=self.search_input.text().strip(),
                status=None if selected_status == "all" else selected_status
            ) or []

            selected_type = self.type_filter.currentData()

            if selected_type != "all":
                self.properties = [
                    prop for prop in self.properties
                    if prop.get("type") == selected_type
                ]

            self.fill_table()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось загрузить объекты",
                str(error)
            )

    def fill_table(self):
        self.table.setRowCount(0)

        for row, prop in enumerate(self.properties):
            self.table.insertRow(row)

            area = self.format_number(prop.get("area", 0))
            price = self.format_number(prop.get("price", 0))

            values = [
                prop.get("id", ""),
                prop.get("title", ""),
                prop.get("address", ""),
                prop.get("type", ""),
                f"{area} м²",
                f"{price} ₽",
                STATUS_LABELS.get(
                    prop.get("status"),
                    prop.get("status", "—")
                )
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                if column in (0, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignCenter)

                if column == 6 and prop.get("status") == "archived":
                    item.setForeground(QBrush(QColor("#8a6b6b")))

                self.table.setItem(row, column, item)

        self.count_label.setText(
            f"Найдено объектов: {len(self.properties)}"
        )

    @staticmethod
    def format_number(value):
        try:
            number = float(value)
            return f"{number:,.2f}".replace(",", " ")
        except (TypeError, ValueError):
            return str(value or "0")

    def add_property(self):
        if not self.token:
            QMessageBox.warning(
                self,
                "Не выполнен вход",
                "Для добавления объекта необходимо авторизоваться."
            )
            return

        dialog = PropertyDialog(self.token, self)

        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()
            QMessageBox.information(
                self,
                "Готово",
                "Объект успешно добавлен."
            )

    def set_token(self, token):
        self.token = token
        self.refresh_table()
