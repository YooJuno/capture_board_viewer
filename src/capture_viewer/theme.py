STYLE = """
QMainWindow, QWidget#root { background: #101318; color: #e5e9ef; }
QWidget { color: #e5e9ef; font-size: 13px; }
QWidget#header { background: #161a21; border-bottom: 1px solid #272d37; }
QWidget#sidebar { background: #161a21; border-left: 1px solid #272d37; }
QWidget#footer { background: #161a21; border-top: 1px solid #272d37; }
QLabel#brand { font-size: 18px; font-weight: 600; }
QLabel#eyebrow { color: #758291; font-size: 10px; font-weight: 600; }
QLabel#section { color: #eef1f5; font-weight: 600; font-size: 14px; }
QLabel#muted { color: #8b97a7; }
QLabel#emptyTitle { color: #d3dbe6; font-size: 20px; font-weight: 500; }
QLabel#emptyText { color: #7b8899; font-size: 13px; }
QLabel#status { color: #9aa8b8; font-weight: 500; }
QPushButton, QToolButton {
 background: #222934; border: 1px solid #303b49; border-radius: 6px;
 padding: 8px 12px; color: #d7e0eb;
}
QPushButton:hover, QToolButton:hover { background: #2b3543; border-color: #4b5b6b; }
QPushButton:pressed, QToolButton:pressed { background: #344252; }
QPushButton:focus, QToolButton:focus, QComboBox:focus { border: 1px solid #81d5bd; }
QPushButton:disabled, QToolButton:disabled { color: #596574; border-color: #29313c; }
QPushButton#connect { background: #81d5bd; color: #10251e; border: 0; font-weight: 600; padding: 11px; }
QPushButton#connect:hover { background: #9ae6d0; }
QPushButton#connect:disabled { background: #2b403c; color: #708b81; }
QPushButton#disconnect { background: #27323c; color: #dce5ef; padding: 11px; }
QComboBox {
 background: #10151c; border: 1px solid #303b49; border-radius: 6px;
 padding: 9px 10px; min-height: 18px;
}
QComboBox:disabled { color: #657182; }
QComboBox QAbstractItemView { background: #202935; selection-background-color: #36534d; border: 1px solid #394657; }
QCheckBox { spacing: 9px; color: #acb8c6; padding: 4px 0; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #4a5768; border-radius: 3px; background: #10151c; }
QCheckBox::indicator:checked { background: #81d5bd; border-color: #81d5bd; }
QToolTip { background: #273340; color: #f0f4f8; border: 1px solid #4c5b6e; padding: 5px; }
QMessageBox, QFileDialog { background: #161a21; }
"""
