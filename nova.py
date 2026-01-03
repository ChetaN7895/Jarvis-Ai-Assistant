# nova.py
# Nova HUD — Camera moved to the left column
# Requires: PySide6, psutil, opencv-python, deepface
# Run: pip install PySide6 psutil opencv-python deepface
#      python nova.py

import sys, math, random, time
from datetime import datetime
try:
    import psutil
except Exception:
    psutil = None

import cv2
from deepface import DeepFace

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QSize
from PySide6.QtGui import (QPainter, QColor, QPen, QFont, QLinearGradient,
                           QRadialGradient, QPainterPath, QImage, QPixmap)
from PySide6.QtWidgets import (QApplication, QWidget, QMainWindow, QLabel, QVBoxLayout,
                               QHBoxLayout, QFrame, QSizePolicy, QGridLayout)

# ---------- Helpers ----------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def smoothstep(edge0, edge1, x):
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3 - 2 * t)

# ---------- Widgets ----------
class SectionTitle(QLabel):
    # ... (अपरिवर्तित)
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("color:#CFE7FF; font-weight:700; font-size:12px; letter-spacing:1px;")

class CameraWidget(QFrame):
    # ... (अपरिवर्तित)
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background: rgba(12,16,22,230); border-radius:12px; border:1px solid rgba(120,160,220,30); }
            QLabel { color:#DCECFB; font-size:12px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        self.title = SectionTitle("LIVE CAMERA FEED")
        self.video_label = QLabel("Initializing Camera...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("border: 1px solid rgba(120,160,220,50); border-radius: 8px;")
        layout.addWidget(self.title)
        layout.addWidget(self.video_label, 1)
        self.capture = cv2.VideoCapture(0)
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        ret, frame = self.capture.read()
        if not ret: return
        frame = cv2.resize(frame, (320, 240))
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.face_cascade.detectMultiScale(gray_frame, 1.1, 4)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (100, 220, 255), 2)
            try:
                face_roi = rgb_frame[y:y+h, x:x+w]
                analysis = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False)
                emotion = analysis[0]['dominant_emotion'].capitalize()
                cv2.putText(frame, emotion, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 220, 255), 2)
            except: pass
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

    def stop_camera(self):
        self.timer.stop()
        if self.capture.isOpened(): self.capture.release()

class NeonBar(QWidget):
    # ... (अपरिवर्तित)
    def __init__(self, title, init=0.0, style='rainbow'):
        super().__init__()
        self.title = title
        self.value = float(init)
        self.unit = ""
        self.setMinimumHeight(56)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.style = style
    def setValue(self, v):
        self.value = clamp(float(v), 0.0, 100.0)
        self.update()
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); r = self.rect().adjusted(8, 8, -8, -8)
        p.setPen(Qt.NoPen); p.setBrush(QColor(14,18,24,220)); p.drawRoundedRect(self.rect(), 10, 10)
        p.setPen(QColor(170,190,210)); p.setFont(QFont("Segoe UI", 10, QFont.Bold)); p.drawText(r.x(), r.y()-2, r.width(), 16, Qt.AlignLeft|Qt.AlignTop, self.title.upper())
        bar = QRectF(r.x(), r.y()+20, r.width(), 14)
        p.setBrush(QColor(28,36,48,220)); p.setPen(Qt.NoPen); p.drawRoundedRect(bar, 8, 8)
        w = bar.width() * (self.value/100.0); fill = QRectF(bar.x(), bar.y(), w, bar.height())
        grad = QLinearGradient(fill.topLeft(), fill.topRight())
        if self.style == 'rainbow': grad.setColorAt(0.0, QColor(30, 220, 140)); grad.setColorAt(0.5, QColor(255, 200, 60)); grad.setColorAt(1.0, QColor(255, 90, 80))
        elif self.style == 'pink': grad.setColorAt(0.0, QColor(255, 100, 220)); grad.setColorAt(1.0, QColor(200, 50, 255))
        elif self.style == 'green': grad.setColorAt(0.0, QColor(40, 220, 120)); grad.setColorAt(1.0, QColor(20, 160, 100))
        else: grad.setColorAt(0.0, QColor(80,200,255)); grad.setColorAt(1.0, QColor(150,120,255))
        p.setBrush(grad); p.drawRoundedRect(fill, 8, 8)
        p.setPen(QPen(QColor(255,255,255,70), 1.0)); p.drawLine(bar.topLeft()+QPointF(0,1), bar.topRight()+QPointF(0,1))
        p.setPen(QColor(230,240,255)); p.setFont(QFont("Consolas", 11, QFont.DemiBold))
        txt = f"{int(self.value)}{self.unit if self.unit else '%'}"
        p.drawText(r, Qt.AlignRight|Qt.AlignVCenter, txt)

