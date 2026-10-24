
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QFormLayout, QMessageBox,
    QTextEdit, QDialogButtonBox,
)

from gge import service


KIND_LABELS = {
    "contract": "Договор",
    "invoice": "Счёт",
    "act": "Акт",
}

STATUS_LABELS = {
    "draft": "Черновик",
    "approved": "Утверждён",
    "paid": "Оплачен",
}

DEAL_STATUS_LABELS = {
    "active": "В работе",
    "completed": "Оформлена",
    "cancelled": "Отменена",
    "ended": "Аренда завершена",
}

DEAL_KIND_LABELS = {
    "sale": "Продажа",
    "rent": "Аренда",
}

ROLE_KIND_CHOICES = {
    "lawyer": ["contract"],
    "accountant": ["invoice", "act"],
    "agent": [],
}


class DocumentEditorDialog(QDialog):
    def __init__(
        self,
        token,
        role,
        deals,
        documents,
        parent=None,
        data=None,
    ):
        super().__init__(parent)

        self.token = token
        self.role = role
        self.deals = deals
        self.documents = documents
        self.data = dict(data or {})
        self.result_data = None
        self.is_edit = bool(data)

        self.setWindowTitle(
            "Новая версия документа"
            if data else "Создание документа"
        )
        self.setMinimumSize(560, 490)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(12)

        self.deal_input = QComboBox()
        self.deal_input.setMinimumHeight(36)

        self.kind_input = QComboBox()
        self.kind_input.setMinimumHeight(36)

        self.title_input = QLineEdit(
            str(self.data.get("title", ""))
        )
        self.title_input.setMaxLength(200)
        self.title_input.setMinimumHeight(36)
        self.title_input.setPlaceholderText(
            "Например, договор купли-продажи"
        )

        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText(
            "Введите текст документа"
        )
        self.body_input.setPlainText(
            str(self.data.get("body", ""))
        )

        if self.is_edit:
            self.deal_input.addItem(
                self.deal_caption(
                    self.find_deal(self.data.get("dealId"))
                ),
                self.data.get("dealId"),
            )
            self.deal_input.setEnabled(False)

            self.kind_input.addItem(
                KIND_LABELS.get(
                    self.data.get("kind"),
                    self.data.get("kind", "Документ"),
                ),
                self.data.get("kind"),
            )
            self.kind_input.setEnabled(False)

        else:
            active_deals = [
                deal for deal in deals
                if deal.get("status") == "active"
            ]

            for deal in active_deals:
                self.deal_input.addItem(
                    self.deal_caption(deal),
                    deal.get("id"),
                )

            self.deal_input.currentIndexChanged.connect(
                self.update_available_kinds
            )
            self.update_available_kinds()

        form.addRow("Сделка:", self.deal_input)
        form.addRow("Тип документа:", self.kind_input)
        form.addRow("Название:", self.title_input)
        form.addRow("Текст документа:", self.body_input)

        root.addLayout(form, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )

        buttons.button(
            QDialogButtonBox.Save
        ).setText("Сохранить")

        buttons.button(
            QDialogButtonBox.Cancel
        ).setText("Отмена")

        buttons.button(
            QDialogButtonBox.Save
        ).setObjectName("primary")

        buttons.button(
            QDialogButtonBox.Save
        ).setMinimumHeight(38)

        buttons.button(
            QDialogButtonBox.Cancel
        ).setObjectName("secondary")

        buttons.button(
            QDialogButtonBox.Cancel
        ).setMinimumHeight(38)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        root.addWidget(buttons)

    @staticmethod
    def deal_caption(deal):
        if not deal:
            return "Сделка недоступна"

        kind = DEAL_KIND_LABELS.get(
            deal.get("kind"),
            deal.get("kind", "Сделка"),
        )

        return (
            f'#{deal.get("id")} · '
            f'{deal.get("propertyTitle", "Объект")} · '
            f'{deal.get("clientName", "Клиент")} · {kind}'
        )

    def find_deal(self, deal_id):
        return next(
            (
                deal for deal in self.deals
                if str(deal.get("id")) == str(deal_id)
            ),
            None,
        )

    def update_available_kinds(self, *_):
        current_deal_id = self.deal_input.currentData()

        already_exists = {
            item.get("kind")
            for item in self.documents
            if str(item.get("dealId")) == str(current_deal_id)
        }

        current_kind = self.kind_input.currentData()

        self.kind_input.blockSignals(True)
        self.kind_input.clear()

        for kind in ROLE_KIND_CHOICES.get(self.role, []):
            if kind not in already_exists:
                self.kind_input.addItem(
                    KIND_LABELS[kind],
                    kind,
                )

        if current_kind is not None:
            index = self.kind_input.findData(current_kind)

            if index >= 0:
                self.kind_input.setCurrentIndex(index)

        self.kind_input.blockSignals(False)

        has_choices = self.kind_input.count() > 0

        if not has_choices:
            self.kind_input.addItem(
                "Нет доступных типов документа",
                None,
            )

        self.kind_input.setEnabled(has_choices)

    def save(self):
        title = self.title_input.text().strip()
        body = self.body_input.toPlainText().strip()

        if not title:
            QMessageBox.warning(
                self,
                "Не указано название",
                "Введите название документа.",
            )
            self.title_input.setFocus()
            return

        if not body:
            QMessageBox.warning(
                self,
                "Не заполнен текст",
                "Введите текст документа.",
            )
            self.body_input.setFocus()
            return

        if len(body) > 20000:
            QMessageBox.warning(
                self,
                "Слишком длинный текст",
                "Текст документа не должен превышать 20 000 символов.",
            )
            return

        if not self.is_edit:
            deal_id = self.deal_input.currentData()
            kind = self.kind_input.currentData()

            if deal_id is None:
                QMessageBox.warning(
                    self,
                    "Нет доступной сделки",
                    "Для создания документа нужна сделка "
                    "со статусом «В работе».",
                )
                return

            if kind is None:
                QMessageBox.warning(
                    self,
                    "Нет доступного типа",
                    "Для выбранной сделки документ этого типа "
                    "уже существует.",
                )
                return

            self.result_data = {
                "dealId": deal_id,
                "kind": kind,
                "title": title,
                "body": body,
            }

        else:
            self.result_data = {
                "id": self.data.get("id"),
                "title": title,
                "body": body,
            }

        self.accept()


