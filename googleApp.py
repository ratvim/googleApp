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
    QRadioButton,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QMessageBox,
    QInputDialog,
    QGroupBox,
    QGridLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


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


class GoogleAppCreator(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Google App & Standalone Web App Builder")
        self.setMinimumSize(640, 780)

        self.data_dir = os.path.expanduser("~/.local/share")
        self.desktop_dir = os.path.join(self.data_dir, "applications")
        self.bin_dir = os.path.expanduser("~/.local/bin")
        self.icon_dir = os.path.join(
            self.data_dir, "icons", "hicolor", "128x128", "apps"
        )
        self.profiles_dir = os.path.join(self.data_dir, "googleapp-profiles")
        self.runner_bin = os.path.join(self.bin_dir, "googleapp-runner")

        for directory in (
            self.desktop_dir,
            self.bin_dir,
            self.icon_dir,
            self.profiles_dir,
        ):
            os.makedirs(directory, exist_ok=True)

        self.custom_apps = []
        self.checkboxes = []

        # Ensure native runner binary is ready
        self.ensure_runner_binary()

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
                ["pkg-config", "--cflags", "--libs", "Qt6WebEngineQuick", "Qt6Quick", "Qt6Gui"],
                capture_output=True,
                text=True,
            )
            if pkg_res.returncode != 0:
                return False

            flags = shlex.split(pkg_res.stdout)
            local_bin = os.path.join(script_dir, "googleapp-runner")
            compile_res = subprocess.run(
                ["g++", "-O2", cpp_file] + flags + ["-o", local_bin],
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

    def init_ui(self):
        main_layout = QVBoxLayout()

        title = QLabel("Google App & Standalone Web App Builder")
        title.setFont(QFont("Sans Serif", 13, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        description = QLabel(
            "Launch each Google App as an independent native desktop window application.\n"
            "Features a custom application bar with Minimize, Maximize, and Close controls, "
            "with redundant web UI headers removed."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        main_layout.addWidget(description)

        # Window & Architecture Style Selection
        style_group = QGroupBox("Window application style")
        style_layout = QVBoxLayout()

        self.native_window_radio = QRadioButton(
            "Native Standalone Window (Integrated application bar, window controls, hidden web UI top bar)"
        )
        self.native_window_radio.setChecked(True)
        self.native_window_radio.setStyleSheet("font-weight: bold;")
        style_layout.addWidget(self.native_window_radio)

        self.hide_web_header_check = QCheckBox(
            "Hide redundant web UI top header (Google Bar / masthead / search bar) on load"
        )
        self.hide_web_header_check.setChecked(True)
        self.hide_web_header_check.setStyleSheet("margin-left: 22px; color: #3584e4;")
        style_layout.addWidget(self.hide_web_header_check)

        self.browser_window_radio = QRadioButton(
            "Browser App Mode (Legacy launch via Flatpak Chrome or Chromium --app)"
        )
        style_layout.addWidget(self.browser_window_radio)

        self.browser_widget = QWidget()
        browser_layout = QVBoxLayout(self.browser_widget)
        browser_layout.setContentsMargins(22, 0, 0, 0)
        browser_layout.addWidget(QLabel("Browser command (e.g. flatpak run com.google.Chrome):"))
        self.browser_input = QLineEdit()
        self.browser_input.setText(self.detect_browser())
        browser_layout.addWidget(self.browser_input)
        style_layout.addWidget(self.browser_widget)

        self.native_window_radio.toggled.connect(self.update_style_visibility)
        self.update_style_visibility()

        style_group.setLayout(style_layout)
        main_layout.addWidget(style_group)

        # App Selection List
        apps_group = QGroupBox("Select applications to create")
        apps_layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        self.grid_layout = QGridLayout(scroll_content)

        for index, app_info in enumerate(DEFAULT_GOOGLE_APPS):
            checkbox = QCheckBox(app_info["name"])
            checkbox.setChecked(True)
            checkbox.setProperty("app_data", app_info)
            self.checkboxes.append(checkbox)
            self.grid_layout.addWidget(checkbox, index // 2, index % 2)

        scroll.setWidget(scroll_content)
        apps_layout.addWidget(scroll)
        apps_group.setLayout(apps_layout)
        main_layout.addWidget(apps_group)

        # Custom Web Applications Group
        custom_group = QGroupBox("Custom web applications")
        custom_layout = QVBoxLayout()

        self.custom_list_label = QLabel("No custom apps added yet.")
        self.custom_list_label.setWordWrap(True)
        custom_layout.addWidget(self.custom_list_label)

        add_button = QPushButton("Add Custom Web App...")
        add_button.clicked.connect(self.add_custom_app_dialog)
        custom_layout.addWidget(add_button)

        custom_group.setLayout(custom_layout)
        main_layout.addWidget(custom_group)

        # Bottom Actions
        action_layout = QHBoxLayout()

        select_all = QPushButton("Select All")
        select_all.clicked.connect(lambda: self.set_all_checkboxes(True))
        action_layout.addWidget(select_all)

        deselect_all = QPushButton("Deselect All")
        deselect_all.clicked.connect(lambda: self.set_all_checkboxes(False))
        action_layout.addWidget(deselect_all)

        generate = QPushButton("Create Selected Applications")
        generate.setStyleSheet(
            "font-weight: bold; padding: 10px; background-color: #3584e4; color: #ffffff; border-radius: 6px;"
        )
        generate.clicked.connect(self.generate_applications)
        action_layout.addWidget(generate)

        main_layout.addLayout(action_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def update_style_visibility(self):
        is_native = self.native_window_radio.isChecked()
        self.hide_web_header_check.setEnabled(is_native)
        self.browser_widget.setVisible(not is_native)

    def detect_browser(self):
        if shutil.which("flatpak"):
            for candidate in (
                "com.google.Chrome",
                "org.chromium.Chromium",
                "com.brave.Browser",
            ):
                result = subprocess.run(
                    ["flatpak", "info", candidate],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    return f"flatpak run {candidate}"

        for candidate in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "brave-browser",
        ):
            path = shutil.which(candidate)
            if path:
                return path

        return "flatpak run com.google.Chrome"

    def set_all_checkboxes(self, state):
        for checkbox in self.checkboxes:
            checkbox.setChecked(state)

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

    def add_custom_app_dialog(self):
        name, accepted = QInputDialog.getText(
            self, "Custom App Name", "Enter application name:"
        )
        if not accepted or not name.strip():
            return

        url, accepted = QInputDialog.getText(
            self, "Custom App URL", "Enter URL (e.g. https://example.com):"
        )
        if not accepted or not url.strip():
            return

        url = url.strip()
        if "://" not in url:
            url = "https://" + url

        if not self.valid_url(url):
            QMessageBox.warning(
                self, "Invalid URL", "Enter a valid HTTP or HTTPS URL."
            )
            return

        slug = self.make_slug(name)
        if any(
            app["slug"] == slug
            for app in (DEFAULT_GOOGLE_APPS + self.custom_apps)
        ):
            QMessageBox.warning(
                self, "Duplicate App", "An application with this slug already exists."
            )
            return

        self.custom_apps.append({
            "name": name.strip(),
            "slug": slug,
            "url": url,
        })

        self.custom_list_label.setText(
            "Added: " + ", ".join(app["name"] for app in self.custom_apps)
        )

    def resolve_and_install_icon(self, slug, url):
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
                    return icon_name
        except (requests.RequestException, OSError, ValueError):
            pass

        return "internet-web-browser"

    @staticmethod
    def desktop_escape(value):
        """Escape a value for a desktop-entry string field."""
        return (
            str(value)
            .replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )

    @staticmethod
    def desktop_exec_arg(value):
        """Quote one argument using desktop Exec syntax."""
        value = str(value)
        if value and re.fullmatch(r"[A-Za-z0-9_./:=+-]+", value):
            return value

        value = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("`", "\\`")
            .replace("$", "\\$")
            .replace("%", "%%")
        )
        return '"' + value + '"'

    def create_launcher(self, app, browser_parts):
        name = app["name"]
        app_slug = self.make_slug(app["slug"])
        launcher_id = f"googleapp-{app_slug}"
        url = app["url"]

        profile_dir = os.path.join(self.profiles_dir, launcher_id)
        os.makedirs(profile_dir, mode=0o700, exist_ok=True)
        os.chmod(profile_dir, 0o700)

        icon_name = self.resolve_and_install_icon(app_slug, url)
        icon_path = os.path.join(self.icon_dir, f"{icon_name}.png")

        use_native_window = (
            self.native_window_radio.isChecked()
            and self.ensure_runner_binary()
        )

        script_path = os.path.join(self.bin_dir, launcher_id + ".sh")

        if use_native_window:
            runner_args = [
                self.runner_bin,
                "--slug", app_slug,
                "--name", name,
                "--url", url,
                "--icon", icon_path if os.path.isfile(icon_path) else icon_name,
            ]
            if not self.hide_web_header_check.isChecked():
                runner_args.append("--show-web-header")

            script_content = (
                "#!/bin/sh\n"
                "set -eu\n"
                "exec " + shlex.join(runner_args) + ' "$@"\n'
            )
            with open(script_path, "w", encoding="utf-8") as script_file:
                script_file.write(script_content)
            os.chmod(script_path, 0o755)

            exec_line = self.desktop_exec_arg(script_path)
        else:
            browser_args = browser_parts + [
                f"--user-data-dir={profile_dir}",
                f"--class={launcher_id}",
                f"--app={url}",
            ]
            script_content = (
                "#!/bin/sh\n"
                "set -eu\n"
                "exec " + shlex.join(browser_args) + "\n"
            )
            with open(script_path, "w", encoding="utf-8") as script_file:
                script_file.write(script_content)
            os.chmod(script_path, 0o755)

            exec_line = self.desktop_exec_arg(script_path)

        desktop_path = os.path.join(self.desktop_dir, launcher_id + ".desktop")

        categories = app.get("categories", "Network;WebBrowser;")
        keywords = app.get("keywords", f"Google;{name};Web;")

        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name={self.desktop_escape(name)}
GenericName=Web Application
Comment=Web application for {self.desktop_escape(name)}
Exec={exec_line}
Terminal=false
Icon={icon_name}
StartupNotify=true
StartupWMClass={launcher_id}
Categories={categories}
Keywords={keywords}
X-KDE-Category=Google Apps
"""
        with open(desktop_path, "w", encoding="utf-8") as desktop_file:
            desktop_file.write(desktop_content)
        os.chmod(desktop_path, 0o644)

    def generate_applications(self):
        use_native = self.native_window_radio.isChecked()
        browser_parts = []

        if use_native:
            if not self.ensure_runner_binary():
                QMessageBox.warning(
                    self,
                    "Runner Build Error",
                    "Could not compile or locate ~/.local/bin/googleapp-runner.\n"
                    "Please ensure g++ and Qt6 development libraries are installed."
                )
                return
        else:
            browser_cmd = self.browser_input.text().strip()
            if not browser_cmd:
                QMessageBox.warning(
                    self, "Warning", "Please specify a browser command."
                )
                return

            try:
                browser_parts = shlex.split(browser_cmd)
            except ValueError as error:
                QMessageBox.warning(self, "Invalid Command", str(error))
                return

            if not browser_parts:
                QMessageBox.warning(
                    self, "Warning", "The browser command is empty."
                )
                return

            executable = browser_parts[0]
            if os.path.sep in executable and not os.path.isfile(executable):
                QMessageBox.warning(
                    self, "Browser Not Found", f"Executable does not exist:\n{executable}"
                )
                return

            if os.path.sep not in executable and shutil.which(executable) is None:
                QMessageBox.warning(
                    self, "Browser Not Found", f"Command not found:\n{executable}"
                )
                return

        selected_apps = [
            checkbox.property("app_data")
            for checkbox in self.checkboxes
            if checkbox.isChecked()
        ]
        selected_apps.extend(self.custom_apps)

        if not selected_apps:
            QMessageBox.warning(
                self, "Warning", "Select or add at least one application."
            )
            return

        created = 0
        errors = []

        for app in selected_apps:
            try:
                self.create_launcher(app, browser_parts)
                created += 1
            except OSError as error:
                errors.append(f"{app['name']}: {error}")

        self.refresh_desktop_system()

        mode_desc = (
            "Native Standalone Window (with custom application bar)"
            if use_native else "Browser App (Chrome/Chromium --app)"
        )

        message = (
            f"Created {created} application launcher(s) in {mode_desc} mode.\n\n"
            f"Desktop files:\n{self.desktop_dir}\n\n"
            f"Launcher scripts:\n{self.bin_dir}\n\n"
            f"Persistent profiles:\n{self.profiles_dir}\n\n"
            "Each app now launches as an independent window with its own application bar, "
            "window controls, and persistent profile."
        )

        if errors:
            message += "\n\nErrors:\n" + "\n".join(errors)

        QMessageBox.information(self, "Launcher Generation Complete", message)

    def refresh_desktop_system(self):
        """Update system desktop database, icon cache, and KDE ksycoca service cache."""
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

    def generate_all_headless(self, native=True, hide_web_header=True):
        self.native_window_radio.setChecked(native)
        self.browser_window_radio.setChecked(not native)
        self.hide_web_header_check.setChecked(hide_web_header)
        created = 0
        errors = []
        for app in DEFAULT_GOOGLE_APPS:
            try:
                self.create_launcher(app, [])
                created += 1
                print(f"  ✓ {app['name']} -> googleapp-{app['slug']}.desktop")
            except Exception as error:
                errors.append(f"{app['name']}: {error}")
                print(f"  ✗ {app['name']}: {error}", file=sys.stderr)

        self.refresh_desktop_system()
        return created, errors


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--all", "--create-all", "-a"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication(sys.argv)
        creator = GoogleAppCreator()
        print("Creating all default Google App standalone launchers...")
        count, errs = creator.generate_all_headless(native=True, hide_web_header=True)
        print(f"\nDone: Created {count} application launchers in Native Standalone Window mode.")
        if errs:
            print("Errors encountered:", file=sys.stderr)
            for err in errs:
                print(f"  - {err}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    app = QApplication(sys.argv)
    window = GoogleAppCreator()
    window.show()
    sys.exit(app.exec())

