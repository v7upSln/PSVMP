import sys
import os
import threading
import time
import webbrowser
import html
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QRadioButton, QButtonGroup, QMessageBox,
    QSplitter, QStyleFactory
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCursor, QIcon

# --- Optional modern theming lib (recommended) ---
_HAS_QDT = False
try:
    import qdarktheme
    _HAS_QDT = True
except Exception:
    _HAS_QDT = False

# Import core logic
import psmedia as core

try:
    from VERSION import VERSION as APP_VERSION
except Exception:
    APP_VERSION = "unknown"

APP_NAME = "PSVMP – PS Vita Media Processor"
GITHUB_URL = "https://github.com/v7upSln/PSVMP"


class LogStream(QObject):
    new_text = pyqtSignal(str, bool)

    def __init__(self, is_error=False):
        super().__init__()
        self.is_error = is_error

    def write(self, text):
        if text:
            self.new_text.emit(text, self.is_error)

    def flush(self):
        pass


class PSVitaMediaGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setGeometry(160, 90, 980, 620)


        # Set window logo
        logo_path = os.path.join("imgs", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))

        self.theme = "dark"
        self.colors = {}

        # Widgets
        self.url_input = QLineEdit()
        paste_btn = QPushButton("Paste")
        paste_btn.clicked.connect(self.paste_from_clipboard)

        self.video_radio = QRadioButton("Video")
        self.music_radio = QRadioButton("Music")
        self.video_radio.setChecked(True)
        media_group = QButtonGroup()
        media_group.addButton(self.video_radio)
        media_group.addButton(self.music_radio)

        self.ip_input = QLineEdit(getattr(core, "DEFAULT_VITA_IP", "192.168.1.7"))
        self.ip_input.setMinimumWidth(180)
        self.port_input = QLineEdit(str(getattr(core, "DEFAULT_VITA_PORT", 1337)))
        self.port_input.setMaximumWidth(110)

        self.process_btn = QPushButton("Process Media")
        self.process_btn.clicked.connect(self.start_pipeline)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.request_stop)

        open_folder_btn = QPushButton("Open Output Folder")
        open_folder_btn.clicked.connect(self.open_output_folder)

        delete_files_btn = QPushButton("Delete All Files")
        delete_files_btn.setStyleSheet("QPushButton { background-color: #E84535; color: white; font-weight: bold; }")
        delete_files_btn.clicked.connect(self.delete_all_files)

        github_btn = QPushButton("GitHub")
        github_btn.clicked.connect(lambda: webbrowser.open(GITHUB_URL))

        theme_btn = QPushButton("Toggle Theme")
        theme_btn.clicked.connect(self.toggle_theme)

        clear_console_btn = QPushButton("Clear Console")
        clear_console_btn.clicked.connect(self.clear_console)
        
        check_update_btn = QPushButton("Check for Updates")
        check_update_btn.clicked.connect(self.check_updates)

        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setAcceptRichText(True)

        # --- Layout ---
        main_layout = QVBoxLayout()

        # Top bar
        top_bar = QHBoxLayout()
        title_lbl = QLabel(f"{APP_NAME}")
        top_bar.addWidget(title_lbl)
        top_bar.addStretch()
        top_bar.addWidget(theme_btn)
        top_bar.addWidget(clear_console_btn)
        top_bar.addWidget(github_btn)
        top_bar.addWidget(check_update_btn)

        # URL row
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("Media URL:"))
        url_row.addWidget(self.url_input)
        url_row.addWidget(paste_btn)

        # Media type row
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        type_row.addWidget(self.video_radio)
        type_row.addWidget(self.music_radio)
        type_row.addStretch()

        # IP/Port row (aligned compact)
        ip_row = QHBoxLayout()
        ip_row.addWidget(QLabel("Vita IP:"))
        ip_row.addWidget(self.ip_input)
        ip_row.addSpacing(10)
        ip_row.addWidget(QLabel("Port:"))
        ip_row.addWidget(self.port_input)
        ip_row.addStretch()

        # Actions row
        action_row = QHBoxLayout()
        action_row.addWidget(self.process_btn)
        action_row.addWidget(self.stop_btn)
        action_row.addStretch()
        action_row.addWidget(open_folder_btn)
        action_row.addWidget(delete_files_btn)

        # Console area with splitter (future-proof if you add side panels)
        splitter = QSplitter(Qt.Orientation.Vertical)
        console_container = QWidget()
        clayout = QVBoxLayout()
        clayout.addWidget(QLabel("Console (verbose)"))
        clayout.addWidget(self.console)
        console_container.setLayout(clayout)
        splitter.addWidget(console_container)

        main_layout.addLayout(top_bar)
        main_layout.addLayout(url_row)
        main_layout.addLayout(type_row)
        main_layout.addLayout(ip_row)
        main_layout.addLayout(action_row)
        main_layout.addWidget(splitter, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Logging redirection
        self.stop_flag = threading.Event()
        self.stdout_stream = LogStream(False)
        self.stderr_stream = LogStream(True)
        self.stdout_stream.new_text.connect(self.append_log)
        self.stderr_stream.new_text.connect(self.append_log)
        sys.stdout = self.stdout_stream
        sys.stderr = self.stderr_stream

        # Apply theme + banner
        self.apply_theme(force_qdarktheme=True)
        self.print_banner()

    # Check updates
    def check_updates(self):
        import updater  # or wherever you put the function
        result, info = updater.check_for_update()

        if result is True:
            QMessageBox.information(
                self,
                "Update Available",
                f"A new version {info} is available!\n"
                "Visit PyPI or GitHub to update."
            )
            webbrowser.open("https://pypi.org/project/psvmp/")
        elif result is False:
            QMessageBox.information(
                self,
                "Up to Date",
                f"You are running the latest version ({APP_VERSION})."
            )
        else:
            QMessageBox.warning(
                self,
                "Update Check Failed",
                f"Could not check for updates:\n{info}"
            )

    def delete_all_files(self):
        from PyQt6.QtWidgets import QMessageBox
        import shutil

        docs_dir = getattr(core, "BASE_DOCS_DIR", os.path.join(os.path.expanduser("~"), "Documents", "PSvita media processer"))

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete ALL files in:\n{docs_dir}\n\nThis cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Delete contents of temp and converted
                for folder in [core.TEMP_FOLDER, core.CONVERTED_FOLDER]:
                    if os.path.exists(folder):
                        for filename in os.listdir(folder):
                            file_path = os.path.join(folder, filename)
                            try:
                                if os.path.isfile(file_path) or os.path.islink(file_path):
                                    os.remove(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                            except Exception as e:
                                print(f"Error deleting {file_path}: {e}")

                QMessageBox.information(self, "Deleted", "All files have been deleted.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete files:\n{e}")


    # --- Theme ---
    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.apply_theme()
        # Re-print banner after theme switch so it matches new colors
        self.print_banner()

    def apply_theme(self, force_qdarktheme=False):
        """Apply custom palettes for dark and light modes."""
        app = QApplication.instance()
        app.setStyle("Fusion")

        if self.theme == "dark":
            self.colors = {
                "bg": "#0D0D0D",          # Deep Black
                "panel_bg": "#1A1A1A",    # Charcoal Black
                "text": "#DEDEDE",        # Light Gray
                "error": "#FF6B6B",
                "timestamp": "#9AA7B2",
                "stream_out": "#00BFFF",  # Deep Blue
                "stream_err": "#FF7B83",
                "border": "#2A2A2A",
                "primary": "#00BFFF",     # PlayStation wave blue
            }
        else:
            self.colors = {
                "bg": "#F8F8F8",          # Soft Off-White
                "panel_bg": "#E5E5E5",    # Light Gray
                "text": "#333333",        # Dark Gray
                "error": "#C62828",
                "timestamp": "#607D8B",
                "stream_out": "#0088CC",  # Aqua Blue
                "stream_err": "#D32F2F",
                "border": "#CCCCCC",
                "primary": "#0088CC",     # Vita-inspired Aqua Blue
            }

        common_css = f"""
        QWidget {{
            font-family: 'Segoe UI', 'Inter', 'Arial';
            font-size: 11pt;
            background: {self.colors['bg']};
            color: {self.colors['text']};
        }}
        QLineEdit {{
            padding: 8px 10px; border-radius: 10px;
            background: {self.colors['panel_bg']};
            border: 1px solid {self.colors['border']};
            color: {self.colors['text']};
        }}
        QPushButton {{
            padding: 10px 14px; border-radius: 12px; border: 1px solid {self.colors['border']};
            background: {self.colors['panel_bg']}; color: {self.colors['text']};
        }}
        QPushButton:hover {{
            border-color: {self.colors['primary']};
        }}
        QPushButton:pressed {{
            background: {self.colors['primary']}; color: #ffffff;
        }}
        QTextEdit {{
            background: {self.colors['panel_bg']}; color: {self.colors['text']};
            border: 1px solid {self.colors['border']}; border-radius: 12px; padding: 8px;
        }}
        """
        self.setStyleSheet(common_css)

        # Primary button accent
        self.process_btn.setStyleSheet(self.styleSheet() + f"""
        QPushButton {{ background: {self.colors['primary']}; color: #ffffff; border: none; }}
        QPushButton:hover {{ opacity: 0.9; }}
        """)

    # --- Helpers ---
    def paste_from_clipboard(self):
        self.url_input.setText(QApplication.clipboard().text())

    def clear_console(self):
        self.console.clear()
        self.print_banner()

    def _escape_html(self, s: str) -> str:
        return html.escape(s, quote=True)

    def append_log(self, text, is_error):
        for raw in text.splitlines(True):
            if raw == "\n":
                self.console.append("")
                continue
            ts = time.strftime("%H:%M:%S")
            stream_color = self.colors["stream_err" if is_error else "stream_out"]
            text_color = self.colors["error" if is_error else "text"]
            html_line = (
                f"<span style='color:{self.colors['timestamp']}'>[{ts}]</span> "
                f"<span style='color:{stream_color}'>[{ 'STDERR' if is_error else 'STDOUT' }]</span> "
                f"<span style='color:{text_color}'>{self._escape_html(raw).rstrip()}</span>"
            )
            self.console.append(html_line)
        self.console.moveCursor(QTextCursor.MoveOperation.End)

    def print_banner(self):
        banner = (
            f"{APP_NAME} v{APP_VERSION}\n"
            f"GitHub: {GITHUB_URL}\n"
            f"Ready. Select type, paste a URL, and click Process.\n"
        )
        self.append_log(banner, is_error=False)

    def request_stop(self):
        self.stop_flag.set()
        self.append_log("Stop requested…\n", True)

    def open_output_folder(self):
        out_dir = getattr(core, "CONVERTED_FOLDER")
        os.makedirs(out_dir, exist_ok=True)

        if sys.platform.startswith("win"):
            os.startfile(out_dir)  # Windows
        elif sys.platform == "darwin":
            os.system(f"open '{out_dir}'")  # macOS
        else:
            os.system(f"xdg-open '{out_dir}' 2>/dev/null || sensible-browser '{out_dir}' 2>/dev/null || true")

    # --- Worker ---
    def start_pipeline(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a media URL")
            return
        try:
            port = int(self.port_input.text())
        except ValueError:
            QMessageBox.critical(self, "Invalid Port", "Port must be a number")
            return

        ip = self.ip_input.text().strip()
        media_type = "music" if self.music_radio.isChecked() else "video"

        self.stop_flag.clear()
        self.process_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        threading.Thread(target=self.run_pipeline, args=(url, ip, port, media_type), daemon=True).start()

    def run_pipeline(self, url, ip, port, media_type):
        try:
            print("Checking dependencies…")
            if not core.check_dependencies():
                raise RuntimeError("Missing dependencies.")

            if self.stop_flag.is_set():
                raise RuntimeError("Stopped by user before download.")

            downloaded_file = core.download_media(url, media_type)
            print(f"Downloaded: {downloaded_file}")

            if self.stop_flag.is_set():
                raise RuntimeError("Stopped by user before conversion.")

            out_dir = getattr(core, "CONVERTED_FOLDER", "psvita_converted")
            os.makedirs(out_dir, exist_ok=True)

            base = os.path.splitext(os.path.basename(downloaded_file))[0]
            base = core.sanitize_filename(base)

            if media_type == "music":
                out_name = base + ".mp3"
                convert_fn = core.convert_for_vita_music
                vita_path = getattr(core, "VITA_MUSIC_PATH", "ux0:/music/")
            else:
                out_name = base + "_psvita.mp4"
                convert_fn = core.convert_for_vita_video
                vita_path = getattr(core, "VITA_VIDEO_PATH", "ux0:/video/shows/")

            converted_file = convert_fn(downloaded_file, os.path.join(out_dir, out_name))
            print(f"Converted: {converted_file}")

            if self.stop_flag.is_set():
                raise RuntimeError("Stopped by user before transfer.")

            ftp = core.VitaFTP(ip, port)
            remote_path = f"{vita_path}{os.path.basename(converted_file)}"
            ftp.transfer(converted_file, remote_path, progress_callback=lambda msg: print(msg))
            print("SUCCESS: File transferred to PS Vita.")
        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            self.process_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = PSVitaMediaGUI()
    gui.show()
    sys.exit(app.exec())