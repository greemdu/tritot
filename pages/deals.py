
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QFormLayout, QMessageBox,
    QDoubleSpinBox, QDateEdit
)

from gge import service


KIND_LABELS = {
    "sale": "Продажа",
    "rent": "Аренда"
}

STATUS_LABELS = {
    "active": "В работе",
    "completed": "Оформлена",
    "cancelled": "Отменена",
    "ended": "Аренда завершена"
}


class DealDialog(QDialog):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.properties = []
        self.clients = []
        self.properties_by_id = {}
        self.result_data = None

        self.setWindowTitle("Новая сделка")
        self.setMinimumWidth(500)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(12)
        self.form = form

        self.property_input = QComboBox()
        self.property_input.setMinimumHeight(36)

        self.client_input = QComboBox()
        self.client_input.setMinimumHeight(36)

        self.kind_input = QComboBox()
        self.kind_input.addItem("Продажа", "sale")
        self.kind_input.addItem("Аренда", "rent")
        self.kind_input.setMinimumHeight(36)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(0.01, 999999999999.99)
        self.amount_input.setDecimals(2)
        self.amount_input.setSingleStep(100000)
        self.amount_input.setSuffix(" ₽")
        self.amount_input.setMinimumHeight(36)

        self.commission_input = QDoubleSpinBox()
        self.commission_input.setRange(0, 999999999999.99)
        self.commission_input.setDecimals(2)
        self.commission_input.setSingleStep(10000)
        self.commission_input.setSuffix(" ₽")
        self.commission_input.setMinimumHeight(36)

        self.start_date_input = QDateEdit()
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("yyyy-MM-dd")
        self.start_date_input.setDate(QDate.currentDate())
        self.start_date_input.setMinimumHeight(36)

        self.end_date_input = QDateEdit()
        self.end_date_input.setCalendarPopup(True)
        self.end_date_input.setDisplayFormat("yyyy-MM-dd")
        self.end_date_input.setDate(QDate.currentDate().addMonths(12))
        self.end_date_input.setMinimumHeight(36)

        form.addRow("Объект:", self.property_input)
        form.addRow("Клиент:", self.client_input)
        form.addRow("Вид сделки:", self.kind_input)
        form.addRow("Сумма / ставка:", self.amount_input)
        form.addRow("Комиссия агентства:", self.commission_input)
        form.addRow("Начало аренды:", self.start_date_input)
        form.addRow("Окончание аренды:", self.end_date_input)

        root.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("secondary")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("Создать сделку")
        save_button.setObjectName("primary")
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.clicked.connect(self.save)

        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)
        root.addLayout(buttons)

        self.property_input.currentIndexChanged.connect(
            self.update_property
        )
        self.kind_input.currentIndexChanged.connect(
            self.update_kind_fields
        )

        self.load_data()
        self.update_kind_fields()

    def load_data(self):
        try:
            self.properties = service.getProperties(
                self.token,
                status="available"
            ) or []

            self.clients = service.getClients(self.token) or []

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось загрузить данные",
                str(error)
            )
            self.reject()
            return

        for prop in self.properties:
            property_id = prop.get("id")
            self.properties_by_id[property_id] = prop

            self.property_input.addItem(
                f'{prop.get("title", "Объект")} — {prop.get("address", "")}',
                property_id
            )

        self.update_property()

    def update_property(self, *_):
        property_id = self.property_input.currentData()
        prop = self.properties_by_id.get(property_id)

        self.client_input.clear()

        if prop is None:
            self.amount_input.setValue(1)
            return

        try:
            self.amount_input.setValue(
                float(prop.get("price", 1))
            )
        except (TypeError, ValueError):
            self.amount_input.setValue(1)

        owner_id = prop.get("ownerId")

        for client in self.clients:
            if client.get("status") == "archived":
                continue

            if (
                owner_id is not None
                and client.get("id") == owner_id
            ):
                continue

            client_id = client.get("id")
            label = (
                f'{client.get("fullName", "Без имени")} — '
                f'{client.get("phone", "")}'
            )

            self.client_input.addItem(label, client_id)

    def update_kind_fields(self, *_):
        is_rent = self.kind_input.currentData() == "rent"

        self.start_date_input.setVisible(is_rent)
        self.end_date_input.setVisible(is_rent)

        start_label = self.form.labelForField(
            self.start_date_input
        )
        end_label = self.form.labelForField(
            self.end_date_input
        )

        if start_label:
            start_label.setVisible(is_rent)

        if end_label:
            end_label.setVisible(is_rent)

    def save(self):
        property_id = self.property_input.currentData()
        client_id = self.client_input.currentData()
        kind = self.kind_input.currentData()

        if property_id is None:
            QMessageBox.warning(
                self,
                "Нет доступных объектов",
                "Добавьте объект со статусом «Доступен» в разделе «Объекты»."
            )
            return

        if client_id is None:
            QMessageBox.warning(
                self,
                "Не выбран клиент",
                "Добавьте активного клиента в разделе «Клиенты»."
            )
            return

        start_date = None
        end_date = None

        if kind == "rent":
            start_date = self.start_date_input.date().toString(
                "yyyy-MM-dd"
            )
            end_date = self.end_date_input.date().toString(
                "yyyy-MM-dd"
            )

            if (
                self.end_date_input.date()
                <= self.start_date_input.date()
            ):
                QMessageBox.warning(
                    self,
                    "Неверные даты",
                    "Дата окончания аренды должна быть позже даты начала."
                )
                return

        try:
            self.result_data = service.createDeal(
                self.token,
                propertyId=property_id,
                clientId=client_id,
                kind=kind,
                amount=self.amount_input.value(),
                commission=self.commission_input.value(),
                startDate=start_date,
                endDate=end_date
            )

            self.accept()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось создать сделку",
                str(error)
            )


