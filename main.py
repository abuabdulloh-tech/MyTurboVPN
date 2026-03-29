import sys
import requests
import winreg
import time
import re
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QMessageBox, QHBoxLayout)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer

class ProxyWorker(QThread):
    finished_signal = pyqtSignal(list)

    def run(self):
        sources = [
            "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=all",
            "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt"
        ]
        
        raw_list = set()
        for url in sources:
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    found = re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', r.text)
                    raw_list.update(found)
            except: continue

        valid_proxies = []
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(self.verify_speed, p) for p in list(raw_list)[:300]]
            for future in futures:
                res = future.result()
                if res: valid_proxies.append(res)
        
        valid_proxies.sort(key=lambda x: x[3])
        self.finished_signal.emit(valid_proxies[:20])

    def verify_speed(self, proxy):
        proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0 Safari/537.36'}
        start = time.time()
        try:
            r = requests.get("https://www.google.com/favicon.ico", proxies=proxies, timeout=3, headers=headers)
            if r.status_code == 200:
                duration = time.time() - start
                try:
                    ip_only = proxy.split(':')[0]
                    geo_r = requests.get(f"http://ip-api.com/json/{ip_only}", timeout=2)
                    country = geo_r.json().get("country", "Noma'lum")
                except: country = "Aniqlanmadi"
                return [proxy, "HTTP/HTTPS", country, duration]
        except: return None

class ProxyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyTurboVPN v1.0")
        self.resize(850, 650)
        
        layout = QVBoxLayout()
        
        # Holat paneli
        self.status_label = QLabel("Tizim proksisi: Tekshirilmoqda...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; padding: 5px; border: 1px solid #ddd;")
        layout.addWidget(self.status_label)

        # Jadval
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Proxy Manzili", "Tur", "Davlat", "Tezlik (s)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        # Boshqaruv tugmalari
        self.btn_manual = QPushButton("🔄 Ro'yxatni hozir yangilash")
        self.btn_manual.clicked.connect(self.start_scan)
        layout.addWidget(self.btn_manual)

        self.btn_connect = QPushButton("✅ Tanlangan proksini ulanish")
        self.btn_connect.clicked.connect(self.apply_proxy)
        self.btn_connect.setStyleSheet("height: 45px; background: #27ae60; color: white; font-weight: bold;")
        layout.addWidget(self.btn_connect)

        # PROKSINI O'CHIRISH TUGMASI (ALOHIDA PASTDA)
        self.btn_off = QPushButton("❌ PROKSINI O'CHIRISH (O'Z INTERNETIMGA QAYTISH)")
        self.btn_off.clicked.connect(self.disable_proxy_action)
        self.btn_off.setStyleSheet("height: 40px; background: #c0392b; color: white; font-weight: bold; margin-top: 10px;")
        layout.addWidget(self.btn_off)

        # Taymerlar
        self.timer = QTimer()
        self.timer.timeout.connect(self.start_scan)
        self.timer.start(30000) # 60 soniyada avto-yangilash

        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui_status)
        self.ui_timer.start(2000) # Holatni 2 soniyada tekshirish

        self.setLayout(layout)
        self.start_scan()
        self.update_ui_status()

    def update_ui_status(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_READ)
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if enabled == 1:
                server = winreg.QueryValueEx(key, "ProxyServer")[0]
                self.status_label.setText(f"HOLAT: YOQILGAN ✅ ({server})")
                self.status_label.setStyleSheet("color: #27ae60; font-weight: bold; background: #f1fcf4; padding: 5px;")
            else:
                self.status_label.setText("HOLAT: O'CHIRILGAN ❌ (O'z internetingiz)")
                self.status_label.setStyleSheet("color: #c0392b; font-weight: bold; background: #fdf2f2; padding: 5px;")
            winreg.CloseKey(key)
        except: pass

    def start_scan(self):
        self.worker = ProxyWorker()
        self.worker.finished_signal.connect(self.update_table)
        self.worker.start()

    def update_table(self, data):
        self.table.setRowCount(0)
        for p in data:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(p[0])))
            self.table.setItem(row, 1, QTableWidgetItem(str(p[1])))
            self.table.setItem(row, 2, QTableWidgetItem(str(p[2])))
            self.table.setItem(row, 3, QTableWidgetItem(f"{round(p[3], 3)} s"))

    def apply_proxy(self):
        row = self.table.currentRow()
        if row == -1:
            QMessageBox.warning(self, "Diqqat", "Ro'yxatdan birorta proksini tanlang!")
            return
        proxy = self.table.item(row, 0).text()
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy)
            winreg.CloseKey(key)
            self.update_ui_status()
        except Exception as e:
            QMessageBox.critical(self, "Xato", f"Ulanib bo'lmadi: {e}")

    def disable_proxy_action(self):
        """Tizim proksi sozlamalarini qo'lda o'chirish"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self.update_ui_status()
            QMessageBox.information(self, "Tozalandi", "Tizim proksisi o'chirildi. O'z internetingiz ishlamoqda.")
        except: pass

    def closeEvent(self, event):
        """Dastur yopilganda (X bosilganda) proksini tozalash"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
        except: pass
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProxyApp()
    window.show()
    sys.exit(app.exec())