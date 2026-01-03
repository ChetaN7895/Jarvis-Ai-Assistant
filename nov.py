# nova.py
# Nova HUD — improved to look much closer to the provided image
# Requires: PySide6, psutil (optional)
# Run: pip install PySide6 psutil
#      python nova.py

import sys, math, random, time
from datetime import datetime
try:
    import psutil
except Exception:
    psutil = None

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QSize
from PySide6.QtGui import (QPainter, QColor, QPen, QFont, QLinearGradient,
                           QRadialGradient, QPainterPath)
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
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("color:#CFE7FF; font-weight:700; font-size:12px; letter-spacing:1px;")

class NeonBar(QWidget):
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
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(8, 8, -8, -8)

        # background card
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(14,18,24,220))
        p.drawRoundedRect(self.rect(), 10, 10)

        # title label
        p.setPen(QColor(170,190,210))
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.drawText(r.x(), r.y()-2, r.width(), 16, Qt.AlignLeft|Qt.AlignTop, self.title.upper())

        # bar background
        bar = QRectF(r.x(), r.y()+20, r.width(), 14)
        p.setBrush(QColor(28,36,48,220))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(bar, 8, 8)

        # fill gradient depends on style
        w = bar.width() * (self.value/100.0)
        fill = QRectF(bar.x(), bar.y(), w, bar.height())
        grad = QLinearGradient(fill.topLeft(), fill.topRight())
        if self.style == 'rainbow':
            grad.setColorAt(0.0, QColor(30, 220, 140))
            grad.setColorAt(0.5, QColor(255, 200, 60))
            grad.setColorAt(1.0, QColor(255, 90, 80))
        elif self.style == 'pink':
            grad.setColorAt(0.0, QColor(255, 100, 220))
            grad.setColorAt(1.0, QColor(200, 50, 255))
        elif self.style == 'green':
            grad.setColorAt(0.0, QColor(40, 220, 120))
            grad.setColorAt(1.0, QColor(20, 160, 100))
        else:
            grad.setColorAt(0.0, QColor(80,200,255))
            grad.setColorAt(1.0, QColor(150,120,255))

        p.setBrush(grad)
        p.drawRoundedRect(fill, 8, 8)

        # glow line top
        pen = QPen(QColor(255,255,255,70), 1.0)
        p.setPen(pen)
        p.drawLine(bar.topLeft()+QPointF(0,1), bar.topRight()+QPointF(0,1))

        # value text right
        p.setPen(QColor(230,240,255))
        p.setFont(QFont("Consolas", 11, QFont.DemiBold))
        txt = f"{int(self.value)}{self.unit if self.unit else '%'}"
        p.drawText(r, Qt.AlignRight|Qt.AlignVCenter, txt)

class StatCard(QFrame):
    def __init__(self, title, bars):
        super().__init__()
        self.setStyleSheet("""
            QFrame { background: rgba(12,16,22,230); border-radius:12px; border:1px solid rgba(120,160,220,30); }
        """)
        lay = QVBoxLayout(self); lay.setContentsMargins(12,12,12,12); lay.setSpacing(8)
        lay.addWidget(SectionTitle(title))
        for b in bars:
            lay.addWidget(b)

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
        self.small = QLabel("")
        lay.addWidget(self.ip); lay.addWidget(self.up); lay.addWidget(self.down); lay.addWidget(self.small)