class DealsPage(QWidget):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.deals = []

        self.init_ui()
        self.refresh_table()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()

        title = QLabel("Сделки")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #24352c;"
        )

        subtitle = QLabel("Продажи и аренда недвижимости")
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet(
            "font-size: 13px; color: #7b877f;"
        )

        titles.addWidget(title)
        titles.addWidget(subtitle)

        header.addLayout(titles)
        header.addStretch()

        self.add_button = QPushButton("+ Новая сделка")
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumHeight(40)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.add_deal)

        header.addWidget(self.add_button)
        root.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText(
            "Поиск по объекту или клиенту..."
        )
        self.search_input.textChanged.connect(self.fill_table)

        self.kind_filter = QComboBox()
        self.kind_filter.setMinimumHeight(38)
        self.kind_filter.addItem("Все виды", "all")
        self.kind_filter.addItem("Продажа", "sale")
        self.kind_filter.addItem("Аренда", "rent")
        self.kind_filter.currentIndexChanged.connect(
            self.fill_table
        )

        self.status_filter = QComboBox()
        self.status_filter.setMinimumHeight(38)
        self.status_filter.addItem("Все статусы", "all")

        for code, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, code)

        self.status_filter.currentIndexChanged.connect(
            self.fill_table
        )

        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.kind_filter, 1)
        filters.addWidget(self.status_filter, 1)

        root.addLayout(filters)

        panel = QFrame()
        panel.setObjectName("panel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)
        panel_layout.setSpacing(14)

        toolbar = QHBoxLayout()

        self.count_label = QLabel("Сделок: 0")
        self.count_label.setObjectName("section_title")
        self.count_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #24352c;"
        )

        toolbar.addWidget(self.count_label)
        toolbar.addStretch()

        self.complete_button = QPushButton("Оформить")
        self.complete_button.setObjectName("secondary")
        self.complete_button.setCursor(Qt.PointingHandCursor)
        self.complete_button.clicked.connect(
            self.complete_deal
        )

        self.cancel_button = QPushButton("Отменить")
        self.cancel_button.setObjectName("secondary")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(
            self.cancel_deal
        )

        self.end_rent_button = QPushButton("Завершить аренду")
        self.end_rent_button.setObjectName("secondary")
        self.end_rent_button.setCursor(Qt.PointingHandCursor)
        self.end_rent_button.clicked.connect(
            self.end_rent
        )

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("secondary")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.clicked.connect(
            self.refresh_table
        )

        for button in (
            self.complete_button,
            self.cancel_button,
            self.end_rent_button,
            self.refresh_button
        ):
            button.setMinimumHeight(38)
            toolbar.addWidget(button)

        panel_layout.addLayout(toolbar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Объект",
            "Клиент",
            "Вид",
            "Сумма",
            "Комиссия",
            "Статус",
            "Период аренды"
        ])

        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

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

        panel_layout.addWidget(self.table)
        root.addWidget(panel, 1)

        self.update_action_buttons()

    def refresh_table(self, *_):
        if not self.token:
            self.deals = []
            self.fill_table()
            self.count_label.setText("Нет активной сессии")
            return

        try:
            self.deals = service.getDeals(self.token) or []
            self.fill_table()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось загрузить сделки",
                str(error)
            )

    def fill_table(self, *_):
        search = self.search_input.text().strip().casefold()
        selected_kind = self.kind_filter.currentData()
        selected_status = self.status_filter.currentData()

        filtered = []

        for deal in self.deals:
            searchable = (
                str(deal.get("propertyTitle", ""))
                + " "
                + str(deal.get("clientName", ""))
            ).casefold()

            if search and search not in searchable:
                continue

            if (
                selected_kind != "all"
                and deal.get("kind") != selected_kind
            ):
                continue

            if (
                selected_status != "all"
                and deal.get("status") != selected_status
            ):
                continue

            filtered.append(deal)

        selected_id = self.selected_deal_id()
        self.table.setRowCount(0)

        for row, deal in enumerate(filtered):
            self.table.insertRow(row)

            start_date = deal.get("startDate") or ""
            end_date = deal.get("endDate") or ""

            if start_date and end_date:
                period = f"{start_date} — {end_date}"
            else:
                period = "—"

            values = [
                deal.get("id", ""),
                deal.get("propertyTitle", "—"),
                deal.get("clientName", "—"),
                KIND_LABELS.get(
                    deal.get("kind"),
                    deal.get("kind", "—")
                ),
                f'{self.format_number(deal.get("amount", 0))} ₽',
                f'{self.format_number(deal.get("commission", 0))} ₽',
                STATUS_LABELS.get(
                    deal.get("status"),
                    deal.get("status", "—")
                ),
                period
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setFlags(
                    item.flags() & ~Qt.ItemIsEditable
                )

                if column in (0, 3, 4, 5, 6, 7):
                    item.setTextAlignment(Qt.AlignCenter)

                if (
                    column == 6
                    and deal.get("status") == "cancelled"
                ):
                    item.setForeground(
                        QBrush(QColor("#8a6b6b"))
                    )

                self.table.setItem(row, column, item)

            self.table.setRowHeight(row, 44)

        self.count_label.setText(
            f"Найдено сделок: {len(filtered)}"
        )

        if selected_id is not None:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)

                if item and item.text() == str(selected_id):
                    self.table.selectRow(row)
                    break

        self.update_action_buttons()

    @staticmethod
    def format_number(value):
        try:
            return f'{float(value):,.2f}'.replace(",", " ")
        except (TypeError, ValueError):
            return str(value or "0")

    def selected_deal_id(self):
        if not hasattr(self, "table"):
            return None

        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        try:
            return int(item.text())
        except ValueError:
            return None

    def selected_deal(self):
        deal_id = self.selected_deal_id()

        if deal_id is None:
            QMessageBox.information(
                self,
                "Сделка не выбрана",
                "Сначала выберите сделку в таблице."
            )
            return None

        return next(
            (
                deal for deal in self.deals
                if deal.get("id") == deal_id
            ),
            None
        )

    def update_action_buttons(self):
        enabled = bool(self.token)

        self.complete_button.setEnabled(enabled)
        self.cancel_button.setEnabled(enabled)
        self.end_rent_button.setEnabled(enabled)

    def add_deal(self):
        if not self.token:
            QMessageBox.warning(
                self,
                "Не выполнен вход",
                "Для создания сделки необходимо авторизоваться."
            )
            return

        dialog = DealDialog(self.token, self)

        if dialog.exec_() == QDialog.Accepted:
            self.refresh_table()

            QMessageBox.information(
                self,
                "Готово",
                "Сделка создана. Объект зарезервирован."
            )

    def change_status(self, status, confirmation):
        deal = self.selected_deal()

        if not deal:
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение",
            confirmation,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if answer != QMessageBox.Yes:
            return

        try:
            service.changeDealStatus(
                self.token,
                dealId=deal["id"],
                status=status
            )

            self.refresh_table()

            QMessageBox.information(
                self,
                "Готово",
                "Статус сделки обновлён."
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось изменить сделку",
                str(error)
            )

    def complete_deal(self):
        deal = self.selected_deal()

        if not deal:
            return

        if deal.get("status") != "active":
            QMessageBox.information(
                self,
                "Нельзя оформить сделку",
                "Оформить можно только сделку со статусом «В работе»."
            )
            return

        self.change_status(
            "completed",
            f'Оформить сделку «{deal.get("propertyTitle", "")}»?\n\n'
            "Сервер проверит утверждённый договор и оплату комиссии, "
            "если она больше нуля."
        )

    def cancel_deal(self):
        deal = self.selected_deal()

        if not deal:
            return

        if deal.get("status") != "active":
            QMessageBox.information(
                self,
                "Нельзя отменить сделку",
                "Отменить можно только сделку со статусом «В работе»."
            )
            return

        self.change_status(
            "cancelled",
            f'Отменить сделку по объекту '
            f'«{deal.get("propertyTitle", "")}»?'
        )

    def end_rent(self):
        deal = self.selected_deal()

        if not deal:
            return

        if (
            deal.get("kind") != "rent"
            or deal.get("status") != "completed"
        ):
            QMessageBox.information(
                self,
                "Нельзя завершить аренду",
                "Завершить можно только аренду, которая уже оформлена "
                "и имеет статус «Оформлена»."
            )
            return

        self.change_status(
            "ended",
            f'Завершить аренду по объекту '
            f'«{deal.get("propertyTitle", "")}»?'
        )

    def set_token(self, token):
        self.token = token
        self.refresh_table()
