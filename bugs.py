from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, Qt, QTimer 
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QLabel, QListWidget, QLineEdit, QDialog, QPushButton, QHBoxLayout, QVBoxLayout, QApplication, QListWidgetItem, QTextEdit, QFileDialog
from bs4 import BeautifulSoup
import requests
import yt_dlp
import eyed3
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib import request
from webdriver_manager.chrome import ChromeDriverManager
import webbrowser
from PIL import Image
import re
from pathlib import Path
import sys, json, urllib.request, importlib.metadata

search_title = ""
music_source = ""
music_meta_data_list = []
target_index = 0

_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*]')

def ensure_latest_yt_dlp():
    try:
        with urllib.request.urlopen("https://pypi.org/pypi/yt-dlp/json", timeout=5) as r:
            latest = json.load(r)["info"]["version"]
    except Exception as e:
        return

    current = importlib.metadata.version("yt-dlp")

    if current == latest:
        return f"yt‑dlp 최신 버전 사용 중 ({current})"
    else:
        return f"※ yt‑dlp 구버전 사용 중 ({current} → {latest}) 사용시 문제가 발생할 수 있습니다."

class MyMainGUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_button = QPushButton("음악 검색")
        self.github_button = QPushButton("Github")
        
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("검색어를 입력하세요.")

        self.music_source = QLineEdit(self)
        self.music_source.setPlaceholderText("유튜브 링크를 입력하세요. (옵션)")

        self.music_list = QListWidget(self)
        self.music_list.setIconSize(QSize(50, 50))
        self.music_list.setFixedSize(800, 600)

        self.status_label = QLabel("", self)
        self.youtube_button = QPushButton("음원 다운로드")

        self.edit_title  = QLineEdit(self)
        self.edit_title.setPlaceholderText("제목")
        self.edit_artist = QLineEdit(self)
        self.edit_artist.setPlaceholderText("아티스트")
        self.edit_album  = QLineEdit(self)
        self.edit_album.setPlaceholderText("앨범")

        self.cover_preview = QLabel(self)
        self.cover_preview.setFixedSize(200, 200)
        self.cover_preview.setStyleSheet("border:1px solid lightgray;")

        self.cover_button = QPushButton("커버 선택")

        self.lyric_edit = QTextEdit(self)
        self.lyric_edit.setPlaceholderText("가사를 입력하세요.")
        self.lyric_edit.setFixedSize(200, 200)
        self.lyric_edit.setStyleSheet("border:1px solid lightgray;")

        edit_vbox = QVBoxLayout()
        edit_vbox.addWidget(QLabel("곡 정보 편집"))
        edit_vbox.addWidget(self.edit_title)
        edit_vbox.addWidget(self.edit_artist)
        edit_vbox.addWidget(self.edit_album)
        edit_vbox.addWidget(self.cover_preview)
        edit_vbox.addWidget(self.cover_button)
        edit_vbox.addWidget(self.lyric_edit)
        edit_vbox.addStretch(1)

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.search_input)
        hbox.addWidget(self.search_button)
        hbox.addWidget(self.github_button)
        hbox.addStretch(1)

        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.music_source)

        hbox3 = QHBoxLayout()
        hbox3.addWidget(self.music_list, stretch=3)
        hbox3.addLayout(edit_vbox, stretch=2)

        hbox4 = QHBoxLayout()
        hbox4.addWidget(self.youtube_button)

        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        vbox.addLayout(hbox3)
        vbox.addStretch(1)
        vbox.addLayout(hbox4)
        vbox.addStretch(1)
        vbox.addWidget(self.status_label)

        self.setLayout(vbox)

        self.setWindowTitle('Bugs Downloader (v2.0)')
        self.setGeometry(300, 300, 800, 600)

        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)


