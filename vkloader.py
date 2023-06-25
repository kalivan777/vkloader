import sys
import os
import vk_api
import requests
import PyQt5
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QAction
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
app = QApplication(sys.argv)
# Установка иконки приложения
app_icon = QIcon(r'C:\Users\иван\Downloads\vkloader\Icon.png')
# Класс потока для загрузки аудиозаписей
class DownloadMusicThread(QThread):
    downloadProgress = pyqtSignal(int)

    def __init__(self, parent=None):
        super(DownloadMusicThread, self).__init__(parent)
        self.credentials = None
        self.playlist_id = None
        self.audio_ids = []
        self.download_dir = None

    def set_credentials(self, login, password):
        self.credentials = (login, password)

    def set_playlist_id(self, playlist_id):
        self.playlist_id = playlist_id

    def set_audio_ids(self, audio_ids):
        self.audio_ids = audio_ids

    def set_download_dir(self, download_dir):
        self.download_dir = download_dir

    def run(self):
        vk_session = vk_api.VkApi(*self.credentials)
        vk_session.auth()
        vk = vk_session.get_api()

        if self.playlist_id is not None:
            audios = vk.audio.get(owner_id=self.credentials[0], playlist_id=self.playlist_id)
            audio_ids = [audio['id'] for audio in audios['items']]
            self.audio_ids = audio_ids

        num_audios = len(self.audio_ids)
        for i, audio_id in enumerate(self.audio_ids):
            try:
                audio = vk.audio.getById(audio_id=audio_id)[0]
                audio_url = audio['url']
                artist = audio['artist'].replace('/', '_')
                title = audio['title'].replace('/', '_')
                filename = "{} - {}.mp3".format(artist, title)
                filepath = os.path.join(self.download_dir, filename)

                response = requests.get(audio_url, stream=True)
                with open(filepath, "wb") as audio_file:
                    for chunk in response.iter_content(chunk_size=1024):
                        audio_file.write(chunk)

                progress = int((i + 1) / num_audios * 100)
                self.downloadProgress.emit(progress)
            except Exception as e:
              print("Error downloading audio %s: %s" % (audio_id, e))

