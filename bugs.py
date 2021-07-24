from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QLabel, QListWidget, QLineEdit, QDialog, QPushButton, QHBoxLayout, QVBoxLayout, QApplication
from bs4 import BeautifulSoup
import requests
import re
import youtube_dl
import eyed3
import os
import shutil
from selenium import webdriver

search_title = ""

class MyMainGUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button = QPushButton("음악 검색")
        self.search_input = QLineEdit(self)
        self.music_list = QListWidget(self)

        self.status_label = QLabel("", self)

        self.youtube_button = QPushButton("음원 다운로드")

        hbox = QHBoxLayout()
        hbox.addStretch(0)
        hbox.addWidget(self.search_input)
        hbox.addWidget(self.search_button)
        hbox.addStretch(0)

        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.music_list)

        hbox3 = QHBoxLayout()
        hbox3.addWidget(self.youtube_button)

        vbox = QVBoxLayout()
        vbox.addStretch(1)
        vbox.addLayout(hbox)
        vbox.addStretch(1)
        vbox.addLayout(hbox2)
        vbox.addStretch(1)
        vbox.addLayout(hbox3)
        vbox.addStretch(1)
        vbox.addWidget(self.status_label)

        self.setLayout(vbox)

        self.setWindowTitle('Bugs Downloader')
        self.setGeometry(300, 300, 500, 200)


class MyMain(MyMainGUI):
    add_sec_signal = pyqtSignal()
    send_instance_singal = pyqtSignal("PyQt_PyObject")

    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button.clicked.connect(self.search)
        self.youtube_button.clicked.connect(self.download)

        self.search_input.textChanged[str].connect(self.title_update)
        self.music_list.itemClicked.connect(self.chkItemClicked)

        self.th_search = searcher(parent=self)
        self.th_search.updated_list.connect(self.list_update)

        self.th_download = downloadr(parent=self)
        self.th_download.updated_label.connect(self.status_update)

        self.show()
    
    def title_update(self, input):
        global search_title
        search_title = input
    
    def chkItemClicked(self) :
        global keyword
        keyword = self.music_list.currentItem().text() 

    @pyqtSlot()
    def search(self):
        self.music_list.clear()
        self.th_search.start()

    @pyqtSlot()
    def download(self):
        self.th_download.start()

    @pyqtSlot(str)
    def list_update(self, msg):
        self.music_list.addItem(msg)
    
    @pyqtSlot(str)
    def status_update(self, msg):
        self.status_label.setText(msg)


class searcher(QThread):
    updated_list = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()

    def run(self):

        global search_title
        global keyword

        title_list = []
        artist_list = []
        album_list = []
        
        if search_title != "":
            html = requests.get('https://music.bugs.co.kr/search/integrated?q=' + search_title)
            soup = BeautifulSoup(html.text, 'html.parser')
            
            title = soup.find_all('p', {'class':'title'})
            artist = soup.find_all('p', {'class':'artist'})
            album = soup.find_all('a', {'class':'album'})

            if len(title) > 5:
                album = album[1:]
                
                for i in range(len(album)):
                    result = re.search('" title="(.*)">', str(album[i]))
                    album_list.append(str(result.group(1)))

                for i in range(len(title)):
                    result = re.search('" title="(.*)">', str(title[i]))
                    title_list.append(str(result.group(1)))

                for i in range(len(artist)):
                    result = re.search('" title="(.*)">', str(artist[i]))
                    artist_list.append(str(result.group(1)))

                title_list = title_list[:10]
                artist_list = artist_list[:10]
                album_list = album_list[:10]

                for i in range(len(artist_list)):
                    self.updated_list.emit("%s // %s // %s" % (title_list[i], artist_list[i], album_list[i]))


class downloadr(QThread):
    updated_label = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__()
        self.main = parent

    def __del__(self):
        self.wait()

    def run(self):
        global keyword

        self.updated_label.emit("음원 파일을 읽는 중 입니다...")
        
        target_title = keyword.split(" // ")[0]
        target_artist = keyword.split(" // ")[1]
        target_album = keyword.split(" // ")[2]

        surch_keyword = target_title + "-" + target_artist + " 음원 듣기"

        new_name = target_title + "_" + target_artist + ".mp3"

        url_list = []
        url = 'https://www.youtube.com/results?search_query={}'.format(surch_keyword)

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--window-size=1024,768')
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome('./chromedriver.exe', options=options)
        
        
        driver.get(url)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.close()

        video_url = soup.select('a#video-title')

        for i in video_url:
            url_list.append('{}{}'.format('https://www.youtube.com',i.get('href')))
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        self.updated_label.emit("음원 다운로드 중 입니다...")

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_list[0]])

        self.updated_label.emit("파일 변환 중 입니다...")

        files = os.listdir("./")

        for file in files:
            if ".mp3" in file:
                os.rename(file, new_name)
        
        audiofile = eyed3.load("./" + new_name)
        audiofile.initTag()
        audiofile.tag.artist = target_artist
        audiofile.tag.title = target_title
        audiofile.tag.album = target_album
        audiofile.tag.save()

        if not os.path.exists("./변환된 파일"):
            os.makedirs("./변환된 파일")

        shutil.move(new_name, "./변환된 파일/" + new_name)

        self.updated_label.emit("변환 완료!")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    form = MyMain()
    app.exec_()