class MyMain(MyMainGUI):
    add_sec_signal = pyqtSignal()
    send_instance_singal = pyqtSignal("PyQt_PyObject")

    def __init__(self, parent=None):
        super().__init__(parent)

        msg = ensure_latest_yt_dlp()
        if msg:
            self.status_update(msg)

        self.search_button.clicked.connect(self.search)
        self.youtube_button.clicked.connect(self.download)
        self.github_button.clicked.connect(lambda: webbrowser.open('https://github.com/Hydragon516/Bugs-Music-Downloader'))

        self.search_input.textChanged[str].connect(self.title_update)
        self.music_list.itemClicked.connect(self.chkItemClicked)
        self.music_list.itemClicked.connect(self.fill_edit_fields)
        self.music_source.textChanged[str].connect(self.source_update)

        self.cover_button.clicked.connect(self.choose_cover)

        self.th_search = searcher(parent=self)
        self.th_search.updated_list.connect(self.list_update)
        self.th_search.updated_label.connect(self.status_update)

        self.th_download = downloadr(parent=self)
        self.th_download.updated_label.connect(self.status_update)

        self.lyric_edit.textChanged.connect(self.queue_lyric_autosave)
        self._save_timer_ms = 700
        self._lyric_timer = QTimer(self)
        self._lyric_timer.setSingleShot(True)
        self._lyric_timer.timeout.connect(self.autosave_lyric)

        self.show()
    
    def title_update(self, input):
        global search_title
        search_title = input

    def source_update(self, input):
        global music_source
        music_source = input
    
    def chkItemClicked(self):
        global target_index
        
        # remove all modified files
        for file in os.listdir("./lyric"):
            if file.endswith("_modified.txt"):
                os.remove(f"./lyric/{file}")
        for file in os.listdir("./cover"):
            if file.endswith("_modified.jpg"):
                os.remove(f"./cover/{file}")

        target_index = self.music_list.currentRow()

    @pyqtSlot()
    def search(self):
        self.music_list.clear()
        self.th_search.start()

    @pyqtSlot()
    def download(self):
        self.th_download.start()

    @pyqtSlot(str, str, str, str)
    def list_update(self, idx, title, artist, album):
        global music_meta_data_list

        meta_data = {}
        meta_data["idx"] = idx
        meta_data["title"] = title
        meta_data["artist"] = artist
        meta_data["album"] = album

        music_meta_data_list.append(meta_data)

        display = f"{title}  —  {artist}  ({album})"
        item = QListWidgetItem(display)

        cover_path = f"./cover/{idx}.jpg"
        lyric_path = f"./lyric/{idx}.txt"

        if os.path.exists(cover_path):
            item.setIcon(QIcon(cover_path))

        item.setData(Qt.UserRole, [title, artist, album, cover_path, lyric_path])
        self.music_list.addItem(item)

    def choose_cover(self):
        current_idx = self.music_list.currentRow()
        item = self.music_list.currentItem()
        if not item:
            return
        file, _ = QFileDialog.getOpenFileName(self, "커버 이미지 선택", "", "Images (*.png *.jpg *.jpeg)")
        if file:
            cover_img = Image.open(file)

            if cover_img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", cover_img.size, (255, 255, 255))
                bg.paste(cover_img, mask=cover_img.split()[-1])
                cover_img = bg
            else:
                cover_img = cover_img.convert("RGB")
            # center crop
            width, height = cover_img.size
            crop_size = min(width, height)
            cover_img = cover_img.crop((0, 0, crop_size, crop_size))
            cover_img.save(f"./cover/{current_idx + 1}_modified.jpg", "JPEG")
            self.set_preview(f"./cover/{current_idx + 1}_modified.jpg")
            
    
    def fill_edit_fields(self, item):
        title, artist, album, cover_path, lyric_path = item.data(Qt.UserRole)
        self.edit_title.setText(title)
        self.edit_artist.setText(artist)
        self.edit_album.setText(album)
        self.set_preview(cover_path)

        mod_path = lyric_path.replace(".txt", "_modified.txt")
        path_to_open = mod_path if os.path.exists(mod_path) else lyric_path
        try:
            with open(path_to_open, "r", encoding="utf-8") as f:
                self.lyric_edit.setPlainText(f.read())
        except FileNotFoundError:
            self.lyric_edit.setPlainText("가사 파일이 없습니다.")


    def set_preview(self, path):
        pix = QPixmap(path).scaled(self.cover_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.cover_preview.setPixmap(pix)
    
    @pyqtSlot(str)
    def status_update(self, msg):
        self.status_label.setText(msg)
    
    def queue_lyric_autosave(self):
        if target_index < 0:
            return
        self._lyric_timer.start(self._save_timer_ms)
    
    def autosave_lyric(self):
        if target_index < 0:
            return
        modified_path = f"./lyric/{target_index + 1}_modified.txt"
        try:
            with open(modified_path, "w", encoding="utf-8") as f:
                f.write(self.lyric_edit.toPlainText())
            self.status_update(f"가사 자동 저장 완료 → {os.path.basename(modified_path)}")
        except Exception as e:
            self.status_update(f"가사 저장 실패: {e}")


class searcher(QThread):
    updated_list = pyqtSignal(str, str, str, str)
    updated_label = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()

    def run(self):
        global search_title
        global music_source
        global keyword

        title_list = []
        artist_list = []
        album_list = []
        
        if search_title != "":
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument("--disable-gpu")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_argument('--log-level=3')
            
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            self.updated_label.emit("서버에 접속하는 중...")

            driver.get(url='https://music.bugs.co.kr/search/track?q=' + search_title)

            if not os.path.exists("./cover"):
                os.makedirs("./cover")
            else:
                for file in os.listdir("./cover"):
                    os.remove("./cover/{}".format(file))
            
            if not os.path.exists("./lyric"):
                os.makedirs("./lyric")
            else:
                for file in os.listdir("./lyric"):
                    os.remove("./lyric/{}".format(file))

            self.updated_label.emit("제목 정보를 불러오는 중...")

            for indx in range(30):
                try:
                    target = driver.find_element(By.XPATH, '//*[@id="DEFAULT0"]/table/tbody/tr[{}]/th/p/a'.format(indx + 1))
                    title_list.append(target.get_attribute("title"))
                except:
                    break
            
            self.updated_label.emit("아티스트 정보를 불러오는 중...")
            
            for indx in range(30):
                try:
                    target = driver.find_element(By.XPATH,'//*[@id="DEFAULT0"]/table/tbody/tr[{}]/td[4]/p/a'.format(indx + 1))
                    artist_list.append(target.get_attribute("title"))
                except:
                    break
            
            self.updated_label.emit("앨범 정보를 불러오는 중...")
            
            for indx in range(30):
                try:
                    target = driver.find_element(By.XPATH,'//*[@id="DEFAULT0"]/table/tbody/tr[{}]/td[5]/a'.format(indx + 1))
                    album_list.append(target.get_attribute("title"))
                except:
                    break

            for indx in range(30):
                self.updated_label.emit(f"커버 이미지 불러오는 중... {indx + 1}/30")
                try:
                    album_a = driver.find_element(
                        By.XPATH, f'//*[@id="DEFAULT0"]/table/tbody/tr[{indx + 1}]/td[5]/a'
                    )
                    album_id = album_a.get_attribute("href").split("/album/")[1].split("?")[0]

                    hi_url = f"https://image.bugsm.co.kr/album/images/original/{album_id[:-2]}/{album_id}.jpg"
                    request.urlretrieve(hi_url, f"./cover/{indx + 1}.jpg")

                except Exception:
                    break

            for idx in range(30):
                try:
                    self.updated_label.emit(f"가사 가져오는 중... {idx + 1}/30")
                    track_a = driver.find_element(
                        By.XPATH, f'//*[@id="DEFAULT0"]/table/tbody/tr[{idx+1}]/td[3]/a'
                    )
                    track_url = track_a.get_attribute("href")

                    html = requests.get(track_url, timeout=5)
                    soup = BeautifulSoup(html.text, "html.parser")

                    lyrics_div = soup.find("div", class_="lyricsContainer")
                    if lyrics_div:
                        lyrics_text = (
                            lyrics_div.get_text("\n", strip=True)
                            .replace("\r", "")
                            .replace("\xa0", " ")
                        )
                    else:
                        lyrics_text = ""

                    with open(f"./lyric/{idx + 1}.txt", "w", encoding="utf-8") as f:
                        f.write(lyrics_text)

                except Exception:
                    break

            driver.close()

            try:
                for i in range(len(artist_list)):
                    self.updated_list.emit(str(i + 1), title_list[i], artist_list[i], album_list[i])
            except:
                pass

            self.updated_label.emit("불러오기 완료!")
        
        else:
            self.updated_label.emit("검색어를 입력하세요")


class downloadr(QThread):
    updated_label = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()

    def sanitize_filename(self, name: str, replacement: str = "_") -> str:
        safe = _INVALID_CHARS_RE.sub(replacement, name)
        safe = safe.rstrip(" .")
        stem, suffix = Path(safe).stem, Path(safe).suffix
        if stem.upper() in _RESERVED_NAMES:
            stem += "_"
        if not stem:
            stem = "untitled"
        return f"{stem}{suffix}"

    def run(self):
        global music_source
        global target_index

        target_title = self.main.edit_title.text()
        target_artist = self.main.edit_artist.text()
        target_album = self.main.edit_album.text()

        if music_source != "":
            if "www.youtube.com" not in music_source:
                self.updated_label.emit("정확한 유튜브 링크를 입력하세요")
                return

        url_list = []
        new_name = target_title + "_" + target_artist
        new_name = new_name.replace("/", "_")
        new_name = self.sanitize_filename(new_name)
        
        if music_source == "":
            self.updated_label.emit("자동 모드로 음원 파일을 검색하는 중 ...")

            surch_keyword = target_title + " " + target_artist + " 음원"

            url = 'https://www.youtube.com/results?search_query={}'.format(surch_keyword)

            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--window-size=1024,768')
            options.add_argument("--disable-gpu")

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            driver.get(url)

            for item in range(50):
                page = driver.find_element(By.TAG_NAME, 'html')
                page.send_keys(Keys.END)

            content = driver.page_source.encode('utf-8').strip()
            soup = BeautifulSoup(content, 'html.parser')

            for link in soup.findAll('a', id='video-title'):
                url_list.append('https://www.youtube.com' + link.get('href'))

            driver.close()

        else:
            self.updated_label.emit("수동 모드로 음원 파일을 검색하는 중 ...")
            url_list.append(music_source)

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': './{}'.format(new_name)
        }

        self.updated_label.emit("음원 다운로드 중 입니다...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_list[0]])

        self.updated_label.emit("파일 변환 중 입니다...")

        if os.path.exists(f"./lyric/{target_index + 1}_modified.txt"):
            OpenLyircsFile = open(f"./lyric/{target_index + 1}_modified.txt", 'r', encoding='UTF8') 
        else:
            OpenLyircsFile = open(f"./lyric/{target_index + 1}.txt", 'r', encoding='UTF8') 
        ReadLyirsFile = OpenLyircsFile.read()

        audiofile = eyed3.load("./" + new_name + ".mp3")
        audiofile.initTag()
        audiofile.tag.artist = target_artist
        audiofile.tag.title = target_title
        audiofile.tag.album = target_album
        audiofile.tag.lyrics.set(ReadLyirsFile)

        if os.path.exists(f"./cover/{target_index + 1}_modified.jpg"):
            audiofile.tag.images.set(3, open(f'./cover/{target_index + 1}_modified.jpg', 'rb').read(), 'image/jpeg')
        else:
            audiofile.tag.images.set(3, open(f'./cover/{target_index + 1}.jpg', 'rb').read(), 'image/jpeg')

        audiofile.tag.save(version=eyed3.id3.ID3_V2_3)

        if not os.path.exists("./변환된 파일"):
            os.makedirs("./변환된 파일")

        shutil.move(new_name + ".mp3", "./변환된 파일/" + new_name + ".mp3")

        self.updated_label.emit("변환 완료!")


if __name__ == "__main__":
    import sys
    ensure_latest_yt_dlp()

    app = QApplication(sys.argv)
    form = MyMain()
    app.exec_()