class ClockCard(QFrame):
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
    def __init__(self):
        super().__init__()
        self.phase = 0.0
        self.setMinimumSize(520, 520)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        cx, cy = rect.center().x(), rect.center().y()
        radius = min(rect.width(), rect.height()) * 0.42

        # radial background subtle glow
        bg = QRadialGradient(QPointF(cx,cy), radius*1.8)
        bg.setColorAt(0.0, QColor(10,12,16))
        bg.setColorAt(1.0, QColor(6,8,12,0))
        p.fillRect(rect, bg)

        # multiple rings with different speeds & widths
        rings = [
            (radius*1.02, 9.0, 0.00, QColor(80,220,255,220)),
            (radius*0.86, 6.0, 0.19, QColor(255,160,90,210)),
            (radius*0.72, 4.0, 0.36, QColor(180,120,255,200)),
            (radius*0.59, 3.0, 0.54, QColor(100,220,200,200)),
            (radius*0.46, 2.2, 0.72, QColor(255,110,200,180)),
        ]
        for r, w, off, col in rings:
            self._draw_ring(p, QPointF(cx,cy), r, w, off, col)

        # central text NOVA and ONLINE with slight glow
        p.setPen(QColor(200,240,255))
        p.setFont(QFont("Segoe UI", 42, QFont.Black))
        p.drawText(rect, Qt.AlignCenter, "NOVA")
        p.setFont(QFont("Segoe UI", 12, QFont.DemiBold))
        p.setPen(QColor(160,200,255))
        p.drawText(rect.adjusted(0,40,0,0), Qt.AlignHCenter|Qt.AlignTop, "•  ONLINE")

    def _draw_ring(self, p, center, radius, width, offset, color):
        base = (self.phase + offset) % 1.0
        # two arcs per ring (like the image feel)
        for i in range(2):
            start = (base + i*0.48) * 360.0
            span = 200.0 if i == 0 else 120.0
            pen = QPen(color, width)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            rect = QRectF(center.x()-radius, center.y()-radius, radius*2, radius*2)
            p.drawArc(rect, int(-start*16), int(-span*16))

        # dotted orbit
        p.setPen(Qt.NoPen)
        dots = 36
        for k in range(dots):
            t = (k/dots + base*0.08) % 1.0
            ang = t * 2*math.pi
            d = radius - width*1.6
            x = center.x() + math.cos(ang)*d
            y = center.y() + math.sin(ang)*d
            a = int(80 * smoothstep(0.0, 1.0, 1.0-abs(0.5-t)*2)) + 40
            p.setBrush(QColor(80,220,255,a))
            p.drawEllipse(QPointF(x,y), 2.2, 2.2)