class DocumentViewDialog(QDialog):
    def __init__(self, document, deal=None, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Документ")
        self.resize(680, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        deal = deal or {}

        number = document.get(
            "number",
            f'DOC-{document.get("id", 0):06d}',
        )

        kind = KIND_LABELS.get(
            document.get("kind"),
            document.get("kind", "Документ"),
        )

        status = STATUS_LABELS.get(
            document.get("status"),
            document.get("status", "—"),
        )

        amount = document.get("amount", "0.00")

        heading = QLabel(f"{kind} · {number}")
        heading.setStyleSheet(
            "font-size: 21px; font-weight: 600; color: #24352c;"
        )
        root.addWidget(heading)

        metadata = QLabel(
            f'Название: {document.get("title", "—")}\n'
            f'Сделка: #{document.get("dealId", "—")} — '
            f'{deal.get("propertyTitle", "Объект")}\n'
            f'Клиент: {deal.get("clientName", "—")}\n'
            f'Сумма: {amount} ₽\n'
            f'Статус: {status}\n'
            f'Версия: {document.get("version", "—")}\n'
            f'Создан: {str(document.get("createdAt", "—")).replace("T", " ")[:19]}\n'
            f'Изменён: {str(document.get("updatedAt", "—")).replace("T", " ")[:19]}'
        )

        metadata.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        metadata.setStyleSheet(
            "color: #526158; font-size: 13px; line-height: 1.4;"
        )
        root.addWidget(metadata)

        body_label = QLabel("Текст документа")
        body_label.setStyleSheet(
            "font-weight: 600; color: #24352c;"
        )
        root.addWidget(body_label)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setPlainText(str(document.get("body", "")))
        root.addWidget(body, 1)

        close_button = QPushButton("Закрыть")
        close_button.setObjectName("secondary")
        close_button.setMinimumHeight(38)
        close_button.clicked.connect(self.accept)

        root.addWidget(
            close_button,
            alignment=Qt.AlignRight,
        )


class DocumentHistoryDialog(QDialog):
    def __init__(self, versions, parent=None):
        super().__init__(parent)

        self.setWindowTitle("История версий документа")
        self.resize(620, 440)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(12)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "Версия",
            "Дата",
            "Название",
            "Статус",
        ])

        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )

        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.Stretch
        )

        for column in (0, 1, 3):
            self.table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        for row, version in enumerate(versions):
            self.table.insertRow(row)

            values = [
                version.get("version", "—"),
                str(
                    version.get("createdAt", "—")
                ).replace("T", " ")[:19],
                version.get("title", "—"),
                STATUS_LABELS.get(
                    version.get("status"),
                    version.get("status", "—"),
                ),
            ]

            for column, value in enumerate(values):
                self.table.setItem(
                    row,
                    column,
                    QTableWidgetItem(str(value)),
                )

        root.addWidget(self.table, 1)

        self.body = QTextEdit()
        self.body.setReadOnly(True)
        self.body.setPlaceholderText(
            "Выберите версию, чтобы посмотреть текст"
        )
        self.body.setMaximumHeight(150)

        self.table.itemSelectionChanged.connect(
            self.show_selected_version
        )

        self.versions = versions
        root.addWidget(self.body)

        close_button = QPushButton("Закрыть")
        close_button.setObjectName("secondary")
        close_button.setMinimumHeight(38)
        close_button.clicked.connect(self.accept)

        root.addWidget(
            close_button,
            alignment=Qt.AlignRight,
        )

        if versions:
            self.table.selectRow(len(versions) - 1)

    def show_selected_version(self):
        row = self.table.currentRow()

        if 0 <= row < len(self.versions):
            version = self.versions[row]
            self.body.setPlainText(
                str(version.get("body", ""))
            )


