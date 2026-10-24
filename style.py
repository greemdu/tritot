COLORS = {
    "navy": "#17243A",
    "navy_light": "#22334F",
    "gold": "#C8A96B",
    "background": "#F4F6FA",
    "white": "#FFFFFF",
    "text": "#243247",
    "muted": "#8994A6",
    "border": "#E7EBF2",
    "green": "#1D9563",
}


APP_STYLE = """
QMainWindow, QWidget#central {
    background-color: #F4F6FA;
}

QWidget {
    font-family: "Segoe UI";
    font-size: 13px;
    color: #243247;
}

QFrame#sidebar {
    background-color: #17243A;
    border: none;
}

QLabel#brand {
    color: #FFFFFF;
    font-size: 19px;
    font-weight: 700;
}

QLabel#brand_subtitle {
    color: #C8A96B;
    font-size: 10px;
    letter-spacing: 2px;
}

QLabel#menu_label {
    color: #718099;
    font-size: 10px;
    font-weight: 600;
    padding: 5px;
}

QPushButton#nav_button {
    background-color: transparent;
    color: #B7C1D1;
    border: none;
    border-radius: 9px;
    text-align: left;
    padding: 13px 15px;
    font-size: 13px;
}

QPushButton#nav_button:hover {
    background-color: #22334F;
    color: #FFFFFF;
}

QPushButton#nav_button[active="true"] {
    background-color: #2C3D58;
    color: #FFFFFF;
    border-left: 3px solid #C8A96B;
    font-weight: 600;
}

QLabel#page_title {
    font-size: 26px;
    font-weight: 700;
    color: #17243A;
}

QLabel#muted {
    color: #8994A6;
    font-size: 12px;
}

QLabel#section_title {
    color: #17243A;
    font-size: 16px;
    font-weight: 700;
}

QLineEdit#search {
    background-color: #FFFFFF;
    border: 1px solid #E7EBF2;
    border-radius: 10px;
    padding: 11px 15px;
    color: #243247;
    min-width: 210px;
}

QLineEdit#search:focus {
    border: 1px solid #C8A96B;
}

QFrame#stat_card, QFrame#panel {
    background-color: #FFFFFF;
    border: 1px solid #E7EBF2;
    border-radius: 14px;
}

QLabel#stat_label {
    color: #8994A6;
    font-size: 12px;
}

QLabel#stat_value {
    color: #17243A;
    font-size: 29px;
    font-weight: 700;
}



QPushButton#primary {
    background-color: #17243A;
    color: #FFFFFF;
    border: none;
    border-radius: 9px;
    padding: 11px 17px;
    font-weight: 600;
}

QPushButton#primary:hover {
    background-color: #2C3D58;
}

QPushButton#secondary {
    background-color: #F8F3E9;
    color: #8D703C;
    border: none;
    border-radius: 8px;
    padding: 9px 13px;
    font-weight: 600;
}

QPushButton#secondary:hover {
    background-color: #EFE4CD;
}

QTableWidget {
    background-color: #FFFFFF;
    border: none;
    gridline-color: #F0F2F6;
    selection-background-color: #EEF2F8;
    selection-color: #17243A;
    outline: none;
}

QHeaderView::section {
    background-color: #FFFFFF;
    color: #8994A6;
    border: none;
    border-bottom: 1px solid #E7EBF2;
    padding: 13px 8px;
    font-size: 11px;
    font-weight: 600;
}

QTableWidget::item {
    padding: 10px 6px;
    border-bottom: 1px solid #F0F2F6;
}

QScrollBar:vertical {
    background: #F4F6FA;
    width: 7px;
    border: none;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #D3D9E3;
    border-radius: 3px;
    min-height: 30px;
}


"""