class TitleBar(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setStyleSheet("QFrame{ background: rgba(12,16,22,200); border-bottom:1px solid rgba(120,160,220,25); } QLabel{ color:#DDEFFB; font-weight:700; }")
        lay = QHBoxLayout(self); lay.setContentsMargins(12,8,12,8)
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lay.addWidget(lbl); lay.addStretch()

class NovaHUD(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nova AI Assistant - @TechOpTrack")
        self.resize(1220, 760)
        self.setStyleSheet("background-color: #071018;")

        top = TitleBar("Nova AI Assistant - @TechOpTrack")
        central = QWidget(); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(10,10,10,10); root.setSpacing(10)
        root.addWidget(top)

        body = QGridLayout(); body.setSpacing(12)
        root.addLayout(body, 1)

        # LEFT card (CPU PROFILES)
        self.cpu_util = NeonBar("CPU UTILIZATION", init=65, style='rainbow')
        self.cpu_temp = NeonBar("CPU TEMPERATURE", init=62, style='rainbow')
        self.battery = NeonBar("BATTERY", init=72, style='rainbow')
        leftCard = StatCard("CPU PROFILES", [self.cpu_util, self.cpu_temp, self.battery])
        body.addWidget(leftCard, 0, 0, 2, 1)

        # CENTER: animated rings
        self.rings = AnimatedRings()
        body.addWidget(self.rings, 0, 1, 2, 1)

        # RIGHT top: OTHER STATS
        self.mem = NeonBar("MEMORY USAGE", init=50, style='pink')
        self.mem.unit = ""
        self.disk = NeonBar("DISK USAGE", init=75, style='green')
        rightCard = StatCard("OTHER STATS", [self.mem, self.disk])
        body.addWidget(rightCard, 0, 2, 1, 1)

        # RIGHT bottom: network + clock + big time box
        rightLower = QVBoxLayout(); rightLower.setSpacing(10)
        self.net = NetworkStats()
        self.clock = ClockCard()
        # big temporal sync box (like image)
        self.bigTime = QFrame()
        self.bigTime.setStyleSheet("QFrame{ background: rgba(18,22,28,230); border-radius:10px; border:1px solid rgba(180,120,80,30); } QLabel{ color:#F4EDE6; }")
        btlay = QVBoxLayout(self.bigTime); btlay.setContentsMargins(12,12,12,12)
        self.bigTimeLabel = QLabel("00:00:00")
        self.bigTimeLabel.setFont(QFont("Consolas", 26, QFont.Bold))
        self.bigTimeDate = QLabel("")
        self.bigTimeDate.setStyleSheet("color:#C8D6E6;")
        btlay.addWidget(self.bigTimeLabel); btlay.addWidget(self.bigTimeDate)

        rightLower.addWidget(self.net)
        rightLower.addWidget(self.clock)
        # rightLower.addWidget(self.bigTime)
        rightWrap = QWidget(); rightWrap.setLayout(rightLower)
        body.addWidget(rightWrap, 1, 2, 1, 1)

        # timers
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
        now = datetime.now()
        self.bigTimeLabel.setText(now.strftime("%H:%M:%S"))
        self.bigTimeDate.setText(now.strftime("%A, %d %b %Y"))
        self.clock.tick()

    def sampleStats(self):
        # CPU
        try:
            cpu = psutil.cpu_percent(interval=None) if psutil else random.uniform(8,88)
        except Exception:
            cpu = random.uniform(8,88)
        self.cpu_util.setValue(cpu)

        # temp
        temp_c = None
        if psutil:
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for k,v in temps.items():
                        if v:
                            temp_c = v[0].current
                            break
            except Exception:
                temp_c = None
        if temp_c is None:
            temp_c = 48 + 12*math.sin(time.time()/6.5) + random.uniform(-2,2)
        self.cpu_temp.setValue(clamp((temp_c/100.0)*100, 0, 100))

        # battery pseudo-temperature (image shows 72°C)
        batt_pct = None
        if psutil and hasattr(psutil, "sensors_battery"):
            try:
                b = psutil.sensors_battery()
                if b:
                    batt_pct = b.percent
            except Exception:
                batt_pct = None
        if batt_pct is None:
            batt_pct = 70 + 8*math.sin(time.time()/10.0) + random.uniform(-4,4)
        pseudo_temp = 60 + (batt_pct/100.0)*20
        self.battery.setValue(clamp(pseudo_temp, 0, 100))

        # memory
        try:
            mem_pct = psutil.virtual_memory().percent if psutil else random.uniform(22,86)
        except Exception:
            mem_pct = random.uniform(22,86)
        self.mem.setValue(mem_pct)

        # disk
        try:
            disk_pct = psutil.disk_usage('/').percent if psutil else random.uniform(12,88)
        except Exception:
            disk_pct = random.uniform(12,88)
        self.disk.setValue(disk_pct)

        # network
        if psutil:
            try:
                addrs = psutil.net_if_addrs()
                ip = "0.0.0.0"
                for _, arr in addrs.items():
                    for a in arr:
                        if getattr(a, 'family', None) and str(getattr(a, 'address','')).count('.')==3 and not a.address.startswith("169.254"):
                            ip = a.address; break
                    if ip!="0.0.0.0": break
                self.net.ip.setText(f"IP Address: {ip}")
            except Exception:
                self.net.ip.setText("IP Address: 0.0.0.0")
            try:
                io = psutil.net_io_counters()
                nowb = (io.bytes_sent, io.bytes_recv)
                if self.last_bytes:
                    up = (nowb[0]-self.last_bytes[0]) / 1024.0 / 1024.0
                    down = (nowb[1]-self.last_bytes[1]) / 1024.0 / 1024.0
                    self.net.up.setText(f"Upload: {up:.1f} MB/s")
                    self.net.down.setText(f"Download: {down:.1f} MB/s")
                self.last_bytes = nowb
            except Exception:
                pass
        else:
            self.net.ip.setText("IP Address: 192.168.1.101")
            self.net.up.setText(f"Upload: {random.uniform(0.4,3.2):.1f} MB/s")
            self.net.down.setText(f"Download: {random.uniform(3.3,18.3):.1f} MB/s")

def main():
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    w = NovaHUD(); w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