class DocumentsPage(QWidget):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.profile = {}
        self.role = None
        self.documents = []
        self.deals = []
        self.deals_by_id = {}

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()

        title = QLabel("Документы")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; color: #24352c;"
        )

        subtitle = QLabel(
            "Договоры, счета и акты по сделкам агентства"
        )
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet(
            "font-size: 13px; color: #7b877f;"
        )

        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch()

        self.add_button = QPushButton("+ Создать документ")
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumHeight(40)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(
            lambda checked=False: self.create_document()
        )

        header.addWidget(self.add_button)
        root.addLayout(header)

        filters = QHBoxLayout()
        filters.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("search")
        self.search_input.setMinimumHeight(38)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setPlaceholderText(
            "Поиск по номеру, названию, сделке или клиенту..."
        )
        self.search_input.textChanged.connect(self.fill_table)

        self.kind_filter = QComboBox()
        self.kind_filter.setMinimumHeight(38)
        self.kind_filter.addItem("Все типы", "all")

        for code, label in KIND_LABELS.items():
            self.kind_filter.addItem(label, code)

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

        inside = QVBoxLayout(panel)
        inside.setContentsMargins(18, 18, 18, 18)
        inside.setSpacing(12)

        toolbar = QHBoxLayout()

        self.count_label = QLabel("Документов: 0")
        self.count_label.setObjectName("section_title")
        self.count_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; color: #24352c;"
        )

        toolbar.addWidget(self.count_label)
        toolbar.addStretch()
        inside.addLayout(toolbar)

        actions = QHBoxLayout()

        self.view_button = QPushButton("Просмотреть")
        self.edit_button = QPushButton("Новая версия")
        self.approve_button = QPushButton("Утвердить")
        self.paid_button = QPushButton("Подтвердить оплату")
        self.history_button = QPushButton("История версий")
        self.refresh_button = QPushButton("Обновить")

        for button in (
            self.view_button,
            self.edit_button,
            self.approve_button,
            self.paid_button,
            self.history_button,
            self.refresh_button,
        ):
            button.setObjectName("secondary")
            button.setMinimumHeight(38)
            button.setCursor(Qt.PointingHandCursor)
            actions.addWidget(button)

        inside.addLayout(actions)

        self.view_button.clicked.connect(
            lambda checked=False: self.view_document()
        )
        self.edit_button.clicked.connect(
            lambda checked=False: self.revise_document()
        )
        self.approve_button.clicked.connect(
            lambda checked=False: self.approve_document()
        )
        self.paid_button.clicked.connect(
            lambda checked=False: self.mark_paid()
        )
        self.history_button.clicked.connect(
            lambda checked=False: self.show_history()
        )
        self.refresh_button.clicked.connect(
            lambda checked=False: self.refresh_data()
        )

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Номер",
            "Документ",
            "Сделка",
            "Клиент",
            "Сумма",
            "Статус",
            "Версия",
        ])

        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        header_view = self.table.horizontalHeader()

        for column in (1, 5, 6, 7):
            header_view.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        for column in (0, 2, 3, 4):
            header_view.setSectionResizeMode(
                column,
                QHeaderView.Stretch,
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
        self.table.cellDoubleClicked.connect(
            lambda row, column: self.view_document()
        )

        inside.addWidget(self.table, 1)
        root.addWidget(panel, 1)

        self.update_action_buttons()

    def refresh_data(self, *_):
        if not self.token:
            self.profile = {}
            self.role = None
            self.documents = []
            self.deals = []
            self.deals_by_id = {}
            self.fill_table()
            self.update_action_buttons()
            return

        try:
            self.profile = service.getProfile(self.token) or {}
            self.role = self.profile.get("role")

            self.documents = (
                service.getDocuments(self.token) or []
            )
            self.deals = service.getDeals(self.token) or []

            self.deals_by_id = {
                str(deal.get("id")): deal
                for deal in self.deals
            }

            self.fill_table()

        except Exception as error:
            self.documents = []
            self.deals = []
            self.deals_by_id = {}
            self.fill_table()

            QMessageBox.warning(
                self,
                "Не удалось загрузить документы",
                str(error),
            )

        self.update_action_buttons()

    def fill_table(self, *_args, selected_id=None):
        if selected_id is None:
            selected_id = self.selected_document_id(
                show_message=False
            )

        needle = self.search_input.text().strip().casefold()
        selected_kind = self.kind_filter.currentData()
        selected_status = self.status_filter.currentData()

        rows = []

        for document in self.documents:
            deal = self.deals_by_id.get(
                str(document.get("dealId")),
                {},
            )

            if (
                selected_kind != "all"
                and document.get("kind") != selected_kind
            ):
                continue

            if (
                selected_status != "all"
                and document.get("status") != selected_status
            ):
                continue

            searchable = " ".join([
                str(document.get("number", "")),
                str(document.get("title", "")),
                str(document.get("dealId", "")),
                str(deal.get("propertyTitle", "")),
                str(deal.get("clientName", "")),
            ]).casefold()

            if needle and needle not in searchable:
                continue

            rows.append(document)

        self.table.setRowCount(0)

        for row, document in enumerate(rows):
            deal = self.deals_by_id.get(
                str(document.get("dealId")),
                {},
            )

            values = [
                document.get("id", ""),
                document.get(
                    "number",
                    f'DOC-{document.get("id", 0):06d}',
                ),
                (
                    f'{KIND_LABELS.get(document.get("kind"), document.get("kind", "Документ"))}: '
                    f'{document.get("title", "Без названия")}'
                ),
                (
                    f'#{document.get("dealId", "—")} · '
                    f'{deal.get("propertyTitle", "Объект")}'
                ),
                deal.get("clientName", "—"),
                f'{document.get("amount", "0.00")} ₽',
                STATUS_LABELS.get(
                    document.get("status"),
                    document.get("status", "—"),
                ),
                document.get("version", "—"),
            ]

            self.table.insertRow(row)

            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setFlags(
                    cell.flags() & ~Qt.ItemIsEditable
                )

                if column in (0, 1, 5, 6, 7):
                    cell.setTextAlignment(Qt.AlignCenter)

                if column == 0:
                    cell.setData(
                        Qt.UserRole,
                        str(document.get("id", "")),
                    )

                if column == 6:
                    if document.get("status") == "approved":
                        cell.setForeground(
                            QBrush(QColor("#2f7650"))
                        )
                    elif document.get("status") == "paid":
                        cell.setForeground(
                            QBrush(QColor("#356a91"))
                        )

                self.table.setItem(row, column, cell)

            self.table.setRowHeight(row, 44)

        self.count_label.setText(
            f"Найдено документов: {len(rows)}"
        )

        if selected_id is not None:
            for row in range(self.table.rowCount()):
                cell = self.table.item(row, 0)

                if (
                    cell
                    and str(cell.data(Qt.UserRole))
                    == str(selected_id)
                ):
                    self.table.setCurrentCell(row, 1)
                    self.table.selectRow(row)
                    break

        self.update_action_buttons()

    def select_table_row(self, row, column=0):
        if 0 <= row < self.table.rowCount():
            target_column = column if column > 0 else 1

            self.table.setCurrentCell(row, target_column)
            self.table.selectRow(row)
            self.table.setFocus(Qt.MouseFocusReason)

        self.update_action_buttons()

    def selected_document_id(self, show_message=True):
        row = -1

        if hasattr(self, "table"):
            selected_rows = (
                self.table.selectionModel().selectedRows()
            )

            if selected_rows:
                row = selected_rows[0].row()

            if row < 0:
                row = self.table.currentRow()

            if row < 0 and self.table.selectedRanges():
                row = self.table.selectedRanges()[0].topRow()

        if (
            row < 0
            or self.table.item(row, 0) is None
        ):
            if show_message:
                QMessageBox.information(
                    self,
                    "Документ не выбран",
                    "Выберите строку документа в таблице, "
                    "затем нажмите нужную кнопку.",
                )
            return None

        item = self.table.item(row, 0)
        document_id = item.data(Qt.UserRole)

        if document_id in (None, ""):
            document_id = item.text()

        return (
            str(document_id)
            if document_id not in (None, "")
            else None
        )

    def selected_document(self, show_message=True):
        document_id = self.selected_document_id(
            show_message=show_message
        )

        if document_id is None:
            return None

        document = next(
            (
                item for item in self.documents
                if str(item.get("id")) == document_id
            ),
            None,
        )

        if document is None and show_message:
            QMessageBox.warning(
                self,
                "Документ не найден",
                "Обновите список и выберите документ ещё раз.",
            )

        return document

    def update_action_buttons(self):
        logged_in = bool(self.token)

        for button in (
            self.view_button,
            self.edit_button,
            self.approve_button,
            self.paid_button,
            self.history_button,
        ):
            button.setEnabled(logged_in)

        self.add_button.setEnabled(logged_in)
        self.refresh_button.setEnabled(True)

    def create_document(self):
        if self.role not in {"lawyer", "accountant"}:
            QMessageBox.information(
                self,
                "Недостаточно прав",
                "Создавать документы могут юрист и бухгалтер. "
                "Агент может просматривать документы своих сделок.",
            )
            return

        active_deals = [
            deal for deal in self.deals
            if deal.get("status") == "active"
        ]

        if not active_deals:
            QMessageBox.information(
                self,
                "Нет активных сделок",
                "Для документа нужна сделка со статусом «В работе».",
            )
            return

        dialog = DocumentEditorDialog(
            self.token,
            self.role,
            active_deals,
            self.documents,
            self,
        )

        if (
            dialog.exec_() != QDialog.Accepted
            or not dialog.result_data
        ):
            return

        data = dialog.result_data

        try:
            service.createDocument(
                self.token,
                dealId=data["dealId"],
                kind=data["kind"],
                title=data["title"],
                body=data["body"],
            )

            self.refresh_data()

            QMessageBox.information(
                self,
                "Готово",
                "Документ создан.",
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось создать документ",
                str(error),
            )

    def view_document(self):
        document = self.selected_document()

        if not document:
            return

        deal = self.deals_by_id.get(
            str(document.get("dealId")),
            {},
        )

        DocumentViewDialog(
            document,
            deal,
            self,
        ).exec_()

    def revise_document(self):
        document = self.selected_document()

        if not document:
            return

        if (
            self.role not in ROLE_KIND_CHOICES
            or document.get("kind")
            not in ROLE_KIND_CHOICES.get(self.role, [])
        ):
            QMessageBox.information(
                self,
                "Недостаточно прав",
                "Новую версию этого типа документа может создавать "
                "только ответственный сотрудник: юрист — для договоров, "
                "бухгалтер — для счетов и актов.",
            )
            return

        if document.get("status") == "paid":
            QMessageBox.information(
                self,
                "Редактирование недоступно",
                "Оплаченный счёт нельзя изменить.",
            )
            return

        deal = self.deals_by_id.get(
            str(document.get("dealId")),
            {},
        )

        if deal.get("status") != "active":
            QMessageBox.information(
                self,
                "Редактирование недоступно",
                "Документы закрытой сделки доступны только для чтения.",
            )
            return

        dialog = DocumentEditorDialog(
            self.token,
            self.role,
            self.deals,
            self.documents,
            self,
            data=document,
        )

        if (
            dialog.exec_() != QDialog.Accepted
            or not dialog.result_data
        ):
            return

        data = dialog.result_data

        try:
            updated = service.reviseDocument(
                self.token,
                documentId=data["id"],
                title=data["title"],
                body=data["body"],
            )

            selected_id = (
                updated.get("id", data["id"])
                if isinstance(updated, dict)
                else data["id"]
            )

            self.refresh_data()
            self.fill_table(selected_id=selected_id)

            QMessageBox.information(
                self,
                "Готово",
                "Создана новая версия документа. "
                "Статус документа сброшен на «Черновик».",
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось создать новую версию",
                str(error),
            )

    def approve_document(self):
        document = self.selected_document()

        if not document:
            return

        allowed_kinds = ROLE_KIND_CHOICES.get(
            self.role,
            [],
        )

        if document.get("kind") not in allowed_kinds:
            QMessageBox.information(
                self,
                "Недостаточно прав",
                "Утверждать документ может юрист для договора "
                "или бухгалтер для счёта/акта.",
            )
            return

        if document.get("status") != "draft":
            QMessageBox.information(
                self,
                "Действие недоступно",
                "Утвердить можно только документ со статусом «Черновик».",
            )
            return

        deal = self.deals_by_id.get(
            str(document.get("dealId")),
            {},
        )

        if deal.get("status") != "active":
            QMessageBox.information(
                self,
                "Действие недоступно",
                "Документы закрытой сделки доступны только для чтения.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение",
            f'Утвердить документ '
            f'«{document.get("title", "Без названия")}»?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        try:
            updated = service.approveDocument(
                self.token,
                document.get("id"),
            )

            selected_id = (
                updated.get("id", document.get("id"))
                if isinstance(updated, dict)
                else document.get("id")
            )

            self.refresh_data()
            self.fill_table(selected_id=selected_id)

            QMessageBox.information(
                self,
                "Готово",
                "Документ утверждён.",
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось утвердить документ",
                str(error),
            )

    def mark_paid(self):
        document = self.selected_document()

        if not document:
            return

        if self.role != "accountant":
            QMessageBox.information(
                self,
                "Недостаточно прав",
                "Подтвердить оплату может только бухгалтер.",
            )
            return

        if document.get("kind") != "invoice":
            QMessageBox.information(
                self,
                "Действие недоступно",
                "Подтвердить оплату можно только для счёта.",
            )
            return

        if document.get("status") != "approved":
            QMessageBox.information(
                self,
                "Действие недоступно",
                "Сначала утвердите счёт. Оплату можно подтвердить "
                "только у утверждённого счёта.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение оплаты",
            f'Подтвердить оплату счёта '
            f'«{document.get("title", "Без названия")}»?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        try:
            updated = service.markPaid(
                self.token,
                document.get("id"),
            )

            selected_id = (
                updated.get("id", document.get("id"))
                if isinstance(updated, dict)
                else document.get("id")
            )

            self.refresh_data()
            self.fill_table(selected_id=selected_id)

            QMessageBox.information(
                self,
                "Готово",
                "Оплата счёта подтверждена.",
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось подтвердить оплату",
                str(error),
            )

    def show_history(self):
        document = self.selected_document()

        if not document:
            return

        try:
            versions = service.getDocumentVersions(
                self.token,
                document.get("id"),
            ) or []

            if not versions:
                QMessageBox.information(
                    self,
                    "История пуста",
                    "Для этого документа пока нет сохранённых версий.",
                )
                return

            DocumentHistoryDialog(
                versions,
                self,
            ).exec_()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось загрузить историю",
                str(error),
            )

    def set_token(self, token):
        self.token = token
        self.refresh_data()
