'''
overlay_timer.py

Displays a transparent always-on-top overlay window showing a hardcoded image or GIF at 50% size with a timer bar
and plays audio from a YouTube link selected at runtime via a setup dialog. The overlay window
is movable via click-&-drag, resizable, and includes pause & cancel functionality. After finishing or canceling,
it returns to the setup screen.

Dependencies:
    pip install PyQt5 python-vlc yt-dlp
Requires VLC installed on system.

Usage:
    - Modify IMAGE_PATH constant to your overlay image/GIF path.
    - Run: python overlay_timer.py
'''
import sys
import os
from PyQt5 import QtWidgets, QtCore, QtGui
import vlc
import yt_dlp

# === CONFIGURATION ===
IMAGE_PATH = 'sr2799489b00daws3.png'  # .png, .jpg, or .gif
FIXED_SCALE = 0.5  # always scale to 50%

class SetupDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Overlay Timer Setup')
        self.setFixedSize(400, 150)
        self.duration_input = QtWidgets.QLineEdit(self)
        self.duration_input.setPlaceholderText('Enter duration (secs)')
        self.url_input = QtWidgets.QLineEdit(self)
        self.url_input.setPlaceholderText('Enter YouTube URL')
        start_btn = QtWidgets.QPushButton('Start', self)
        start_btn.clicked.connect(self.accept)
        layout = QtWidgets.QFormLayout()
        layout.addRow('Duration (s):', self.duration_input)
        layout.addRow('YouTube URL:', self.url_input)
        layout.addRow(start_btn)
        self.setLayout(layout)

    def get_values(self):
        try:
            dur = int(self.duration_input.text())
        except:
            dur = 0
        return dur, self.url_input.text().strip()

class OverlayWindow(QtWidgets.QWidget):
    finished = QtCore.pyqtSignal()

    def __init__(self, path, duration, url):
        super().__init__()
        # Frameless, always-on-top transparent
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Load image or GIF
        self.is_gif = path.lower().endswith('.gif')
        if self.is_gif:
            self.movie = QtGui.QMovie(path)
            if not self.movie.isValid():
                raise ValueError(f"Invalid GIF: {path}")
            frame = self.movie.currentImage()
            w0, h0 = frame.width(), frame.height()
        else:
            pix = QtGui.QPixmap(path)
            if pix.isNull():
                raise FileNotFoundError(f"Image not found: {path}")
            w0, h0 = pix.width(), pix.height()
            self.original_pixmap = pix

        # Compute initial size
        self.init_w = int(w0 * FIXED_SCALE)
        self.init_h = int(h0 * FIXED_SCALE)
        self.ctrl_h = 100
        self.resize(self.init_w, self.init_h + self.ctrl_h)

        # Center window
        scr = QtWidgets.QApplication.primaryScreen().geometry()
        self.move((scr.width() - self.init_w)//2, (scr.height() - self.init_h)//2)

        # Label for image/GIF
        self.label = QtWidgets.QLabel(self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setGeometry(0, 0, self.init_w, self.init_h)
        if self.is_gif:
            self.movie.setScaledSize(QtCore.QSize(self.init_w, self.init_h))
            self.label.setMovie(self.movie)
        else:
            self.label.setPixmap(self.original_pixmap.scaled(
                self.init_w, self.init_h,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation))

        # Progress bar
        self.progress = QtWidgets.QProgressBar(self)
        self.progress.setRange(0, duration)
        self.progress.setValue(0)
        self.progress.setStyleSheet(
            "QProgressBar { background-color: rgba(255,255,255,120); color: white; font-size: 16px; }"
            "QProgressBar::chunk { background-color: rgba(0,150,0,180); }"
        )

        # Cancel button
        self.cancel_btn = QtWidgets.QPushButton('Cancel', self)
        self.cancel_btn.setFixedSize(140, 40)
        self.cancel_btn.setStyleSheet("font-size: 24px;")
        self.cancel_btn.clicked.connect(self._cancel)

        # Pause/resume button
        self.pause_btn = QtWidgets.QPushButton('Pause', self)
        self.pause_btn.setFixedSize(140, 40)
        self.pause_btn.setStyleSheet("font-size: 24px;")
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.paused = False

        # Resize grip
        self.grip = QtWidgets.QSizeGrip(self)
        self.grip.setFixedSize(30, 30)

        # Timer
        self.duration, self.elapsed = duration, 0
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

        # Audio via yt-dlp
        ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        self.player = vlc.MediaPlayer(info['url'])

        # Windows DLL
        if sys.platform.startswith('win'):
            os.add_dll_directory(r"C:\Program Files\VideoLAN\VLC")

        # Layout & start
        self._layout()

    def showEvent(self, event):
        super().showEvent(event)
        # start GIF and audio when visible
        if self.is_gif:
            self.movie.start()
        self.player.play()

    def _layout(self):
        w, h = self.width(), self.height()
        img_h = h - self.ctrl_h
        # scale image/GIF
        if self.is_gif:
            self.movie.setScaledSize(QtCore.QSize(w, img_h))
        else:
            scaled = self.original_pixmap.scaled(
                w, img_h,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation)
            self.label.setPixmap(scaled)
        self.label.setGeometry(0, 0, w, img_h)
        # progress bar
        self.progress.setGeometry(10, img_h + 10, w - 20, 40)
        # pause & cancel buttons
        gap = 20
        total_width = self.pause_btn.width() + gap + self.cancel_btn.width()
        x0 = (w - total_width) // 2
        y0 = img_h + 60
        self.pause_btn.move(x0, y0)
        self.cancel_btn.move(x0 + self.pause_btn.width() + gap, y0)
        # resize grip
        self.grip.move(w - self.grip.width(), h - self.grip.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self._drag)
            event.accept()

    def _tick(self):
        if not self.paused:
            self.elapsed += 1
            self.progress.setValue(self.elapsed)
            if self.elapsed >= self.duration:
                self._finish()

    def _toggle_pause(self):
        if not self.paused:
            # pause everything
            self.timer.stop()
            self.player.pause()
            if self.is_gif:
                self.movie.setPaused(True)
            self.pause_btn.setText('Resume')
            self.paused = True
        else:
            # resume
            self.timer.start(1000)
            self.player.play()
            if self.is_gif:
                self.movie.setPaused(False)
            self.pause_btn.setText('Pause')
            self.paused = False

    def _cancel(self):
        self.timer.stop()
        self.player.stop()
        if self.is_gif:
            self.movie.stop()
        self._finish()

    def _finish(self):
        # ensure stopped
        try: self.timer.stop()
        except: pass
        try: self.player.stop()
        except: pass
        if self.is_gif:
            try: self.movie.stop()
            except: pass
        self.close()
        self.finished.emit()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    overlays = []
    def start_cycle():
        dlg = SetupDialog()
        if dlg.exec_():
            dur, url = dlg.get_values()
            if dur > 0 and url:
                ow = OverlayWindow(IMAGE_PATH, dur, url)
                ow.finished.connect(start_cycle)
                ow.show(); ow.raise_(); ow.activateWindow()
                overlays[:] = [ow]
        else:
            app.quit()
    QtCore.QTimer.singleShot(0, start_cycle)
    sys.exit(app.exec_())
