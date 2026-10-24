
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QComboBox,
    QMessageBox,
    QFrame,
)

from gge import service


class AuthWindow(QWidget):

    authenticated = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Территория своих — авторизация")
        self.resize(560, 720)
        self.setMinimumSize(520, 650)
        self.setWindowFlags(
            Qt.Window | Qt.WindowCloseButtonHint
        )

        self.setStyleSheet("""
            QWidget {
                background-color: #F4F6FA;
                color: #22334F;
                font-family: "Segoe UI";
                font-size: 13px;
            }

            QFrame#auth_card {
                background-color: white;
                border: 1px solid #E1E7F0;
                border-radius: 16px;
            }

            QLabel#brand {
                color: #22334F;
                font-size: 23px;
                font-weight: 700;
            }

            QLabel#subtitle {
                color: #78869B;
                font-size: 12px;
            }

            QLabel#form_title {
                font-size: 19px;
                font-weight: 600;
            }

            QLineEdit, QComboBox {
                background-color: white;
                border: 1px solid #D9E1EC;
                border-radius: 8px;
                padding: 9px 12px;
                min-height: 24px;
                font-size: 13px;
            }

            QLabel {
                padding-top: 2px;
            }

            QPushButton#primary {
            min-height: 24px;
            padding: 10px 14px;
            }  

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #557EB8;
            }

            QPushButton#primary {
                background-color: #29466D;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: 600;
            }

            QPushButton#primary:hover {
                background-color: #355987;
            }

            QPushButton#primary:disabled {
                background-color: #AAB7CA;
            }

            QTabWidget::pane {
                border: none;
                background-color: white;
                top: -1px;
            }

            QTabBar::tab {
                background-color: #F0F3F8;
                color: #68768B;
                padding: 10px 18px;
                border-radius: 7px;
                margin-right: 5px;
            }

            QTabBar::tab:selected {
                background-color: #29466D;
                color: white;
            }

            QLabel#hint {
                color: #78869B;
                font-size: 11px;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(30, 25, 30, 25)
        root.setSpacing(12)

        brand = QLabel("ТЕРРИТОРИЯ СВОИХ")
        brand.setObjectName("brand")
        brand.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("КОРПОРАТИВНАЯ СИСТЕМА АГЕНТСТВА")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        root.addWidget(brand)
        root.addWidget(subtitle)
        root.addSpacing(4)

        self.card = QFrame()
        self.card.setObjectName("auth_card")

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(26, 24, 26, 24)
        self.card_layout.setSpacing(12)

        root.addWidget(self.card, 1)

        if service.needsSetup():
            self.build_admin_setup()
        else:
            self.build_auth_tabs()

    def build_auth_tabs(self):

        tabs = QTabWidget()

        login_page = QWidget()
        login_layout = QVBoxLayout(login_page)
        login_layout.setContentsMargins(4, 16, 4, 4)
        login_layout.setSpacing(13)

        login_title = QLabel("Вход в аккаунт")
        login_title.setObjectName("form_title")
        login_layout.addWidget(login_title)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Корпоративный логин")
        self.login_input.setMaxLength(40)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.returnPressed.connect(self.login)

        login_layout.addWidget(QLabel("Логин"))
        login_layout.addWidget(self.login_input)
        login_layout.addWidget(QLabel("Пароль"))
        login_layout.addWidget(self.password_input)

        login_button = QPushButton("Войти")
        login_button.setObjectName("primary")
        login_button.setCursor(Qt.PointingHandCursor)
        login_button.clicked.connect(self.login)

        login_layout.addSpacing(4)
        login_layout.addWidget(login_button)

        login_hint = QLabel(
            "Доступ предоставляется сотрудникам с подтверждённой "
            "учётной записью."
        )
        login_hint.setObjectName("hint")
        login_hint.setWordWrap(True)
        login_layout.addWidget(login_hint)
        login_layout.addStretch()

        register_page = QWidget()
        register_layout = QVBoxLayout(register_page)
        register_layout.setContentsMargins(4, 16, 4, 4)
        register_layout.setSpacing(10)

        register_title = QLabel("Регистрация сотрудника")
        register_title.setObjectName("form_title")
        register_layout.addWidget(register_title)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Фамилия и имя")
        self.name_input.setMaxLength(150)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("+7 900 000-00-00")
        self.phone_input.setMaxLength(20)

        self.register_login_input = QLineEdit()
        self.register_login_input.setPlaceholderText(
            "Латинские буквы, цифры, . _ -"
        )
        self.register_login_input.setMaxLength(40)

        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText(
            "Не менее 8 символов"
        )
        self.register_password_input.setEchoMode(QLineEdit.Password)
        self.register_password_input.setMaxLength(128)

        self.role_input = QComboBox()
        self.role_input.addItem("Агент", "agent")
        self.role_input.addItem("Бухгалтер", "accountant")
        self.role_input.addItem("Юрист", "lawyer")

        for label, widget in [
            ("ФИО", self.name_input),
            ("Телефон", self.phone_input),
            ("Логин", self.register_login_input),
            ("Пароль", self.register_password_input),
            ("Должность", self.role_input),
        ]:
            register_layout.addWidget(QLabel(label))
            register_layout.addWidget(widget)

        register_button = QPushButton("Отправить заявку")
        register_button.setObjectName("primary")
        register_button.setCursor(Qt.PointingHandCursor)
        register_button.clicked.connect(self.register)

        register_layout.addWidget(register_button)

        register_hint = QLabel(
            "После регистрации администратор должен подтвердить "
            "доступ к системе."
        )
        register_hint.setObjectName("hint")
        register_hint.setWordWrap(True)
        register_layout.addWidget(register_hint)
        register_layout.addStretch()

        tabs.addTab(login_page, "Вход")
        tabs.addTab(register_page, "Регистрация")

        self.card_layout.addWidget(tabs)

    def build_admin_setup(self):

        title = QLabel("Первичная настройка")
        title.setObjectName("form_title")

        description = QLabel(
            "Учётных записей пока нет. Создай администратора "
            "агентства — он сможет управлять доступом сотрудников."
        )
        description.setWordWrap(True)
        description.setObjectName("subtitle")

        self.setup_name = QLineEdit()
        self.setup_name.setPlaceholderText("ФИО администратора")

        self.setup_phone = QLineEdit()
        self.setup_phone.setPlaceholderText("Контактный телефон")

        self.setup_login = QLineEdit()
        self.setup_login.setPlaceholderText("Логин")

        self.setup_password = QLineEdit()
        self.setup_password.setPlaceholderText(
            "Пароль (не менее 8 символов)"
        )
        self.setup_password.setEchoMode(QLineEdit.Password)

        self.setup_password_confirm = QLineEdit()
        self.setup_password_confirm.setPlaceholderText(
            "Повтори пароль"
        )
        self.setup_password_confirm.setEchoMode(QLineEdit.Password)

        self.card_layout.addWidget(title)
        self.card_layout.addWidget(description)

        for label, widget in [
            ("ФИО", self.setup_name),
            ("Телефон", self.setup_phone),
            ("Логин", self.setup_login),
            ("Пароль", self.setup_password),
            ("Повтор пароля", self.setup_password_confirm),
        ]:
            self.card_layout.addWidget(QLabel(label))
            self.card_layout.addWidget(widget)

        create_button = QPushButton("Создать администратора")
        create_button.setObjectName("primary")
        create_button.setCursor(Qt.PointingHandCursor)
        create_button.clicked.connect(self.create_admin)

        self.card_layout.addSpacing(8)
        self.card_layout.addWidget(create_button)
        self.card_layout.addStretch()

    def login(self):

        login = self.login_input.text().strip()
        password = self.password_input.text()

        try:
            token = service.login(login, password)
            profile = service.getProfile(token)
            self.authenticated.emit(token, profile)

        except Exception as error:
            QMessageBox.warning(
                self,
                "Не удалось войти",
                str(error),
            )
            self.password_input.clear()
            self.password_input.setFocus()

    def register(self):

        full_name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        login = self.register_login_input.text().strip()
        password = self.register_password_input.text()
        role = self.role_input.currentData()

        try:
            user_id = service.registerUser(
                full_name,
                phone,
                login,
                password,
                role,
            )

            QMessageBox.information(
                self,
                "Заявка отправлена",
                f"Заявка №{user_id} создана.\n\n"
                "Теперь дождись подтверждения администратора. "
                "До подтверждения войти в систему не получится.",
            )

            self.name_input.clear()
            self.phone_input.clear()
            self.register_login_input.clear()
            self.register_password_input.clear()

        except Exception as error:
            QMessageBox.warning(
                self,
                "Ошибка регистрации",
                str(error),
            )

    def create_admin(self):
        print("1. Начинаем создание администратора")

        full_name = self.setup_name.text().strip()
        phone = self.setup_phone.text().strip()
        login = self.setup_login.text().strip()
        password = self.setup_password.text()
        confirmation = self.setup_password_confirm.text()

        if password != confirmation:
            QMessageBox.warning(
                self,
                "Проверь пароль",
                "Пароли не совпадают.",
            )
            return

        try:
            print("2. Вызываем service.createAdmin()")

            token = service.createAdmin(
                full_name,
                phone,
                login,
                password,
            )

            print("3. Администратор создан, получаем профиль")

            profile = service.getProfile(token)

            print("4. Профиль получен:", profile)
            print("5. Отправляем сигнал authenticated")

            self.authenticated.emit(token, profile)

            print("6. Сигнал отправлен")

        except Exception as error:
            print("ОШИБКА:", repr(error))

            QMessageBox.warning(
                self,
                "Не удалось создать администратора",
                str(error),
            )

