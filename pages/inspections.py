
import json
from pathlib import Path

from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QVBoxLayout,
    QHBoxLayout, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog, QFormLayout,
    QMessageBox, QDateEdit, QTimeEdit, QTextEdit,
)

from gge import service


STATUS_LABELS = {
    "planned": "Запланирована",
    "completed": "Проверена",
    "cancelled": "Отменена",
}

INSPECTION_TYPES = {
    "initial": "Первичный осмотр",
    "pre_sale": "Перед продажей",
    "pre_rent": "Перед сдачей в аренду",
    "repeat": "Повторный осмотр",
}

CONDITION_LABELS = {
    "not_checked": "Не оценено",
    "good": "Хорошее состояние",
    "minor_issues": "Есть небольшие замечания",
    "repairs_needed": "Требуется ремонт",
    "critical": "Серьёзные недостатки",
}

DATA_DIR = Path.home() / ".territoria_svoih"
DATA_FILE = DATA_DIR / "inspections.json"


class InspectionDialog(QDialog):
    def __init__(self, token, properties, parent=None, data=None):
        super().__init__(parent)

        self.token = token
        self.properties = properties
        self.data = dict(data or {})
        self.result_data = None

        self.property_by_id = {
            str(item.get("id")): item
            for item in properties
        }

        self.setWindowTitle(
            "Редактирование инспекции"
            if data else "Новая инспекция"
        )
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(15)

        form = QFormLayout()
        form.setSpacing(11)

        self.property_input = QComboBox()
        self.property_input.setMinimumHeight(36)

        for prop in properties:
            self.property_input.addItem(
                f'{prop.get("title", "Объект")} — '
                f'{prop.get("address", "")}',
                prop.get("id"),
            )

        property_index = self.property_input.findData(
            self.data.get("propertyId")
        )

        if property_index < 0 and self.data.get("propertyId") is not None:
            property_index = next(
                (
                    i for i in range(self.property_input.count())
                    if str(self.property_input.itemData(i))
                    == str(self.data.get("propertyId"))
                ),
                -1,
            )

        if property_index >= 0:
            self.property_input.setCurrentIndex(property_index)

        self.type_input = QComboBox()
        self.type_input.setMinimumHeight(36)

        for code, label in INSPECTION_TYPES.items():
            self.type_input.addItem(label, code)

        type_index = self.type_input.findData(
            self.data.get("inspectionType", "initial")
        )
        self.type_input.setCurrentIndex(max(type_index, 0))

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        self.date_input.setMinimumHeight(36)

        date_value = QDate.fromString(
            self.data.get("date", ""),
            "yyyy-MM-dd",
        )

        self.date_input.setDate(
            date_value if date_value.isValid()
            else QDate.currentDate()
        )

        self.time_input = QTimeEdit()
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setMinimumHeight(36)

        time_value = QTime.fromString(
            self.data.get("time", ""),
            "HH:mm",
        )

        self.time_input.setTime(
            time_value if time_value.isValid()
            else QTime(12, 0)
        )

        self.inspector_input = QLineEdit(
            str(self.data.get("inspector", ""))
        )
        self.inspector_input.setMinimumHeight(36)
        self.inspector_input.setPlaceholderText(
            "ФИО ответственного сотрудника"
        )

        self.condition_input = QComboBox()
        self.condition_input.setMinimumHeight(36)

        for code, label in CONDITION_LABELS.items():
            self.condition_input.addItem(label, code)

        condition_index = self.condition_input.findData(
            self.data.get("condition", "not_checked")
        )
        self.condition_input.setCurrentIndex(max(condition_index, 0))

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(110)
        self.notes_input.setPlaceholderText(
            "Состояние объекта, обнаруженные дефекты и рекомендации"
        )
        self.notes_input.setPlainText(
            str(self.data.get("notes", ""))
        )

        form.addRow("Объект недвижимости:", self.property_input)
        form.addRow("Тип инспекции:", self.type_input)
        form.addRow("Дата:", self.date_input)
        form.addRow("Время:", self.time_input)
        form.addRow("Ответственный:", self.inspector_input)
        form.addRow("Состояние объекта:", self.condition_input)
        form.addRow("Результат и замечания:", self.notes_input)

        root.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Отмена")
        cancel_button.setObjectName("secondary")
        cancel_button.setMinimumHeight(38)
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        save_button = QPushButton("Сохранить")
        save_button.setObjectName("primary")
        save_button.setMinimumHeight(38)
        save_button.setCursor(Qt.PointingHandCursor)
        save_button.clicked.connect(self.save)

        buttons.addWidget(cancel_button)
        buttons.addWidget(save_button)

        root.addLayout(buttons)

    def save(self):
        property_id = self.property_input.currentData()

        if property_id is None:
            QMessageBox.warning(
                self,
                "Не выбран объект",
                "Добавьте объект недвижимости в разделе «Объекты».",
            )
            return

        inspector = self.inspector_input.text().strip()

        if not inspector:
            QMessageBox.warning(
                self,
                "Не указан ответственный",
                "Укажите сотрудника, который проведёт инспекцию.",
            )
            self.inspector_input.setFocus()
            return

        prop = self.property_by_id.get(
            str(property_id),
            {},
        )

        self.result_data = {
            "propertyId": property_id,
            "propertyTitle": prop.get(
                "title",
                self.data.get("propertyTitle", "Объект"),
            ),
            "propertyAddress": prop.get(
                "address",
                self.data.get("propertyAddress", ""),
            ),
            "inspectionType": self.type_input.currentData(),
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "time": self.time_input.time().toString("HH:mm"),
            "inspector": inspector,
            "condition": self.condition_input.currentData(),
            "notes": self.notes_input.toPlainText().strip(),
            "status": self.data.get("status", "planned"),
            "createdAt": self.data.get("createdAt", ""),
        }

        self.accept()


