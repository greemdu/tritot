import os
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = r"C:/Users/диджей арбуз/PycharmProject/territoria/.venv/Lib/site-packages/PyQt5/Qt5/plugins"
import sys
import faulthandler
faulthandler.enable()
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QLabel,
    QPushButton,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QStackedWidget,
    QToolButton,
    QMenu,
    QMessageBox
)

from gge import service
from style import APP_STYLE
from pages.clients import ClientsPage
from pages.auth import AuthWindow
from pages.properties import PropertiesPage
from gge.database import initDb
from pages.deals import DealsPage
from pages.showings import ShowingsPage
from pages.inspections import InspectionsPage
from pages.documents import DocumentsPage
from pages.reports import ReportsPage
from pages.references import ReferencesPage


class StatCard(QFrame):
    def __init__(self, title, value, description):
        super().__init__()

        self.setObjectName("stat_card")
        self.setMinimumHeight(145)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        label = QLabel(title)
        label.setObjectName("stat_label")

        number = QLabel(value)
        number.setObjectName("stat_value")

        subtitle = QLabel(description)
        subtitle.setObjectName("muted")

        layout.addWidget(label)
        layout.addWidget(number)
        layout.addWidget(subtitle)
        layout.addStretch()



class Dashboard(QWidget):
    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 25, 28, 25)
        root.setSpacing(23)

        # Заголовок
        header = QHBoxLayout()

        titles = QVBoxLayout()
        titles.setSpacing(5)

        title = QLabel("Добро пожаловать!")
        title.setObjectName("page_title")

        subtitle = QLabel(
            "Вот что происходит в вашем агентстве сегодня."
        )
        subtitle.setObjectName("muted")

        titles.addWidget(title)
        titles.addWidget(subtitle)

        # Поиск по сделкам
        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText(
            "Поиск по сделкам..."
        )
        self.search.setClearButtonEnabled(True)

        # Кнопка новой сделки
        add_button = QPushButton("+ Новая сделка")
        add_button.setObjectName("primary")
        add_button.setCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self.new_deal)

        header.addLayout(titles)
        header.addStretch()
        header.addWidget(self.search)
        header.addWidget(add_button)

        root.addLayout(header)

        # Карточки статистики
        self.stats_layout = QGridLayout()
        self.stats_layout.setSpacing(16)

        cards = [
            (
                "Активные объекты",
                "128",
                "Недвижимость в базе",
            ),
            (
                "Клиенты",
                "356",
                "Всего в CRM",
            ),
            (
                "Сделки в работе",
                "24",
                "Требуют внимания",
            ),
            (
                "Продажи за месяц",
                "18,6 млн ₽",
                "Объём за текущий месяц",
            ),
        ]

        self.stat_cards = [
            StatCard(*data) for data in cards
        ]

        self.update_stats_layout()
        root.addLayout(self.stats_layout)

        # Панель последних сделок
        panel = QFrame()
        panel.setObjectName("panel")

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(16)

        panel_header = QHBoxLayout()

        section_title = QLabel("Последние сделки")
        section_title.setObjectName("section_title")

        view_all = QPushButton("Все сделки →")
        view_all.setObjectName("secondary")
        view_all.setCursor(Qt.PointingHandCursor)
        view_all.clicked.connect(
            lambda: self.search.setFocus()
        )

        panel_header.addWidget(section_title)
        panel_header.addStretch()
        panel_header.addWidget(view_all)

        panel_layout.addLayout(panel_header)

        # Таблица демонстрационных сделок
        self.table = QTableWidget(0, 5)

        self.table.setHorizontalHeaderLabels([
            "КЛИЕНТ",
            "ОБЪЕКТ",
            "СТОИМОСТЬ",
            "МЕНЕДЖЕР",
            "СТАТУС",
        ])

        rows = [
            (
                "Анна Смирнова",
                "Квартира · Центр",
                "12 500 000 ₽",
                "Иван Петров",
                "Переговоры",
            ),
            (
                "Дмитрий Волков",
                "Дом · Пригород",
                "18 900 000 ₽",
                "Мария Иванова",
                "Одобрено",
            ),
            (
                "Елена Козлова",
                "Студия · Север",
                "6 200 000 ₽",
                "Иван Петров",
                "Новая",
            ),
            (
                "Сергей Орлов",
                "Квартира · Центр",
                "9 800 000 ₽",
                "Анна Соколова",
                "Документы",
            ),
            (
                "Ольга Морозова",
                "Дом · Запад",
                "22 000 000 ₽",
                "Мария Иванова",
                "Переговоры",
            ),
        ]

        self.table.setRowCount(len(rows))

        for row_index, row_data in enumerate(rows):
            for col_index, value in enumerate(row_data):
                item = QTableWidgetItem(value)

                item.setTextAlignment(
                    Qt.AlignVCenter | Qt.AlignLeft
                )

                if col_index == 4:
                    if value == "Одобрено":
                        item.setForeground(Qt.darkGreen)
                    elif value == "Новая":
                        item.setForeground(Qt.darkBlue)

                self.table.setItem(
                    row_index,
                    col_index,
                    item,
                )

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
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
        self.table.setMinimumHeight(300)

        panel_layout.addWidget(self.table)
        root.addWidget(panel, 1)

        # Поиск по таблице
        self.search.textChanged.connect(self.filter_table)

    def update_stats_layout(self):
        width = self.width()

        if width >= 1100:
            columns = 4
        elif width >= 650:
            columns = 2
        else:
            columns = 1

        for card in self.stat_cards:
            self.stats_layout.removeWidget(card)

        for index, card in enumerate(self.stat_cards):
            row = index // columns
            column = index % columns

            self.stats_layout.addWidget(
                card,
                row,
                column,
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_stats_layout()

    def filter_table(self, text):
        text = text.strip().casefold()

        for row in range(self.table.rowCount()):
            matches = any(
                text in (
                    self.table.item(row, column).text().casefold()
                    if self.table.item(row, column)
                    else ""
                )
                for column in range(self.table.columnCount())
            )

            self.table.setRowHidden(
                row,
                not matches,
            )

    def new_deal(self):
        self.search.clear()
        self.search.setFocus()



class RealEstateApp(QMainWindow):
    def __init__(self, token, profile, auth_window=None):
        super().__init__()

        self.token = token
        self.profile_data = profile
        self.auth_window = auth_window

        self.setWindowTitle("Территория своих")
        self.resize(1440, 900)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(APP_STYLE)

        # Центральный контейнер
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Боковая панель
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(235)

        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(15, 27, 15, 20)
        side_layout.setSpacing(8)

        # Брендинг
        brand = QLabel("ТЕРРИТОРИЯ СВОИХ")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignCenter)

        brand_subtitle = QLabel("REAL MANAGEMENT")
        brand_subtitle.setObjectName("brand_subtitle")
        brand_subtitle.setAlignment(Qt.AlignCenter)

        side_layout.addWidget(brand)
        side_layout.addWidget(brand_subtitle)
        side_layout.addSpacing(30)

        menu_label = QLabel("  ОСНОВНОЕ МЕНЮ")
        menu_label.setObjectName("menu_label")
        side_layout.addWidget(menu_label)

        # Контейнер страниц
        self.pages = QStackedWidget()

        # Главная
        self.dashboard = Dashboard()
        self.pages.addWidget(self.dashboard)

        # Клиенты
        self.clients_page = ClientsPage(token=self.token)
        self.pages.addWidget(self.clients_page)

        # Объекты
        self.properties_page = PropertiesPage(token=self.token)
        self.pages.addWidget(self.properties_page)

        # Показы
        self.deals_page = DealsPage(token=self.token)
        self.pages.addWidget(self.deals_page)

        # Сделки
        self.showings_page = ShowingsPage(token=self.token)
        self.pages.addWidget(self.showings_page)

        # Инспекции
        self.inspections_page = InspectionsPage(token=self.token)
        self.pages.addWidget(self.inspections_page)

        # Документы
        self.documents_page = DocumentsPage(token=self.token)
        self.pages.addWidget(self.documents_page)

        # Отчеты
        self.reports_page = ReportsPage(token=self.token,role=self.profile_data.get("role"))
        self.pages.addWidget(self.reports_page)

        # Справочники
        self.references_page = ReferencesPage(token=self.token,role=self.profile_data.get("role"),)
        self.pages.addWidget(self.references_page)


        # Кнопки навигации
        self.nav_buttons = []

        menu_items = [
            "Главная",
            "Клиенты",
            "Объекты",
            "Показы",
            "Сделки",
            "Инспекции",
            "Документы",
            "Отчеты",
            "Справочники",
        ]

        for name in menu_items:
            button = QPushButton(name)
            button.setObjectName("nav_button")
            button.setProperty(
                "active",
                name == "Главная",
            )
            button.setCursor(Qt.PointingHandCursor)

            button.clicked.connect(
                lambda checked=False, page=name:
                self.navigate(page)
            )

            self.nav_buttons.append((name, button))
            side_layout.addWidget(button)

        side_layout.addStretch()

        # Меню профиля пользователя
        role_names = {
            "admin": "Администратор",
            "agent": "Агент",
            "accountant": "Бухгалтер",
            "lawyer": "Юрист",
        }

        employee_name = self.profile_data.get(
            "fullName", "Сотрудник"
        )

        role_title = role_names.get(
            self.profile_data.get("role"),
            "Сотрудник",
        )

        self.profile_button = QToolButton()
        self.profile_button.setObjectName("profile_button")
        self.profile_button.setText(
            f"◉  {employee_name}\n    {role_title}"
        )
        self.profile_button.setToolButtonStyle(
            Qt.ToolButtonTextOnly
        )
        self.profile_button.setPopupMode(
            QToolButton.InstantPopup
        )
        self.profile_button.setCursor(Qt.PointingHandCursor)
        self.profile_button.setMinimumHeight(74)
        self.profile_button.setStyleSheet("""
            QToolButton#profile_button {
                background-color: #22334F;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px;
                text-align: left;
                font-size: 13px;
                font-weight: 600;
            }

            QToolButton#profile_button:hover {
                background-color: #2B4263;
            }

            QToolButton#profile_button::menu-indicator {
                subcontrol-origin: padding;
                subcontrol-position: right center;
            }
        """)

        self.profile_menu = QMenu(self.profile_button)
        self.profile_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                color: #22334F;
                border: 1px solid #E1E7F0;
                border-radius: 8px;
                padding: 5px;
            }

            QMenu::item {
                padding: 9px 24px;
                border-radius: 5px;
            }

            QMenu::item:selected {
                background-color: #F0F3F8;
                color: #22334F;
            }
        """)

        logout_action = self.profile_menu.addAction(
            "Выйти из аккаунта"
        )
        logout_action.triggered.connect(self.logout)

        self.profile_button.setMenu(self.profile_menu)

        side_layout.addWidget(self.profile_button)

        # Добавляем боковую панель и страницы
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)

        # При запуске открываем главную страницу
        self.pages.setCurrentWidget(self.dashboard)


    def create_placeholder(self, name):
        page = QWidget()

        layout = QVBoxLayout(page)
        layout.setContentsMargins(35, 35, 35, 35)
        layout.setSpacing(15)

        title = QLabel(name)
        title.setObjectName("page_title")

        description = QLabel(
            f"Раздел «{name}». Здесь будут расположены "
            "инструменты для работы сотрудников агентства."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        return page


    def navigate(self, name):

        # Обновляем оформление кнопок меню
        for button_name, button in self.nav_buttons:
            active = button_name == name

            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

        # Открываем выбранную страницу
        if name == "Главная":
            self.pages.setCurrentWidget(self.dashboard)

        elif name == "Клиенты":
            self.pages.setCurrentWidget(self.clients_page)

        elif name == "Объекты":
            self.pages.setCurrentWidget(self.properties_page)

        elif name == "Сделки":
            self.pages.setCurrentWidget(self.deals_page)

        elif name == "Показы":
            self.pages.setCurrentWidget(self.showings_page)

        elif name == "Инспекции":
            self.pages.setCurrentWidget(self.inspections_page)

        elif name == "Документы":
            self.pages.setCurrentWidget(self.documents_page)

        elif name == "Отчеты":
            self.pages.setCurrentWidget(self.reports_page)

        elif name == "Справочники":
            self.pages.setCurrentWidget(self.references_page)

        elif name in self.placeholders:
            self.pages.setCurrentWidget(self.placeholders[name])

    def logout(self):
        answer = QMessageBox.question(
            self,
            "Выход из аккаунта",
            "Вы действительно хотите выйти из аккаунта?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        logout_error = None

        try:
            service.logout(self.token)
        except Exception as error:
            logout_error = error

        self.token = None
        self.close()

        if getattr(self, "auth_window", None) is not None:
            self.auth_window.show()
            self.auth_window.raise_()
            self.auth_window.activateWindow()

            if logout_error is not None:
                QMessageBox.warning(
                    self.auth_window,
                    "Завершение сеанса",
                    "Окно входа открыто, но сервер не подтвердил "
                    "завершение сеанса:\n"
                    f"{logout_error}",
                )
        else:
            QMessageBox.warning(
                None,
                "Ошибка",
                "Окно авторизации не найдено. "
                "Перезапустите приложение.",
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))

    initDb()

    auth_window = AuthWindow()
    main_window = None

    def open_main_window(token, profile):
        global main_window

        main_window = RealEstateApp(
            token,
            profile,
            auth_window=auth_window,
        )

        main_window.show()
        auth_window.hide()

    auth_window.authenticated.connect(
        open_main_window
    )

    auth_window.show()

    sys.exit(app.exec_())