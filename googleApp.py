#!/usr/bin/env python3

import os
import re
import sys
import shlex
import shutil
import subprocess
from urllib.parse import urlsplit

import requests

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
    QLineEdit,
    QComboBox,
    QScrollArea,
    QMessageBox,
    QGroupBox,
    QGridLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QFont,
    QIcon,
    QPixmap,
    QPainter,
    QColor,
    QBrush,
    QLinearGradient,
)


DEFAULT_GOOGLE_APPS = [
    {
        "name": "Google Calendar",
        "slug": "google-calendar",
        "url": "https://calendar.google.com",
        "categories": "Office;Calendar;Network;WebBrowser;",
        "keywords": "Google;Calendar;Schedule;Appointment;Agenda;Planner;Web;",
    },
    {
        "name": "Google Gmail",
        "slug": "google-gmail",
        "url": "https://mail.google.com",
        "categories": "Office;Email;Network;WebBrowser;",
        "keywords": "Google;Gmail;Email;Mail;Inbox;Web;",
    },
    {
        "name": "Google Drive",
        "slug": "google-drive",
        "url": "https://drive.google.com",
        "categories": "Office;Network;WebBrowser;FileTransfer;",
        "keywords": "Google;Drive;Cloud;Files;Storage;Docs;Web;",
    },
    {
        "name": "Google Keep",
        "slug": "google-keep",
        "url": "https://keep.google.com",
        "categories": "Utility;Office;Network;WebBrowser;",
        "keywords": "Google;Keep;Notes;Todo;Checklist;Lists;Web;",
    },
    {
        "name": "YouTube",
        "slug": "youtube",
        "url": "https://youtube.com",
        "categories": "AudioVideo;Video;Network;WebBrowser;",
        "keywords": "Google;YouTube;Video;Watch;Stream;Media;",
    },
    {
        "name": "YouTube Music",
        "slug": "youtube-music",
        "url": "https://music.youtube.com",
        "categories": "AudioVideo;Audio;Music;Network;WebBrowser;",
        "keywords": "Google;YouTube;Music;Songs;Audio;Streaming;Playlist;",
    },
    {
        "name": "Gemini",
        "slug": "gemini",
        "url": "https://gemini.google.com",
        "categories": "Utility;Network;WebBrowser;",
        "keywords": "Google;Gemini;AI;Assistant;Chatbot;LLM;Web;",
    },
    {
        "name": "Google Chat",
        "slug": "google-chat",
        "url": "https://chat.google.com",
        "categories": "Network;Chat;InstantMessaging;WebBrowser;",
        "keywords": "Google;Chat;Messaging;Team;Hangouts;Web;",
    },
    {
        "name": "Google Photos",
        "slug": "google-photos",
        "url": "https://photos.google.com",
        "categories": "Graphics;Photography;Network;WebBrowser;",
        "keywords": "Google;Photos;Pictures;Gallery;Albums;Images;Cloud;",
    },
    {
        "name": "Google Maps",
        "slug": "google-maps",
        "url": "https://maps.google.com",
        "categories": "Utility;Geography;Maps;Network;WebBrowser;",
        "keywords": "Google;Maps;Navigation;Directions;GPS;Traffic;Location;",
    },
    {
        "name": "Google Docs",
        "slug": "google-docs",
        "url": "https://docs.google.com",
        "categories": "Office;WordProcessor;Network;WebBrowser;",
        "keywords": "Google;Docs;Documents;Word;Editor;Writing;Office;",
    },
    {
        "name": "Google Sheets",
        "slug": "google-sheets",
        "url": "https://sheets.google.com",
        "categories": "Office;Spreadsheet;Network;WebBrowser;",
        "keywords": "Google;Sheets;Spreadsheet;Excel;Tables;Data;Office;",
    },
]

CATEGORY_MAP = {
    "Internet": "Network;WebBrowser;",
    "Office": "Office;Network;WebBrowser;",
    "Multimedia": "AudioVideo;Network;WebBrowser;",
    "Utilities": "Utility;Network;WebBrowser;",
    "Graphics": "Graphics;Network;WebBrowser;",
    "Development": "Development;Network;WebBrowser;",
}

KNOWN_SYSTEM_ICON_ALIASES = {
    "google-calendar": ["google-calendar", "calendar", "korganizer"],
    "google-gmail": ["google-gmail", "mail-client", "internet-mail", "email"],
    "google-drive": ["google-drive", "folder-google-drive", "drive-harddisk"],
    "google-keep": ["google-keep", "notes", "accessories-text-editor"],
    "youtube": ["youtube", "video-player"],
    "youtube-music": ["youtube-music", "multimedia-audio-player"],
    "gemini": ["gemini", "assistant"],
    "google-chat": ["google-chat", "chat", "instant-messaging"],
    "google-photos": ["google-photos", "photos", "image-viewer"],
    "google-maps": ["google-maps", "maps", "app.organicmaps.desktop"],
    "google-docs": ["google-docs", "x-office-document"],
    "google-sheets": ["google-sheets", "x-office-spreadsheet"],
}