class InspectionsPage(QWidget):
    def __init__(self, token, parent=None):
        super().__init__(parent)

        self.token = token
        self.properties = []
        self.inspections = []

        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(18)

        header = QHBoxLayout()
        titles = QVBoxLayout()

        title = QLabel("Инспекции недвижимости")
        title.setObjectName("page_title")
        title.setStyleSheet(
            "font-size: 26px; font-weight: 600; "
            "color: #24352c;"
        )

        subtitle = QLabel(
            "Планирование осмотров объектов и фиксация "
            "их технического состояния"
        )
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet(
            "font-size: 13px; color: #7b877f;"
        )

        titles.addWidget(title)
        titles.addWidget(subtitle)

        header.addLayout(titles)
        header.addStretch()

        self.add_button = QPushButton("+ Добавить инспекцию")
        self.add_button.setObjectName("primary")
        self.add_button.setMinimumHeight(40)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(
            lambda checked=False: self.add_inspection()
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
            "Поиск по объекту, адресу или ответственному..."
        )
        self.search_input.textChanged.connect(self.fill_table)

        self.status_filter = QComboBox()
        self.status_filter.setMinimumHeight(38)
        self.status_filter.addItem("Все статусы", "all")

        for code, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, code)

        self.status_filter.currentIndexChanged.connect(
            self.fill_table
        )

        filters.addWidget(self.search_input, 3)
        filters.addWidget(self.status_filter, 1)

        root.addLayout(filters)

        panel = QFrame()
        panel.setObjectName("panel")

        inside = QVBoxLayout(panel)
        inside.setContentsMargins(18, 18, 18, 18)
        inside.setSpacing(14)

        toolbar = QHBoxLayout()

        self.count_label = QLabel("Инспекций: 0")
        self.count_label.setObjectName("section_title")
        self.count_label.setStyleSheet(
            "font-size: 16px; font-weight: 600; "
            "color: #24352c;"
        )

        toolbar.addWidget(self.count_label)
        toolbar.addStretch()

        self.view_button = QPushButton("Просмотреть")
        self.edit_button = QPushButton("Редактировать")
        self.complete_button = QPushButton("Отметить проверенной")
        self.cancel_button = QPushButton("Отменить")
        self.refresh_button = QPushButton("Обновить")

        for button in (
            self.view_button,
            self.edit_button,
            self.complete_button,
            self.cancel_button,
            self.refresh_button,
        ):
            button.setObjectName("secondary")
            button.setMinimumHeight(38)
            button.setCursor(Qt.PointingHandCursor)
            toolbar.addWidget(button)

        # Явно передаём действия кнопок без аргумента checked.
        self.view_button.clicked.connect(
            lambda checked=False: self.view_inspection()
        )
        self.edit_button.clicked.connect(
            lambda checked=False: self.edit_inspection()
        )
        self.complete_button.clicked.connect(
            lambda checked=False: self.complete_inspection()
        )
        self.cancel_button.clicked.connect(
            lambda checked=False: self.cancel_inspection()
        )
        self.refresh_button.clicked.connect(
            lambda checked=False: self.refresh_data()
        )

        inside.addLayout(toolbar)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Дата",
            "Время",
            "Объект",
            "Адрес",
            "Тип инспекции",
            "Ответственный",
            "Статус",
        ])

        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)

        header_view = self.table.horizontalHeader()

        for column in (1, 2, 5, 7):
            header_view.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        for column in (0, 3, 4, 6):
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
            lambda row, column: self.view_inspection()
        )

        inside.addWidget(self.table)
        root.addWidget(panel, 1)

        self.update_action_buttons()

    def select_table_row(self, row, column=0):
        if 0 <= row < self.table.rowCount():
            visible_column = column if column > 0 else 1
            self.table.setCurrentCell(row, visible_column)
            self.table.selectRow(row)

        self.update_action_buttons()

    def load_inspections(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            if not DATA_FILE.exists():
                DATA_FILE.write_text("[]", encoding="utf-8")

            loaded = json.loads(
                DATA_FILE.read_text(encoding="utf-8")
            )

            self.inspections = (
                [item for item in loaded if isinstance(item, dict)]
                if isinstance(loaded, list)
                else []
            )

            changed = False

            used_ids = {
                str(item.get("id"))
                for item in self.inspections
                if item.get("id") not in (None, "")
            }

            next_id = max(
                (
                    int(item.get("id"))
                    for item in self.inspections
                    if str(item.get("id", "")).isdigit()
                ),
                default=0,
            ) + 1

            for item in self.inspections:
                if item.get("id") in (None, ""):
                    while str(next_id) in used_ids:
                        next_id += 1

                    item["id"] = next_id
                    used_ids.add(str(next_id))
                    next_id += 1
                    changed = True

                if not item.get("status"):
                    item["status"] = "planned"
                    changed = True

                item.setdefault("propertyTitle", "Объект")
                item.setdefault("propertyAddress", "")
                item.setdefault("inspectionType", "initial")
                item.setdefault(
                    "date",
                    QDate.currentDate().toString("yyyy-MM-dd"),
                )
                item.setdefault("time", "12:00")
                item.setdefault("inspector", "")
                item.setdefault("condition", "not_checked")
                item.setdefault("notes", "")

            if changed:
                self.save_inspections()

        except (OSError, json.JSONDecodeError) as error:
            self.inspections = []
            QMessageBox.warning(
                self,
                "Не удалось загрузить инспекции",
                str(error),
            )

    def save_inspections(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)

            temporary_file = DATA_FILE.with_suffix(".tmp")
            temporary_file.write_text(
                json.dumps(
                    self.inspections,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            temporary_file.replace(DATA_FILE)

            return True

        except OSError as error:
            QMessageBox.critical(
                self,
                "Не удалось сохранить инспекции",
                str(error),
            )
            return False

    def refresh_data(self, *_):
        if self.token:
            try:
                self.properties = (
                    service.getProperties(self.token) or []
                )
            except Exception as error:
                self.properties = []

                QMessageBox.warning(
                    self,
                    "Не удалось загрузить объекты",
                    "Для инспекций нужен доступ к разделу «Объекты»."
                    "\n\n" + str(error),
                )
        else:
            self.properties = []

        self.load_inspections()
        self.fill_table()

    def fill_table(self, *_args, selected_id=None):
        if selected_id is None:
            selected_id = self.selected_inspection_id(
                show_message=False
            )

        needle = self.search_input.text().strip().casefold()
        selected_status = self.status_filter.currentData()
        rows = []

        for inspection in self.inspections:
            searchable = " ".join([
                str(inspection.get("propertyTitle", "")),
                str(inspection.get("propertyAddress", "")),
                str(inspection.get("inspector", "")),
                str(inspection.get("notes", "")),
            ]).casefold()

            if needle and needle not in searchable:
                continue

            if (
                selected_status != "all"
                and inspection.get("status") != selected_status
            ):
                continue

            rows.append(inspection)

        rows.sort(
            key=lambda item: (
                str(item.get("date", "")),
                str(item.get("time", "")),
            ),
            reverse=True,
        )

        self.table.setRowCount(0)

        for row, inspection in enumerate(rows):
            self.table.insertRow(row)

            date_text = str(inspection.get("date", ""))
            parsed_date = QDate.fromString(
                date_text,
                "yyyy-MM-dd",
            )

            if parsed_date.isValid():
                date_text = parsed_date.toString("dd.MM.yyyy")

            values = [
                inspection.get("id", ""),
                date_text or "—",
                inspection.get("time", "—"),
                inspection.get("propertyTitle", "Объект"),
                inspection.get("propertyAddress", "—"),
                INSPECTION_TYPES.get(
                    inspection.get("inspectionType"),
                    inspection.get("inspectionType", "—"),
                ),
                inspection.get("inspector", "—"),
                STATUS_LABELS.get(
                    inspection.get("status"),
                    inspection.get("status", "—"),
                ),
            ]

            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setFlags(
                    cell.flags() & ~Qt.ItemIsEditable
                )

                if column in (0, 1, 2, 5, 7):
                    cell.setTextAlignment(Qt.AlignCenter)

                if column == 0:
                    cell.setData(
                        Qt.UserRole,
                        str(inspection.get("id", "")),
                    )

                if column == 7:
                    if inspection.get("status") == "completed":
                        cell.setForeground(
                            QBrush(QColor("#2f7650"))
                        )
                    elif inspection.get("status") == "cancelled":
                        cell.setForeground(
                            QBrush(QColor("#9a6666"))
                        )

                self.table.setItem(row, column, cell)

            self.table.setRowHeight(row, 44)

        self.count_label.setText(
            f"Найдено инспекций: {len(rows)}"
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

    def selected_inspection_id(self, show_message=True):
        row = -1

        selection = self.table.selectionModel().selectedRows()

        if selection:
            row = selection[0].row()

        if row < 0:
            row = self.table.currentRow()

        if row < 0 and self.table.selectedRanges():
            row = self.table.selectedRanges()[0].topRow()

        if row < 0 or self.table.item(row, 0) is None:
            if show_message:
                QMessageBox.information(
                    self,
                    "Инспекция не выбрана",
                    "Сначала выберите инспекцию в таблице.",
                )
            return None

        cell = self.table.item(row, 0)
        inspection_id = cell.data(Qt.UserRole)

        if inspection_id in (None, ""):
            inspection_id = cell.text()

        if inspection_id in (None, ""):
            if show_message:
                QMessageBox.warning(
                    self,
                    "Не удалось определить инспекцию",
                    "Обновите список и выберите строку ещё раз.",
                )
            return None

        return str(inspection_id)

    def selected_inspection(self, show_message=True):
        inspection_id = self.selected_inspection_id(
            show_message
        )

        if inspection_id is None:
            return None

        for inspection in self.inspections:
            if str(inspection.get("id")) == inspection_id:
                return inspection

        if show_message:
            QMessageBox.warning(
                self,
                "Инспекция не найдена",
                "Обновите список и выберите инспекцию ещё раз.",
            )

        return None

    def update_action_buttons(self):
        # Кнопки активны после входа. При отсутствии выбора
        # обработчики выводят сообщение вместо молчаливого отказа.
        logged_in = bool(self.token)

        self.view_button.setEnabled(logged_in)
        self.edit_button.setEnabled(logged_in)
        self.complete_button.setEnabled(logged_in)
        self.cancel_button.setEnabled(logged_in)
        self.add_button.setEnabled(logged_in)
        self.refresh_button.setEnabled(True)

    def add_inspection(self):
        if not self.token:
            QMessageBox.warning(
                self,
                "Не выполнен вход",
                "Войдите в систему, чтобы добавить инспекцию.",
            )
            return

        if not self.properties:
            QMessageBox.warning(
                self,
                "Нет доступных объектов",
                "Сначала добавьте объект в разделе «Объекты» "
                "и убедитесь, что у вас есть к нему доступ.",
            )
            return

        dialog = InspectionDialog(
            self.token,
            self.properties,
            self,
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        next_id = max(
            (
                int(item.get("id", 0))
                for item in self.inspections
                if str(item.get("id", "")).isdigit()
            ),
            default=0,
        ) + 1

        record = dict(dialog.result_data)
        record["id"] = next_id
        record["createdAt"] = (
            QDate.currentDate().toString("yyyy-MM-dd")
        )

        self.inspections.append(record)

        if self.save_inspections():
            self.fill_table(selected_id=next_id)

    def edit_inspection(self):
        inspection = self.selected_inspection()

        if not inspection:
            return

        if inspection.get("status", "planned") != "planned":
            QMessageBox.information(
                self,
                "Редактирование недоступно",
                "Редактировать можно только запланированные инспекции.",
            )
            return

        if not self.properties:
            QMessageBox.warning(
                self,
                "Нет объектов",
                "Не удалось загрузить список объектов.",
            )
            return

        old_record = dict(inspection)

        dialog = InspectionDialog(
            self.token,
            self.properties,
            self,
            data=old_record,
        )

        if dialog.exec_() != QDialog.Accepted:
            return

        inspection.update(dialog.result_data)

        if self.save_inspections():
            self.fill_table(
                selected_id=inspection.get("id")
            )
        else:
            inspection.clear()
            inspection.update(old_record)

    def view_inspection(self):
        inspection = self.selected_inspection()

        if not inspection:
            return

        date_text = str(inspection.get("date", "—"))
        parsed_date = QDate.fromString(
            date_text,
            "yyyy-MM-dd",
        )

        if parsed_date.isValid():
            date_text = parsed_date.toString("dd.MM.yyyy")

        details = (
            f'Объект: {inspection.get("propertyTitle", "—")}\n'
            f'Адрес: {inspection.get("propertyAddress", "—")}\n'
            f'Тип: {INSPECTION_TYPES.get(inspection.get("inspectionType"), "—")}\n'
            f'Дата и время: {date_text}, {inspection.get("time", "—")}\n'
            f'Ответственный: {inspection.get("inspector", "—")}\n'
            f'Состояние: {CONDITION_LABELS.get(inspection.get("condition"), "Не оценено")}\n'
            f'Статус: {STATUS_LABELS.get(inspection.get("status"), "—")}\n\n'
            f'Результат и замечания:\n{inspection.get("notes") or "Не указаны"}'
        )

        QMessageBox.information(
            self,
            "Информация об инспекции",
            details,
        )

    def change_status(
        self,
        new_status,
        confirmation,
        inspection=None,
    ):
        if inspection is None:
            inspection = self.selected_inspection()

        if not inspection:
            return

        if inspection.get("status", "planned") != "planned":
            QMessageBox.information(
                self,
                "Действие недоступно",
                "Изменить статус можно только у запланированной инспекции.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Подтверждение",
            confirmation,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        previous_status = inspection.get("status", "planned")
        inspection["status"] = new_status

        if self.save_inspections():
            self.fill_table(
                selected_id=inspection.get("id")
            )
        else:
            inspection["status"] = previous_status
            self.update_action_buttons()

    def complete_inspection(self):
        inspection = self.selected_inspection()

        if not inspection:
            return

        self.change_status(
            "completed",
            f'Отметить инспекцию объекта '
            f'«{inspection.get("propertyTitle", "Объект")}» '
            f'как проверенную?',
            inspection=inspection,
        )

    def cancel_inspection(self):
        inspection = self.selected_inspection()

        if not inspection:
            return

        self.change_status(
            "cancelled",
            f'Отменить инспекцию объекта '
            f'«{inspection.get("propertyTitle", "Объект")}»?',
            inspection=inspection,
        )

    def set_token(self, token):
        self.token = token
        self.refresh_data()