class StatCard(QFrame):
    # ... (अपरिवर्तित)
    def __init__(self, title, bars):
        super().__init__()
        self.setStyleSheet("QFrame { background: rgba(12,16,22,230); border-radius:12px; border:1px solid rgba(120,160,220,30); }")
        lay = QVBoxLayout(self); lay.setContentsMargins(12,12,12,12); lay.setSpacing(8)
        lay.addWidget(SectionTitle(title))
        for b in bars: lay.addWidget(b)

class NetworkStats(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background: rgba(12,16,22,230); border-radius:12px; border:1px solid rgba(120,160,220,30); }
            QLabel { color:#DCECFB; font-size:12px; }
        """)
        lay = QVBoxLayout(self); lay.setContentsMargins(12,12,12,12); lay.setSpacing(6)
        lay.addWidget(SectionTitle("NETWORK STATISTICS"))
        self.ip = QLabel("IP Address: 0.0.0.0")
        self.up = QLabel("Upload: 0.0 MB/s")
        self.down = QLabel("Download: 0.0 MB/s")
        lay.addWidget(self.ip); lay.addWidget(self.up); lay.addWidget(self.down)
        lay.addStretch()

class ClockCard(QFrame):
    # ... (अपरिवर्तित)
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background: rgba(12,16,22,230); border-radius:12px; border:1px solid rgba(120,160,220,30); }
            QLabel { color:#EAF6FF; }
        """)
        lay = QVBoxLayout(self); lay.setContentsMargins(12,12,12,12)
        self.timeLbl = QLabel("--:--:--")
        self.timeLbl.setStyleSheet("font-size:34px; font-weight:800;")
        self.dateLbl = QLabel("")
        self.dateLbl.setStyleSheet("color:#AFC7DA; font-size:12px;")
        lay.addWidget(self.timeLbl); lay.addWidget(self.dateLbl)

    def tick(self):
        now = datetime.now()
        self.timeLbl.setText(now.strftime("%H:%M:%S"))
        self.dateLbl.setText(now.strftime("%A, %d %b %Y"))