# Класс главного окна
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('VK Music Downloader')
        self.setWindowIcon(app_icon)
        self.setFixedSize(400, 300)

        # Окно ввода логина и пароля
        login_label = QAction('Логин:', self)
        font = QFont()
        font.setPointSize(10)
        login_label.setFont(font)
        login_label.setDisabled(True)
        self.addToolBarBreak()
        self.toolbar = self.addToolBar('Вход')
        self.toolbar.addAction(login_label)
        self.login_edit = self.toolbar.addLineEdit()
        password_label = QAction('Пароль:', self)
        password_label.setFont(font)
        password_label.setDisabled(True)
        self.toolbar.addAction(password_label)
        self.password_edit = self.toolbar.addLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.toolbar.addAction('Войти', self.login_check)

        # Окно для выбора плейлиста или конкретных аудиозаписей
        download_label = QAction('Из плейлиста:', self)
        download_label.setFont(font)
        download_label.setDisabled(True)
        self.addToolBarBreak()
        self.toolbar = self.addToolBar('Загрузка')
        self.toolbar.addAction(download_label)
        self.playlist_radio = self.toolbar.addRadioButton('Плейлист')
        self.playlist_radio.toggled.connect(self.toggle_playlist_field)
        self.playlist_field = self.toolbar.addComboBox()
        self.playlist_field.setDisabled(True)
        self.toolbar.addAction('Обзор...', self.open_file_dialog)
        self.audios_radio = self.toolbar.addRadioButton('Аудиозаписи')
        self.audios_radio.toggled.connect(self.toggle_audios_field)
        self.audios_field = self.toolbar.addLineEdit()
        self.audios_field.setDisabled(True)

        # Окно для выбора директории загрузки
        folder_label = QAction('Сохранять в:', self)
        folder_label.setFont(font)
        folder_label.setDisabled(True)
        self.addToolBarBreak()
        self.toolbar = self.addToolBar('Сохранение')
        self.toolbar.addAction(folder_label)
        self.folder_edit = self.toolbar.addLineEdit()
        self.toolbar.addAction('Обзор...', self.open_dir_dialog)

        # Кнопка начала загрузки
        self.addToolBarBreak()
        self.toolbar = self.addToolBar('Начало загрузки')
        self.download_button = self.toolbar.addAction('Загрузить')
        self.download_button.setDisabled(True)
        self.download_button.triggered.connect(self.start_download)

        # Связывание потока загрузки музыки с сигналами главного окна
        self.download_thread = DownloadMusicThread()
        self.download_thread.downloadProgress.connect(self.update_progress)

    # Проверка корректности логина и пароля
    def login_check(self):
        login = self.login_edit.text().strip()
        password = self.password_edit.text().strip()
        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Введите логин и пароль')
            return
        self.download_button.setEnabled(False)
        self.playlist_field.clear()
        try:
            vk_session = vk_api.VkApi(login, password)
            vk_session.auth()
            vk = vk_session.get_api()
            playlists = vk.audio.getPlaylists()
            for playlist in playlists['items']:
                self.playlist_field.addItem(playlist['title'], playlist['id'])
        except vk_api.AuthError:
            QMessageBox.warning(self, 'Ошибка', 'Не удалось авторизоваться')
            return
        self.playlist_field.setEnabled(True)
        self.download_button.setEnabled(True)

    # Переключение между выбором плейлиста и конкретных аудиозаписей
    def toggle_playlist_field(self, checked):
        self.playlist_field.setEnabled(checked)
        self.audios_field.setDisabled(checked)

    def toggle_audios_field(self, checked):
        self.audios_field.setEnabled(checked)
        self.playlist_field.setDisabled(checked)

    # Открытие диалога выбора плейлиста или файлов с аудиозаписями для загрузки
    def open_file_dialog(self):
        if self.playlist_radio.isChecked():
            self.playlist_field.showPopup()
        else:
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            filenames, _ = QFileDialog.getOpenFileNames(self, "Выбрать аудиозаписи для загрузки", "",
                                                        "Аудио файлы (*.mp3);;Все файлы (*)", options=options)
            if filenames:
                self.audios_field.setText("\n".join(filenames))

    # Открытие диалога выбора директории для сохранения файлов
    def open_dir_dialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        foldername = QFileDialog.getExistingDirectory(self, "Выбрать директорию для сохранения", options=options)
        if foldername:
            self.folder_edit.setText(foldername)

    # Запуск загрузки музыки
    def start_download(self):
        login = self.login_edit.text().strip()
        password = self.password_edit.text().strip()
        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Введите логин и пароль')
            return

        if self.download_thread.isRunning():
            QMessageBox.warning(self, 'Ошибка', 'Загрузка уже запущена')
            return

        self.download_thread.set_credentials(login, password)

        if self.playlist_radio.isChecked():
            playlist_index = self.playlist_field.currentIndex()
            if playlist_index >= 0:
                playlist_id = self.playlist_field.itemData(playlist_index)
                self.download_thread.set_playlist_id(playlist_id)
        else:
            audio_ids = [audio_id.strip() for audio_id in self.audios_field.toPlainText().split('\n')]
            self.download_thread.set_audio_ids(audio_ids)

        download_dir = self.folder_edit.text().strip()
        if not download_dir:
            QMessageBox.warning(self, 'Ошибка', 'Выберите директорию для сохранения')
            return
        self.download_thread.set_download_dir(download_dir)

        self.download_thread.start()

    # Обновление индикатора загрузки
    def update_progress(self, progress):
       self.statusBar().showMessage("Загружено %s%%" % progress)
       if progress >= 100:
            QMessageBox.information(self, 'Загрузка завершена', 'Файлы успешно загружены')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationDisplayName('VKloader')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
