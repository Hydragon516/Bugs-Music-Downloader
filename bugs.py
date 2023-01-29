from PyQt5.QtCore import pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QLabel, QListWidget, QLineEdit, QDialog, QPushButton, QHBoxLayout, QVBoxLayout, QApplication
from bs4 import BeautifulSoup
import requests
import re
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

search_title = ""

class MyMainGUI(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button = QPushButton("음악 검색")
        self.github_button = QPushButton("Github")
        
        self.search_input = QLineEdit(self)
        self.music_list = QListWidget(self)

        self.status_label = QLabel("", self)

        self.youtube_button = QPushButton("음원 다운로드")

        hbox = QHBoxLayout()
        hbox.addStretch(1)
        hbox.addWidget(self.search_input)
        hbox.addWidget(self.search_button)
        hbox.addWidget(self.github_button)
        hbox.addStretch(1)

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

        self.setWindowTitle('Bugs Downloader (v1.5)')
        self.setGeometry(300, 300, 500, 350)


class MyMain(MyMainGUI):
    add_sec_signal = pyqtSignal()
    send_instance_singal = pyqtSignal("PyQt_PyObject")

    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_button.clicked.connect(self.search)
        self.youtube_button.clicked.connect(self.download)
        self.github_button.clicked.connect(lambda: webbrowser.open('https://github.com/Hydragon516/Bugs-Music-Downloader'))

        self.search_input.textChanged[str].connect(self.title_update)
        self.music_list.itemClicked.connect(self.chkItemClicked)

        self.th_search = searcher(parent=self)
        self.th_search.updated_list.connect(self.list_update)
        self.th_search.updated_label.connect(self.status_update)

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
    updated_label = pyqtSignal(str)

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
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument("--disable-gpu")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_argument('--log-level=3')
            
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            self.updated_label.emit("서버에 접속하는 중...")

            driver.get(url='https://music.bugs.co.kr/search/track?q=' + search_title)

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

            try:
                for i in range(len(artist_list)):
                    self.updated_list.emit("%s // %s // %s // %s" % (str(i + 1), title_list[i], artist_list[i], album_list[i]))
            except:
                pass

            driver.close()

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

    def run(self):
        global keyword
        global search_title

        self.updated_label.emit("음원 파일을 읽는 중 ...")
        
        target_index = keyword.split(" // ")[0]
        target_title = keyword.split(" // ")[1]
        target_artist = keyword.split(" // ")[2]
        target_album = keyword.split(" // ")[3]

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument("--disable-gpu")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument('--log-level=3')

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.implicitly_wait(5)

        driver.get(url='https://music.bugs.co.kr/search/track?q=' + search_title)
        target_music_button = driver.find_element(By.XPATH,'//*[@id="DEFAULT0"]/table/tbody/tr[{}]/td[3]/a'.format(target_index))
        target_music_button.click()
        
        lyrics_url = driver.current_url

        driver.close()

        self.updated_label.emit("가사 가져오는 중 ...")
        
        html = requests.get(lyrics_url)
        soup = BeautifulSoup(html.text, 'html.parser')

        lyric = soup.find_all('div', {'class':'lyricsContainer'})
        lines = str(lyric).split("\n")

        line_state = False
        lyrics = []

        for item in lines:
            if line_state == True:
                if "</xmp></p>" not in item:
                    lyrics.append(item)
            
            if "<p><xmp>" in item:
                lyrics.append(item.replace("<p><xmp>", ""))
                line_state = True
            
            if "</xmp></p>" in item:
                lyrics.append(item.replace("</xmp></p>", ""))
                break

        with open("lyric.txt", 'w', encoding='utf-8') as f:
            for row in lyrics:
                f.write(row)

        f.close()

        self.updated_label.emit("앨범 커버 가져오는 중 ...")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.implicitly_wait(5)

        driver.get(lyrics_url)
        target_cover_button = driver.find_element(By.XPATH,'//*[@id="container"]/section[1]/div/div[1]/div/ul/li/a/span')
        target_cover_button.click()
        driver.implicitly_wait(5)
        target_cover_button = driver.find_element(By.XPATH,'//*[@id="container"]/section[1]/div/div[1]/div/ul/li/a/span')
        target_cover_button.click()
        driver.implicitly_wait(5)
        target_cover_button = driver.find_element(By.XPATH,'//*[@id="originalPhotoViewBtn"]/img')
        target_cover_button.click()
        driver.implicitly_wait(5)

        # cover = soup.find_all('div', {'class':'photos'})
        cover_link = driver.current_url
        cover_num = (cover_link.split("album/")[1]).split("?")[0]
        new_cover_link = "https://image.bugsm.co.kr/album/images/original/{}/{}.jpg".format(cover_num[0:-2], cover_num)
        driver.close()

        request.urlretrieve(new_cover_link, "cover.jpg")

        surch_keyword = target_title + " " + target_artist + " 음원"

        new_name = target_title + "_" + target_artist + ".mp3"
        new_name = new_name.replace("/", "_")

        url_list = []
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
        
        OpenLyircsFile = open("lyric.txt", 'r', encoding='UTF8') 
        ReadLyirsFile = OpenLyircsFile.read() 

        audiofile = eyed3.load("./" + new_name)
        audiofile.initTag()
        audiofile.tag.artist = target_artist
        audiofile.tag.title = target_title
        audiofile.tag.album = target_album
        audiofile.tag.lyrics.set(ReadLyirsFile)
        audiofile.tag.images.set(3, open('cover.jpg','rb').read(), 'image/jpeg')
        audiofile.tag.save(version=eyed3.id3.ID3_V2_3)

        if not os.path.exists("./변환된 파일"):
            os.makedirs("./변환된 파일")

        shutil.move(new_name, "./변환된 파일/" + new_name)

        self.updated_label.emit("변환 완료!")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    form = MyMain()
    app.exec_()