class AnimatedRings(QWidget):
    # ... (अपरिवर्तित)
    def __init__(self):
        super().__init__()
        self.phase = 0.0
        self.setMinimumSize(520, 520)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True); rect = self.rect()
        cx, cy = rect.center().x(), rect.center().y(); radius = min(rect.width(), rect.height()) * 0.42
        bg = QRadialGradient(QPointF(cx,cy), radius*1.8); bg.setColorAt(0.0, QColor(10,12,16)); bg.setColorAt(1.0, QColor(6,8,12,0)); p.fillRect(rect, bg)
        rings = [(radius*1.02, 9.0, 0.00, QColor(80,220,255,220)), (radius*0.86, 6.0, 0.19, QColor(255,160,90,210)), (radius*0.72, 4.0, 0.36, QColor(180,120,255,200)), (radius*0.59, 3.0, 0.54, QColor(100,220,200,200)), (radius*0.46, 2.2, 0.72, QColor(255,110,200,180)),]
        for r, w, off, col in rings: self._draw_ring(p, QPointF(cx,cy), r, w, off, col)
        p.setPen(QColor(200,240,255)); p.setFont(QFont("Segoe UI", 42, QFont.Black)); p.drawText(rect, Qt.AlignCenter, "J.A.R.V.I.S")
        p.setFont(QFont("Segoe UI", 12, QFont.DemiBold)); p.setPen(QColor(160,200,255)); p.drawText(rect.adjusted(0,40,0,0), Qt.AlignHCenter|Qt.AlignTop, "•  ONLINE")
    def _draw_ring(self, p, center, radius, width, offset, color):
        base = (self.phase + offset) % 1.0
        for i in range(2):
            start = (base + i*0.48) * 360.0; span = 200.0 if i == 0 else 120.0
            pen = QPen(color, width); pen.setCapStyle(Qt.RoundCap); p.setPen(pen)
            rect = QRectF(center.x()-radius, center.y()-radius, radius*2, radius*2)
            p.drawArc(rect, int(-start*16), int(-span*16))
        p.setPen(Qt.NoPen); dots = 36
        for k in range(dots):
            t = (k/dots + base*0.08) % 1.0; ang = t * 2*math.pi; d = radius - width*1.6; x = center.x() + math.cos(ang)*d; y = center.y() + math.sin(ang)*d
            a = int(80 * smoothstep(0.0, 1.0, 1.0-abs(0.5-t)*2)) + 40
            p.setBrush(QColor(80,220,255,a)); p.drawEllipse(QPointF(x,y), 2.2, 2.2)

class TitleBar(QFrame):
    # ... (अपरिवर्तित)
    def __init__(self, title):
        super().__init__()
        self.setStyleSheet("QFrame{ background: rgba(12,16,22,200); border-bottom:1px solid rgba(120,160,220,25); } QLabel{ color:#DDEFFB; font-weight:700; }")
        lay = QHBoxLayout(self); lay.setContentsMargins(12,8,12,8); lbl = QLabel(title); lbl.setFont(QFont("Segoe UI", 12, QFont.Bold)); lay.addWidget(lbl); lay.addStretch()

class NovaHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S Vision HUD")
        self.resize(1220, 760)
        self.setStyleSheet("background-color: #071018;")

        top = TitleBar("J.A.R.V.I.S VISION INTERFACE")
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(10,10,10,10); root.setSpacing(10)
        root.addWidget(top)

        body = QGridLayout(); body.setSpacing(12)
        root.addLayout(body, 1)

        # === [बदलाव] === लेआउट को यहाँ समायोजित किया गया है ===

        # LEFT TOP card (CPU PROFILES)
        self.cpu_util = NeonBar("CPU UTILIZATION", init=65)
        self.cpu_temp = NeonBar("CPU TEMPERATURE", init=62)
        self.battery = NeonBar("BATTERY", init=72)
        leftCard = StatCard("SYSTEM PROFILES", [self.cpu_util, self.cpu_temp, self.battery])
        # अब यह केवल एक पंक्ति लेता है (1, 1)
        body.addWidget(leftCard, 0, 0, 1, 1)

        # LEFT BOTTOM: Camera
        self.camera_view = CameraWidget()
        # इसे बाईं ओर नीचे रखें (पंक्ति 1, कॉलम 0)
        body.addWidget(self.camera_view, 1, 0, 1, 1)

        # CENTER: animated rings (अपरिवर्तित)
        self.rings = AnimatedRings()
        body.addWidget(self.rings, 0, 1, 2, 1) # यह दो पंक्तियाँ लेता है

        # RIGHT TOP: OTHER STATS (अपरिवर्तित)
        self.mem = NeonBar("MEMORY USAGE", init=50, style='pink')
        self.disk = NeonBar("DISK USAGE", init=75, style='green')
        rightCard = StatCard("STORAGE STATS", [self.mem, self.disk])
        body.addWidget(rightCard, 0, 2, 1, 1)

        # RIGHT BOTTOM: network + clock (कैमरा को नेटवर्क से बदल दिया गया)
        rightLower = QVBoxLayout(); rightLower.setSpacing(10)
        self.net = NetworkStats() # NetworkStats को वापस लाएं
        self.clock = ClockCard()
        rightLower.addWidget(self.net)
        rightLower.addWidget(self.clock)
        rightWrap = QWidget(); rightWrap.setLayout(rightLower)
        body.addWidget(rightWrap, 1, 2, 1, 1)
        
        # Grid layout को ठीक से संतुलित करें
        body.setColumnStretch(0, 1)
        body.setColumnStretch(1, 2)
        body.setColumnStretch(2, 1)
        body.setRowStretch(0, 1)
        body.setRowStretch(1, 1)

        # timers (अपरिवर्तित)
        self.animTimer = QTimer(self); self.animTimer.timeout.connect(self.animate); self.animTimer.start(16)
        self.statTimer = QTimer(self); self.statTimer.timeout.connect(self.sampleStats); self.statTimer.start(1000)
        self.clockTimer = QTimer(self); self.clockTimer.timeout.connect(self.tick); self.clockTimer.start(1000)

        self.last_bytes = None
        self.sampleStats()
        self.tick()

    def animate(self):
        self.rings.phase = (self.rings.phase + 0.0075) % 1.0
        self.rings.update()

    def tick(self):
        self.clock.tick()

    def sampleStats(self):
        # ... (यह फंक्शन लगभग अपरिवर्तित है)
        try: cpu = psutil.cpu_percent(interval=None) if psutil else random.uniform(8,88)
        except: cpu = random.uniform(8,88)
        self.cpu_util.setValue(cpu)
        temp_c = None
        if psutil:
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for k,v in temps.items():
                        if v: temp_c = v[0].current; break
            except: temp_c = None
        if temp_c is None: temp_c = 48 + 12*math.sin(time.time()/6.5) + random.uniform(-2,2)
        self.cpu_temp.setValue(clamp((temp_c/100.0)*100, 0, 100))
        batt_pct = None
        if psutil and hasattr(psutil, "sensors_battery"):
            try:
                b = psutil.sensors_battery()
                if b: batt_pct = b.percent
            except: batt_pct = None
        if batt_pct is None: batt_pct = 70 + 8*math.sin(time.time()/10.0) + random.uniform(-4,4)
        self.battery.setValue(clamp(batt_pct, 0, 100))
        try: mem_pct = psutil.virtual_memory().percent if psutil else random.uniform(22,86)
        except: mem_pct = random.uniform(22,86)
        self.mem.setValue(mem_pct)
        try: disk_pct = psutil.disk_usage('/').percent if psutil else random.uniform(12,88)
        except: disk_pct = random.uniform(12,88)
        self.disk.setValue(disk_pct)

        # Network stats update code (यह अब आवश्यक है)
        if psutil:
            try:
                addrs = psutil.net_if_addrs(); ip = "0.0.0.0"
                for _, arr in addrs.items():
                    for a in arr:
                        if getattr(a, 'family', None) and str(getattr(a, 'address','')).count('.')==3 and not a.address.startswith("169.254"):
                            ip = a.address; break
                    if ip!="0.0.0.0": break
                self.net.ip.setText(f"IP Address: {ip}")
            except: self.net.ip.setText("IP Address: 0.0.0.0")
            try:
                io = psutil.net_io_counters(); nowb = (io.bytes_sent, io.bytes_recv)
                if self.last_bytes:
                    up = (nowb[0]-self.last_bytes[0]) / 1024.0 / 1024.0
                    down = (nowb[1]-self.last_bytes[1]) / 1024.0 / 1024.0
                    self.net.up.setText(f"Upload: {up:.1f} MB/s")
                    self.net.down.setText(f"Download: {down:.1f} MB/s")
                self.last_bytes = nowb
            except: pass
        else:
            self.net.ip.setText("IP Address: 192.168.1.101")
            self.net.up.setText(f"Upload: {random.uniform(0.4,3.2):.1f} MB/s")
            self.net.down.setText(f"Download: {random.uniform(3.3,18.3):.1f} MB/s")

    def closeEvent(self, event):
        self.camera_view.stop_camera()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    w = NovaHUD(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()