class WebAppManager(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Web App Manager")
        self.setMinimumSize(800, 740)

        self.data_dir = os.path.expanduser("~/.local/share")
        self.desktop_dir = os.path.join(self.data_dir, "applications")
        self.bin_dir = os.path.expanduser("~/.local/bin")
        self.icon_dir = os.path.join(
            self.data_dir, "icons", "hicolor", "128x128", "apps"
        )
        self.profiles_dir = os.path.join(self.data_dir, "googleapp-profiles")
        self.runner_bin = os.path.join(self.bin_dir, "googleapp-runner")
        self.kmenu_file = os.path.expanduser("~/.config/menus/applications-kmenuedit.menu")

        for directory in (
            self.desktop_dir,
            self.bin_dir,
            self.icon_dir,
            self.profiles_dir,
        ):
            os.makedirs(directory, exist_ok=True)

        self.checkboxes = []

        # Ensure runner binary and self-registration desktop entry
        self.ensure_runner_binary()
        self.ensure_manager_desktop_entry()

        self.init_ui()

    def ensure_runner_binary(self):
        """Build or verify native googleapp-runner binary."""
        if os.path.isfile(self.runner_bin) and os.access(self.runner_bin, os.X_OK):
            return True

        script_dir = os.path.dirname(os.path.abspath(__file__))
        cpp_file = os.path.join(script_dir, "googleapp_runner.cpp")
        if not os.path.isfile(cpp_file):
            return False

        if not shutil.which("g++"):
            return False

        try:
            pkg_res = subprocess.run(
                ["pkg-config", "--cflags", "--libs", "Qt6WebEngineQuick", "Qt6WebEngineCore", "Qt6Network", "Qt6Quick", "Qt6Gui", "KF6WindowSystem"],
                capture_output=True,
                text=True,
            )
            if pkg_res.returncode != 0:
                return False

            flags = shlex.split(pkg_res.stdout)
            local_bin = os.path.join(script_dir, "googleapp-runner")
            compile_res = subprocess.run(
                ["g++", "-O2", "-fPIC", cpp_file] + flags + ["-o", local_bin],
                capture_output=True,
                text=True,
            )
            if compile_res.returncode == 0:
                shutil.copy2(local_bin, self.runner_bin)
                os.chmod(self.runner_bin, 0o755)
                return True
        except Exception:
            return False

        return False

    def ensure_manager_desktop_entry(self):
        """Install desktop launcher and icon for this Web App Manager."""
        icon_path = os.path.join(self.icon_dir, "webapp-manager.png")
        if not os.path.isfile(icon_path):
            try:
                pix = QPixmap(128, 128)
                pix.fill(Qt.GlobalColor.transparent)
                p = QPainter(pix)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                grad = QLinearGradient(0, 0, 128, 128)
                grad.setColorAt(0.0, QColor("#3584e4"))
                grad.setColorAt(1.0, QColor("#1c71d8"))
                p.setBrush(QBrush(grad))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(QRectF(8, 8, 112, 112), 24, 24)
                p.setPen(QColor("#ffffff"))
                p.setFont(QFont("Sans Serif", 44, QFont.Weight.Bold))
                p.drawText(QRectF(0, 0, 128, 128), Qt.AlignmentFlag.AlignCenter, "🌐")
                p.end()
                pix.save(icon_path)
            except Exception:
                pass

        # Wrapper script in ~/.local/bin/webapp-manager
        script_dir = os.path.dirname(os.path.abspath(__file__))
        venv_python = os.path.join(script_dir, "venv", "bin", "python3")
        python_exec = venv_python if os.path.isfile(venv_python) else sys.executable
        script_file = os.path.join(script_dir, "googleApp.py")

        wrapper_path = os.path.join(self.bin_dir, "webapp-manager")
        wrapper_content = f"""#!/bin/sh
set -eu
exec {shlex.quote(python_exec)} {shlex.quote(script_file)} "$@"
"""
        try:
            with open(wrapper_path, "w", encoding="utf-8") as f:
                f.write(wrapper_content)
            os.chmod(wrapper_path, 0o755)
        except OSError:
            pass

        # Desktop entry
        desktop_path = os.path.join(self.desktop_dir, "webapp-manager.desktop")
        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Web App Manager
GenericName=Web App Installer
Comment=Install and manage standalone desktop web applications
Exec={wrapper_path}
Terminal=false
Icon=webapp-manager
StartupNotify=true
Categories=System;Settings;Utility;
Keywords=Web;App;Installer;Manager;Google;PWA;
"""
        try:
            with open(desktop_path, "w", encoding="utf-8") as f:
                f.write(desktop_content)
            os.chmod(desktop_path, 0o644)
        except OSError:
            pass

    def init_ui(self):
        # Global stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e222b;
            }
            QWidget {
                color: #e6edf3;
                font-family: 'Sans Serif';
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid #313846;
                background-color: #242933;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background: #1a1d24;
                color: #8b949e;
                padding: 10px 24px;
                border: 1px solid #313846;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #242933;
                color: #ffffff;
                border-bottom: 2px solid #3584e4;
            }
            QLineEdit, QComboBox {
                background-color: #181a1f;
                border: 1px solid #3d4455;
                border-radius: 6px;
                padding: 8px 12px;
                color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #3584e4;
            }
            QPushButton {
                background-color: #2d3342;
                border: 1px solid #3d4455;
                border-radius: 6px;
                padding: 8px 16px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #384052;
                border-color: #4f586d;
            }
            QPushButton:pressed {
                background-color: #252a36;
            }
            QGroupBox {
                border: 1px solid #313846;
                border-radius: 8px;
                margin-top: 14px;
                padding: 14px;
                font-weight: bold;
                color: #78aeed;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QTableWidget {
                background-color: #181a1f;
                border: 1px solid #313846;
                border-radius: 6px;
                gridline-color: #242933;
            }
            QHeaderView::section {
                background-color: #242933;
                color: #8b949e;
                padding: 6px;
                border: none;
                font-weight: bold;
            }
        """)

        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Title
        title_layout = QHBoxLayout()
        header_icon = QLabel("🌐")
        header_icon.setFont(QFont("Sans Serif", 22))
        title_layout.addWidget(header_icon)

        title_text_layout = QVBoxLayout()
        title = QLabel("Web App Manager")
        title.setFont(QFont("Sans Serif", 16, QFont.Weight.Bold))
        subtitle = QLabel("Create and manage standalone native desktop web applications")
        subtitle.setStyleSheet("color: #8b949e; font-size: 12px;")
        title_text_layout.addWidget(title)
        title_text_layout.addWidget(subtitle)
        title_layout.addLayout(title_text_layout)
        title_layout.addStretch()

        main_layout.addLayout(title_layout)

        # Tab Widget
        self.tabs = QTabWidget()

        # Tab 1: Install New App
        self.tab_install = QWidget()
        self.setup_install_tab()
        self.tabs.addTab(self.tab_install, "✨ Install New App")

        # Tab 2: Manage Installed Apps
        self.tab_manage = QWidget()
        self.setup_manage_tab()
        self.tabs.addTab(self.tab_manage, "📦 Installed Apps")

        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)

    def setup_install_tab(self):
        layout = QVBoxLayout(self.tab_install)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Custom App Box
        create_group = QGroupBox("Install New Application from URL")
        create_layout = QVBoxLayout()
        create_layout.setSpacing(10)

        # Form Fields
        form_grid = QGridLayout()
        form_grid.setSpacing(10)

        form_grid.addWidget(QLabel("Application Name:"), 0, 0)
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g. ChatGPT, Notion, Slack, Spotify, Reddit")
        self.input_name.textChanged.connect(self.update_icon_preview)
        form_grid.addWidget(self.input_name, 0, 1)

        form_grid.addWidget(QLabel("Web URL:"), 1, 0)
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("e.g. https://chatgpt.com")
        self.input_url.textChanged.connect(self.update_icon_preview)
        form_grid.addWidget(self.input_url, 1, 1)

        form_grid.addWidget(QLabel("Menu Category:"), 2, 0)
        self.category_combo = QComboBox()
        self.category_combo.addItems(list(CATEGORY_MAP.keys()))
        form_grid.addWidget(self.category_combo, 2, 1)

        # Icon Selection & Preview Row
        form_grid.addWidget(QLabel("Application Icon:"), 3, 0)
        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)

        self.icon_preview = QLabel("🌐")
        self.icon_preview.setFixedSize(42, 42)
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview.setStyleSheet("""
            background-color: #181a1f;
            border: 1px solid #3d4455;
            border-radius: 6px;
            font-size: 20px;
        """)
        icon_row.addWidget(self.icon_preview)

        self.input_icon_path = QLineEdit()
        self.input_icon_path.setPlaceholderText("Auto: system icon first, then web favicon, or select custom path...")
        self.input_icon_path.textChanged.connect(self.update_icon_preview)
        icon_row.addWidget(self.input_icon_path)

        browse_btn = QPushButton("📁 Browse...")
        browse_btn.clicked.connect(self.browse_custom_icon)
        icon_row.addWidget(browse_btn)

        auto_btn = QPushButton("↺ Auto")
        auto_btn.setToolTip("Reset to auto-detection (System icon -> Web favicon)")
        auto_btn.clicked.connect(self.reset_icon_to_auto)
        icon_row.addWidget(auto_btn)

        form_grid.addLayout(icon_row, 3, 1)

        create_layout.addLayout(form_grid)

        # Options
        self.hide_header_check = QCheckBox("Hide redundant web UI top header (Google masthead / banner) on load")
        self.hide_header_check.setChecked(True)
        self.hide_header_check.setStyleSheet("color: #78aeed;")
        create_layout.addWidget(self.hide_header_check)

        # Install Button
        install_btn = QPushButton("🚀 Install Application")
        install_btn.setStyleSheet("""
            background-color: #3584e4;
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            padding: 10px;
            border-radius: 6px;
        """)
        install_btn.clicked.connect(self.handle_install_custom_app)
        create_layout.addWidget(install_btn)

        create_group.setLayout(create_layout)
        layout.addWidget(create_group)

        # Google Apps Presets Group
        presets_group = QGroupBox("Google Apps & Presets")
        presets_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        grid = QGridLayout(scroll_content)
        grid.setSpacing(8)

        self.checkboxes = []
        for index, app_info in enumerate(DEFAULT_GOOGLE_APPS):
            cb = QCheckBox(app_info["name"])
            cb.setChecked(True)
            cb.setProperty("app_data", app_info)
            self.checkboxes.append(cb)
            grid.addWidget(cb, index // 2, index % 2)

        scroll.setWidget(scroll_content)
        presets_layout.addWidget(scroll)

        # Preset Buttons
        btn_layout = QHBoxLayout()
        sel_all = QPushButton("Select All")
        sel_all.clicked.connect(lambda: [c.setChecked(True) for c in self.checkboxes])
        desel_all = QPushButton("Deselect All")
        desel_all.clicked.connect(lambda: [c.setChecked(False) for c in self.checkboxes])
        install_presets_btn = QPushButton("Install Selected Google Apps")
        install_presets_btn.setStyleSheet("background-color: #1c71d8; color: white;")
        install_presets_btn.clicked.connect(self.handle_install_presets)

        btn_layout.addWidget(sel_all)
        btn_layout.addWidget(desel_all)
        btn_layout.addWidget(install_presets_btn)
        presets_layout.addLayout(btn_layout)

        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)

    def browse_custom_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Application Icon",
            os.path.expanduser("~"),
            "Images (*.png *.svg *.ico *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if file_path:
            self.input_icon_path.setText(file_path)
            self.update_icon_preview()

    def reset_icon_to_auto(self):
        self.input_icon_path.clear()
        self.update_icon_preview()

    def update_icon_preview(self):
        custom_path = self.input_icon_path.text().strip()
        if custom_path:
            expanded = os.path.expanduser(custom_path)
            if os.path.isfile(expanded):
                pix = QPixmap(expanded)
                if not pix.isNull():
                    self.icon_preview.setPixmap(
                        pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    )
                    self.icon_preview.setText("")
                    return

        name = self.input_name.text().strip()
        if name:
            slug = self.make_slug(name)
            sys_name, sys_path = self.find_system_icon(slug, name)
            if sys_path and os.path.isfile(sys_path):
                pix = QPixmap(sys_path)
                if not pix.isNull():
                    self.icon_preview.setPixmap(
                        pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    )
                    self.icon_preview.setText("")
                    return
            elif sys_name and QIcon.hasThemeIcon(sys_name):
                self.icon_preview.setPixmap(QIcon.fromTheme(sys_name).pixmap(32, 32))
                self.icon_preview.setText("")
                return

        # Default fallback icon
        self.icon_preview.setPixmap(QPixmap())
        self.icon_preview.setText("🌐")

    def setup_manage_tab(self):
        layout = QVBoxLayout(self.tab_manage)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Applications installed via Web App Manager:"))
        top_bar.addStretch()

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.clicked.connect(self.populate_installed_table)
        top_bar.addWidget(refresh_btn)
        layout.addLayout(top_bar)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Icon & Name", "URL", "Category", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 230)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.populate_installed_table()

    def populate_installed_table(self):
        apps = self.get_installed_apps()
        self.table.setRowCount(len(apps))

        for row, app in enumerate(apps):
            self.table.setRowHeight(row, 44)

            # Column 0: Icon & Name
            icon_item = QTableWidgetItem(f"  {app['name']}")
            if app["icon_path"] and os.path.isfile(app["icon_path"]):
                icon_item.setIcon(QIcon(app["icon_path"]))
            elif app["icon_name"] and QIcon.hasThemeIcon(app["icon_name"]):
                icon_item.setIcon(QIcon.fromTheme(app["icon_name"]))
            else:
                icon_item.setIcon(QIcon.fromTheme("internet-web-browser"))

            icon_item.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
            self.table.setItem(row, 0, icon_item)

            # Column 1: URL
            url_item = QTableWidgetItem(app["url"])
            url_item.setForeground(QColor("#78aeed"))
            self.table.setItem(row, 1, url_item)

            # Column 2: Category
            cat_display = app["categories"].split(";")[0] if app["categories"] else "Internet"
            cat_item = QTableWidgetItem(cat_display)
            self.table.setItem(row, 2, cat_item)

            # Column 3: Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(6)

            launch_btn = QPushButton("▶ Launch")
            launch_btn.setStyleSheet("background-color: #26a269; color: white; padding: 4px 8px;")
            launch_btn.clicked.connect(lambda _, s=app["slug"]: self.launch_app(s))

            icon_btn = QPushButton("🎨 Icon")
            icon_btn.setStyleSheet("background-color: #3584e4; color: white; padding: 4px 8px;")
            icon_btn.setToolTip("Change custom icon for this app")
            icon_btn.clicked.connect(lambda _, a=app: self.change_app_icon(a))

            del_btn = QPushButton("✕")
            del_btn.setStyleSheet("background-color: #c01c28; color: white; padding: 4px 8px;")
            del_btn.setToolTip("Uninstall this application")
            del_btn.clicked.connect(lambda _, s=app["slug"], n=app["name"]: self.uninstall_app(s, n))

            actions_layout.addWidget(launch_btn)
            actions_layout.addWidget(icon_btn)
            actions_layout.addWidget(del_btn)
            self.table.setCellWidget(row, 3, actions_widget)

    def get_installed_apps(self):
        apps = []
        if not os.path.isdir(self.desktop_dir):
            return apps

        for filename in sorted(os.listdir(self.desktop_dir)):
            if filename.startswith("googleapp-") and filename.endswith(".desktop"):
                slug = filename[len("googleapp-"):-len(".desktop")]
                desktop_file = os.path.join(self.desktop_dir, filename)
                script_file = os.path.join(self.bin_dir, f"googleapp-{slug}.sh")

                name = slug
                categories = "Internet"
                icon_name = f"googleapp-{slug}"
                url = ""

                try:
                    with open(desktop_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("Name="):
                                name = line.strip().split("=", 1)[1]
                            elif line.startswith("Categories="):
                                categories = line.strip().split("=", 1)[1]
                            elif line.startswith("Icon="):
                                icon_name = line.strip().split("=", 1)[1]
                except OSError:
                    continue

                if os.path.isfile(script_file):
                    try:
                        with open(script_file, "r", encoding="utf-8") as f:
                            content = f.read()
                            match = re.search(r"--url\s+(\S+)", content)
                            if match:
                                url = match.group(1).strip("'\"")
                    except OSError:
                        pass

                icon_path = ""
                # Check custom/downloaded file
                png_path = os.path.join(self.icon_dir, f"{icon_name}.png")
                svg_path = os.path.join(self.icon_dir, f"{icon_name}.svg")
                if os.path.isfile(icon_name):
                    icon_path = icon_name
                elif os.path.isfile(png_path):
                    icon_path = png_path
                elif os.path.isfile(svg_path):
                    icon_path = svg_path
                elif shutil.which("kiconfinder6"):
                    res = subprocess.run(["kiconfinder6", icon_name], capture_output=True, text=True)
                    if res.returncode == 0 and res.stdout.strip() and os.path.isfile(res.stdout.strip()):
                        icon_path = res.stdout.strip()

                apps.append({
                    "slug": slug,
                    "name": name,
                    "url": url,
                    "categories": categories,
                    "icon_name": icon_name,
                    "icon_path": icon_path,
                })

        return apps

    def launch_app(self, slug):
        script_path = os.path.join(self.bin_dir, f"googleapp-{slug}.sh")
        if os.path.isfile(script_path):
            subprocess.Popen([script_path])

    def uninstall_app(self, slug, name):
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Are you sure you want to uninstall '{name}'?\nThis will remove its desktop launcher and script.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            desktop_file = os.path.join(self.desktop_dir, f"googleapp-{slug}.desktop")
            script_file = os.path.join(self.bin_dir, f"googleapp-{slug}.sh")

            for path in (desktop_file, script_file):
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                except OSError:
                    pass

            self.remove_from_kmenuedit(f"googleapp-{slug}.desktop")
            self.refresh_desktop_system()
            self.populate_installed_table()

    def change_app_icon(self, app):
        slug = app["slug"]
        name = app["name"]
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Select Custom Icon for {name}",
            "",
            "Images (*.png *.svg *.ico *.jpg *.jpeg *.webp);;All Files (*)",
        )
        if not file_path or not os.path.isfile(file_path):
            return

        _, ext = os.path.splitext(file_path)
        if not ext:
            ext = ".png"
        target_name = f"googleapp-{slug}"
        target_file = os.path.join(self.icon_dir, f"{target_name}{ext}")

        try:
            shutil.copy2(file_path, target_file)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not copy icon file:\n{e}")
            return

        # Invalidate any cached runner icon
        cached_icon = os.path.expanduser(f"~/.cache/googleapp/googleapp-{slug}/app_icon.png")
        if os.path.isfile(cached_icon):
            try:
                os.remove(cached_icon)
            except OSError:
                pass

        # Update launcher shell script
        script_file = os.path.join(self.bin_dir, f"googleapp-{slug}.sh")
        if os.path.isfile(script_file):
            try:
                with open(script_file, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = re.sub(
                    r'--icon\s+([^\s"]+|"[^"]*"|\'[^\']*\')',
                    f'--icon "{target_file}"',
                    content,
                )
                with open(script_file, "w", encoding="utf-8") as f:
                    f.write(new_content)
                os.chmod(script_file, 0o755)
            except Exception as e:
                print(f"Warning: failed to update script {script_file}: {e}")

        # Update desktop entry
        desktop_file = os.path.join(self.desktop_dir, f"googleapp-{slug}.desktop")
        if os.path.isfile(desktop_file):
            try:
                with open(desktop_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                with open(desktop_file, "w", encoding="utf-8") as f:
                    for line in lines:
                        if line.startswith("Icon="):
                            f.write(f"Icon={target_file}\n")
                        else:
                            f.write(line)
            except Exception as e:
                print(f"Warning: failed to update desktop file {desktop_file}: {e}")

        self.refresh_desktop_system()
        self.populate_installed_table()
        QMessageBox.information(self, "Icon Updated", f"Custom icon for '{name}' was successfully updated.")

    @staticmethod
    def make_slug(value):
        slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return slug or "web-app"

    @staticmethod
    def valid_url(url):
        try:
            parsed = urlsplit(url)
            return (
                parsed.scheme in ("http", "https")
                and bool(parsed.hostname)
                and not any(c in url for c in "\r\n\t")
            )
        except ValueError:
            return False

    def find_system_icon(self, slug, name):
        """
        Check if an icon exists in the active system icon theme.
        Returns: (theme_icon_name, file_path) or (None, None)
        """
        candidates = []
        if slug in KNOWN_SYSTEM_ICON_ALIASES:
            candidates.extend(KNOWN_SYSTEM_ICON_ALIASES[slug])

        candidates.append(slug)
        name_clean = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
        if name_clean and name_clean not in candidates:
            candidates.append(name_clean)

        seen = set()
        unique_candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        for cand in unique_candidates:
            # 1. Try kiconfinder6 / kiconfinder5
            for kfinder in ("kiconfinder6", "kiconfinder5"):
                if shutil.which(kfinder):
                    res = subprocess.run([kfinder, cand], capture_output=True, text=True)
                    if res.returncode == 0:
                        path = res.stdout.strip()
                        if path and os.path.isfile(path):
                            return cand, path

            # 2. Try QIcon.hasThemeIcon
            if QIcon.hasThemeIcon(cand):
                return cand, ""

        return None, None

    def resolve_app_icon(self, slug, name, url, custom_icon_path=""):
        """
        Priority order:
        1. Custom icon path if provided and exists.
        2. System icon from the active icon theme.
        3. WebApp-Manager assigned icon (downloaded 128x128 favicon from domain).
        4. Generic web browser fallback.

        Returns: (desktop_icon_name, runner_icon_arg)
        """
        # Priority 1: Custom Icon Path
        if custom_icon_path:
            custom_path = os.path.expanduser(custom_icon_path.strip())
            if os.path.isfile(custom_path):
                _, ext = os.path.splitext(custom_path)
                if not ext:
                    ext = ".png"
                target_name = f"googleapp-{slug}"
                target_file = os.path.join(self.icon_dir, f"{target_name}{ext}")
                try:
                    shutil.copy2(custom_path, target_file)
                    return target_name, target_file
                except OSError:
                    return custom_path, custom_path

        # Priority 2: System Icon Theme
        sys_name, sys_path = self.find_system_icon(slug, name)
        if sys_name:
            return sys_name, sys_path or sys_name

        # Priority 3: WebApp-Manager Assigned Icon (Domain Favicon)
        icon_name = f"googleapp-{slug}"
        icon_path = os.path.join(self.icon_dir, icon_name + ".png")

        try:
            domain = urlsplit(url).hostname
            if domain:
                icon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
                response = requests.get(icon_url, timeout=5)
                response.raise_for_status()

                if response.headers.get("content-type", "").startswith("image/"):
                    with open(icon_path, "wb") as icon_file:
                        icon_file.write(response.content)
                    return icon_name, icon_path
        except (requests.RequestException, OSError, ValueError):
            pass

        if os.path.isfile(icon_path):
            return icon_name, icon_path

        # Priority 4: Fallback
        return "internet-web-browser", ""

    def install_single_app(self, name, url, category="Internet", hide_header=True, custom_icon_path=""):
        name = name.strip()
        url = url.strip()
        if not name or not url:
            raise ValueError("Application name and URL must not be empty.")

        if not self.valid_url(url):
            raise ValueError(f"Invalid web URL: '{url}'. Please include http:// or https://")

        slug = self.make_slug(name)
        launcher_id = f"googleapp-{slug}"

        profile_dir = os.path.join(self.profiles_dir, launcher_id)
        os.makedirs(profile_dir, mode=0o700, exist_ok=True)
        os.chmod(profile_dir, 0o700)

        # Resolve icon (Custom -> System Icon Theme -> WebApp-Manager Favicon -> Generic)
        icon_name, runner_icon_target = self.resolve_app_icon(slug, name, url, custom_icon_path)

        runner_args = [
            self.runner_bin,
            "--slug", slug,
            "--name", name,
            "--url", url,
            "--icon", runner_icon_target if runner_icon_target else icon_name,
        ]
        if not hide_header:
            runner_args.append("--show-web-header")

        # Launcher Shell Script
        script_path = os.path.join(self.bin_dir, launcher_id + ".sh")
        script_content = (
            "#!/bin/sh\n"
            "set -eu\n"
            "exec " + shlex.join(runner_args) + ' "$@"\n'
        )
        with open(script_path, "w", encoding="utf-8") as script_file:
            script_file.write(script_content)
        os.chmod(script_path, 0o755)

        # Desktop Entry
        categories = CATEGORY_MAP.get(category, "Network;WebBrowser;")
        desktop_path = os.path.join(self.desktop_dir, launcher_id + ".desktop")
        desktop_icon = runner_icon_target if (runner_icon_target and os.path.isfile(runner_icon_target)) else icon_name
        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={name}
GenericName=Web Application
Comment=Web application for {name}
Exec={script_path}
Terminal=false
Icon={desktop_icon}
StartupNotify=true
StartupWMClass={launcher_id}
Categories={categories}
Keywords=Google;{name};Web;
X-KDE-Category=Google Apps
"""
        with open(desktop_path, "w", encoding="utf-8") as desktop_file:
            desktop_file.write(desktop_content)
        os.chmod(desktop_path, 0o644)

        # Add to custom menu layout if applicable
        self.add_to_kmenuedit(f"{launcher_id}.desktop")

        return launcher_id

    def add_to_kmenuedit(self, desktop_filename):
        """Ensure the desktop entry is included in ~/.config/menus/applications-kmenuedit.menu."""
        if not os.path.isfile(self.kmenu_file):
            return

        try:
            with open(self.kmenu_file, "r", encoding="utf-8") as f:
                content = f.read()

            if desktop_filename in content:
                return

            entry_xml = f"   <Filename>{desktop_filename}</Filename>\n"

            # Insert into <Name>Applications</Name> Layout & Include
            if "<Name>Applications</Name>" in content:
                content = content.replace(
                    "<Name>Applications</Name>\n  <Layout>\n   <Merge type=\"files\"/>\n",
                    "<Name>Applications</Name>\n  <Layout>\n   <Merge type=\"files\"/>\n" + entry_xml,
                )
                if "</Include>" in content:
                    idx = content.rfind("</Include>")
                    content = content[:idx] + entry_xml + content[idx:]

                with open(self.kmenu_file, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception:
            pass

    def remove_from_kmenuedit(self, desktop_filename):
        """Remove entry from ~/.config/menus/applications-kmenuedit.menu."""
        if not os.path.isfile(self.kmenu_file):
            return
        try:
            with open(self.kmenu_file, "r", encoding="utf-8") as f:
                content = f.read()
            if desktop_filename in content:
                content = re.sub(rf"\s*<Filename>{re.escape(desktop_filename)}</Filename>", "", content)
                with open(self.kmenu_file, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception:
            pass

    def refresh_desktop_system(self):
        """Update desktop database, icon cache, and KDE sycoca cache."""
        if shutil.which("update-desktop-database"):
            subprocess.run(["update-desktop-database", self.desktop_dir], capture_output=True, text=True)
        if shutil.which("gtk-update-icon-cache"):
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", os.path.expanduser("~/.local/share/icons/hicolor")],
                capture_output=True,
                text=True,
            )
        if shutil.which("kbuildsycoca6"):
            subprocess.run(["kbuildsycoca6", "--noincremental"], capture_output=True, text=True)
        if shutil.which("dbus-send"):
            subprocess.run(
                [
                    "dbus-send", "--session", "--dest=org.kde.KWin",
                    "--type=method_call", "/KWin", "org.kde.KWin.reconfigure",
                ],
                capture_output=True,
                text=True,
            )

    def handle_install_custom_app(self):
        name = self.input_name.text().strip()
        url = self.input_url.text().strip()
        category = self.category_combo.currentText()
        hide_header = self.hide_header_check.isChecked()
        custom_icon = self.input_icon_path.text().strip()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter an application name.")
            self.input_name.setFocus()
            return

        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a web URL.")
            self.input_url.setFocus()
            return

        try:
            launcher_id = self.install_single_app(
                name, url, category, hide_header, custom_icon_path=custom_icon
            )
            self.refresh_desktop_system()
            self.populate_installed_table()

            # Clear inputs
            self.input_name.clear()
            self.input_url.clear()
            self.input_icon_path.clear()
            self.update_icon_preview()

            QMessageBox.information(
                self,
                "Installation Successful",
                f"Application '{name}' was installed successfully!\n\n"
                f"• Desktop launcher: ~/.local/share/applications/{launcher_id}.desktop\n"
                f"• Runner script: ~/.local/bin/{launcher_id}.sh\n\n"
                "The application is now available in your Application Launcher and search.",
            )
            self.tabs.setCurrentIndex(1)  # Switch to Installed tab to show it
        except Exception as e:
            QMessageBox.critical(self, "Installation Error", str(e))

    def handle_install_presets(self):
        selected = [cb.property("app_data") for cb in self.checkboxes if cb.isChecked()]
        if not selected:
            QMessageBox.warning(self, "Selection Required", "Please select at least one preset app.")
            return

        created = 0
        errors = []
        for app in selected:
            try:
                cat_first = app.get("categories", "").split(";")[0] or "Internet"
                self.install_single_app(app["name"], app["url"], cat_first, True)
                created += 1
            except Exception as e:
                errors.append(f"{app['name']}: {e}")

        self.refresh_desktop_system()
        self.populate_installed_table()

        msg = f"Successfully installed {created} preset application(s) with system/web icons."
        if errors:
            msg += "\n\nErrors:\n" + "\n".join(errors)
        QMessageBox.information(self, "Preset Installation", msg)
        self.tabs.setCurrentIndex(1)


# ==============================================================================
# CLI and Entrypoint
# ==============================================================================
def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd in ("--install", "-i") and len(sys.argv) >= 4:
            name = sys.argv[2]
            url = sys.argv[3]
            category = "Internet"
            custom_icon = ""

            args = sys.argv[4:]
            idx = 0
            while idx < len(args):
                if args[idx] in ("--category", "-c") and idx + 1 < len(args):
                    category = args[idx + 1]
                    idx += 2
                elif args[idx] in ("--icon",) and idx + 1 < len(args):
                    custom_icon = args[idx + 1]
                    idx += 2
                else:
                    idx += 1

            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            app = QApplication(sys.argv)
            mgr = WebAppManager()
            try:
                lid = mgr.install_single_app(
                    name, url, category, hide_header=True, custom_icon_path=custom_icon
                )
                mgr.refresh_desktop_system()
                print(f"✓ Successfully installed '{name}' ({lid}) for URL: {url}")
                sys.exit(0)
            except Exception as e:
                print(f"✗ Error installing {name}: {e}", file=sys.stderr)
                sys.exit(1)

        elif cmd in ("--all", "-a"):
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            app = QApplication(sys.argv)
            mgr = WebAppManager()
            for gapp in DEFAULT_GOOGLE_APPS:
                cat_first = gapp.get("categories", "").split(";")[0] or "Internet"
                mgr.install_single_app(gapp["name"], gapp["url"], cat_first, True)
                print(f"  ✓ {gapp['name']} installed")
            mgr.refresh_desktop_system()
            print("✓ All default Google Apps installed successfully.")
            sys.exit(0)

        elif cmd in ("--list", "-l"):
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            app = QApplication(sys.argv)
            mgr = WebAppManager()
            installed = mgr.get_installed_apps()
            print(f"Found {len(installed)} installed web application(s):")
            for item in installed:
                print(f"  • {item['name']} ({item['slug']}) [Icon: {item['icon_name']}] -> {item['url']}")
            sys.exit(0)

    app = QApplication(sys.argv)
    window = WebAppManager()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
