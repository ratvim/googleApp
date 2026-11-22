
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
    },
    {
        "name": "Google Gmail",
        "slug": "google-gmail",
        "url": "https://mail.google.com",
    },
    {
        "name": "Google Drive",
        "slug": "google-drive",
        "url": "https://drive.google.com",
    },
    {
        "name": "Google Keep",
        "slug": "google-keep",
        "url": "https://keep.google.com",
    },
    {
        "name": "YouTube",
        "slug": "youtube",
        "url": "https://youtube.com",
    },
    {
        "name": "YouTube Music",
        "slug": "youtube-music",
        "url": "https://music.youtube.com",
    },
    {
        "name": "Gemini",
        "slug": "gemini",
        "url": "https://gemini.google.com",
    },
    {
        "name": "Google Chat",
        "slug": "google-chat",
        "url": "https://chat.google.com",
    },
    {
        "name": "Google Photos",
        "slug": "google-photos",
        "url": "https://photos.google.com",
    },
]


class GoogleAppCreator(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Google App Launcher Builder")
        self.setMinimumSize(600, 720)

        self.data_dir = os.path.expanduser("~/.local/share")
        self.desktop_dir = os.path.join(
            self.data_dir, "applications"
        )
        self.bin_dir = os.path.expanduser("~/.local/bin")
        self.icon_dir = os.path.join(
            self.data_dir, "icons", "hicolor",
            "128x128", "apps"
        )
        self.profiles_dir = os.path.join(
            self.data_dir, "googleapp-profiles"
        )

        for directory in (
            self.desktop_dir,
            self.bin_dir,
            self.icon_dir,
            self.profiles_dir,
        ):
            os.makedirs(directory, exist_ok=True)

        self.custom_apps = []
        self.checkboxes = []

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        title = QLabel("Google App & Web App Launcher Builder")
        title.setFont(QFont("Sans Serif", 12, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        description = QLabel(
            "Create independent Chrome app launchers.\n"
            "Each app has its own persistent browser profile."
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(description)

        browser_group = QGroupBox("Browser command")
        browser_layout = QVBoxLayout()

        browser_layout.addWidget(QLabel(
            "Flatpak example: flatpak run com.google.Chrome"
        ))

        self.browser_input = QLineEdit()
        self.browser_input.setText(self.detect_browser())
        browser_layout.addWidget(self.browser_input)

        browser_group.setLayout(browser_layout)
        main_layout.addWidget(browser_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        self.grid_layout = QGridLayout(scroll_content)

        for index, app_info in enumerate(DEFAULT_GOOGLE_APPS):
            checkbox = QCheckBox(app_info["name"])
            checkbox.setChecked(True)
            checkbox.setProperty("app_data", app_info)

            self.checkboxes.append(checkbox)
            self.grid_layout.addWidget(
                checkbox, index // 2, index % 2
            )

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        custom_group = QGroupBox("Custom web applications")
        custom_layout = QVBoxLayout()

        self.custom_list_label = QLabel(
            "No custom apps added yet."
        )
        self.custom_list_label.setWordWrap(True)
        custom_layout.addWidget(self.custom_list_label)

        add_button = QPushButton("Add Custom Web App")
        add_button.clicked.connect(self.add_custom_app_dialog)
        custom_layout.addWidget(add_button)

        custom_group.setLayout(custom_layout)
        main_layout.addWidget(custom_group)

        action_layout = QHBoxLayout()

        select_all = QPushButton("Select All")
        select_all.clicked.connect(
            lambda: self.set_all_checkboxes(True)
        )
        action_layout.addWidget(select_all)

        deselect_all = QPushButton("Deselect All")
        deselect_all.clicked.connect(
            lambda: self.set_all_checkboxes(False)
        )
        action_layout.addWidget(deselect_all)

        generate = QPushButton("Create Selected Applications")
        generate.setStyleSheet(
            "font-weight: bold; padding: 8px;"
        )
        generate.clicked.connect(self.generate_applications)
        action_layout.addWidget(generate)

        main_layout.addLayout(action_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

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
        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            value.lower()
        ).strip("-")

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
            self,
            "Custom App Name",
            "Enter application name:"
        )

        if not accepted or not name.strip():
            return

        url, accepted = QInputDialog.getText(
            self,
            "Custom App URL",
            "Enter URL (e.g. https://example.com):"
        )

        if not accepted or not url.strip():
            return

        url = url.strip()

        if "://" not in url:
            url = "https://" + url

        if not self.valid_url(url):
            QMessageBox.warning(
                self,
                "Invalid URL",
                "Enter a valid HTTP or HTTPS URL."
            )
            return

        slug = self.make_slug(name)

        if any(app["slug"] == slug for app in (
            DEFAULT_GOOGLE_APPS + self.custom_apps
        )):
            QMessageBox.warning(
                self,
                "Duplicate App",
                "An application with this slug already exists."
            )
            return

        self.custom_apps.append({
            "name": name.strip(),
            "slug": slug,
            "url": url,
        })

        self.custom_list_label.setText(
            "Added: " + ", ".join(
                app["name"] for app in self.custom_apps
            )
        )

    def resolve_and_install_icon(self, slug, url):
        icon_name = f"googleapp-{slug}"
        icon_path = os.path.join(
            self.icon_dir, icon_name + ".png"
        )

        try:
            domain = urlsplit(url).hostname

            if domain:
                icon_url = (
                    "https://www.google.com/s2/favicons"
                    f"?domain={domain}&sz=128"
                )

                response = requests.get(
                    icon_url, timeout=5
                )
                response.raise_for_status()

                # Avoid saving an HTML error page as an icon.
                if (
                    response.headers.get(
                        "content-type", ""
                    ).startswith("image/")
                ):
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
        if value and re.fullmatch(
            r"[A-Za-z0-9_./:=+-]+", value
        ):
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

        profile_dir = os.path.join(
            self.profiles_dir, launcher_id
        )
        os.makedirs(profile_dir, mode=0o700, exist_ok=True)
        os.chmod(profile_dir, 0o700)

        icon_name = self.resolve_and_install_icon(
            app_slug, url
        )

        # Each launcher invokes its own wrapper script.
        # shlex.join safely quotes arguments for the shell.
        browser_args = browser_parts + [
            f"--user-data-dir={profile_dir}",
            f"--class={launcher_id}",
            f"--app={url}",
        ]

        script_path = os.path.join(
            self.bin_dir, launcher_id + ".sh"
        )

        script_content = (
            "#!/bin/sh\n"
            "set -eu\n"
            "exec " + shlex.join(browser_args) + "\n"
        )

        with open(
            script_path, "w", encoding="utf-8"
        ) as script_file:
            script_file.write(script_content)

        os.chmod(script_path, 0o755)

        desktop_path = os.path.join(
            self.desktop_dir, launcher_id + ".desktop"
        )

        # The desktop entry calls the wrapper directly.
        exec_line = self.desktop_exec_arg(script_path)

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
Categories=Network;
"""

        with open(
            desktop_path, "w", encoding="utf-8"
        ) as desktop_file:
            desktop_file.write(desktop_content)

        os.chmod(desktop_path, 0o644)

    def generate_applications(self):
        browser_cmd = self.browser_input.text().strip()

        if not browser_cmd:
            QMessageBox.warning(
                self, "Warning",
                "Please specify a browser command."
            )
            return

        try:
            browser_parts = shlex.split(browser_cmd)
        except ValueError as error:
            QMessageBox.warning(
                self, "Invalid Command", str(error)
            )
            return

        if not browser_parts:
            QMessageBox.warning(
                self, "Warning",
                "The browser command is empty."
            )
            return

        # Verify the runner or executable exists.
        executable = browser_parts[0]
        if (
            os.path.sep in executable
            and not os.path.isfile(executable)
        ):
            QMessageBox.warning(
                self,
                "Browser Not Found",
                f"Executable does not exist:\n{executable}"
            )
            return

        if (
            os.path.sep not in executable
            and shutil.which(executable) is None
        ):
            QMessageBox.warning(
                self,
                "Browser Not Found",
                f"Command not found:\n{executable}"
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
                self, "Warning",
                "Select or add at least one application."
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

        if shutil.which("update-desktop-database"):
            subprocess.run(
                ["update-desktop-database", self.desktop_dir],
                capture_output=True,
                text=True,
            )

        if shutil.which("gtk-update-icon-cache"):
            subprocess.run(
                [
                    "gtk-update-icon-cache",
                    "-f", "-t",
                    os.path.expanduser(
                        "~/.local/share/icons/hicolor"
                    ),
                ],
                capture_output=True,
                text=True,
            )

        message = (
            f"Created {created} application launcher(s).\n\n"
            f"Desktop files:\n{self.desktop_dir}\n\n"
            f"Launcher scripts:\n{self.bin_dir}\n\n"
            f"Persistent profiles:\n{self.profiles_dir}\n\n"
            "Close existing app windows before testing "
            "the newly generated launchers."
        )

        if errors:
            message += "\n\nErrors:\n" + "\n".join(errors)

        QMessageBox.information(
            self, "Launcher Generation Complete", message
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GoogleAppCreator()
    window.show()
    sys.exit(app.exec())
