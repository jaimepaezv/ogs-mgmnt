import sys
import os
import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QDialog, QFormLayout, QComboBox, QDateEdit,
    QMessageBox, QFileDialog, QTabWidget, QGridLayout,
    QScrollArea, QCalendarWidget, QTextEdit, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, QSize, QUrl, QRect, QPoint
from PySide6.QtGui import QIcon, QFont, QColor, QDesktopServices, QPainter, QPen, QBrush, QLinearGradient

# Local Imports
from app.models.database import (
    initialize_db, Service, Client, ServiceStatus, Provider, 
    ServiceType, Ticket, Offer, Task, Note, Invoice, Payment, 
    AuditLog, MessageTemplate, Reminder
)
from app.services.logic import BusinessLogic
from app.utils.security import backup_db, restore_db

class Theme:
    PRIMARY = "#1e272e"
    SECONDARY = "#2f3640"
    ACCENT = "#3498db"
    DANGER = "#e84118"
    SUCCESS = "#27ae60"
    WARNING = "#f39c12"
    WHATSAPP = "#25D366"
    WHITE = "#ffffff"
    BG = "#f5f6fa"

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DHM Pro | Acceso Seguro")
        self.setFixedSize(420, 320)
        self.setStyleSheet(f"background-color: {Theme.BG}; border-radius: 8px;")
        
        lyt = QVBoxLayout(self)
        lyt.setContentsMargins(40, 40, 40, 40)
        lyt.setSpacing(15)
        
        header = QLabel("DHM PRO")
        header.setStyleSheet(f"color: {Theme.PRIMARY}; font-size: 24px; font-weight: bold; margin-bottom: 5px;")
        header.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Professional Reseller Management")
        subtitle.setStyleSheet(f"color: {Theme.SECONDARY}; font-size: 11px; margin-bottom: 15px;")
        subtitle.setAlignment(Qt.AlignCenter)
        
        input_style = f"""
            QLineEdit {{
                background-color: white;
                border: 2px solid #dcdde1;
                border-radius: 6px;
                padding: 10px;
                color: {Theme.PRIMARY};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {Theme.ACCENT};
            }}
        """
        
        self.user = QLineEdit(placeholderText="Usuario")
        self.user.setStyleSheet(input_style)
        self.user.setMinimumHeight(45)
        
        self.pwd = QLineEdit(placeholderText="Contraseña")
        self.pwd.setStyleSheet(input_style)
        self.pwd.setMinimumHeight(45)
        self.pwd.setEchoMode(QLineEdit.Password)
        
        self.btn = QPushButton("ENTRAR AL SISTEMA")
        self.btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Theme.ACCENT};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 4px;
                font-weight: bold;
                font-size: 14px;
                margin-top: 15px;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
            }}
        """)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.check_login)
        
        lyt.addWidget(header)
        lyt.addWidget(subtitle)
        lyt.addWidget(self.user)
        lyt.addWidget(self.pwd)
        lyt.addWidget(self.btn)
        lyt.addStretch()

    def check_login(self):
        # admin/admin as default local login
        if self.user.text() == "admin" and self.pwd.text() == "admin":
            self.accept()
        else:
            QMessageBox.critical(self, "Acceso Denegado", "Usuario o contraseña incorrectos.\nVerifique sus credenciales.")

class BaseView(QWidget):
    def __init__(self, title):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        head = QHBoxLayout()
        self.title_lbl = QLabel(title); self.title_lbl.setFont(QFont("Segoe UI Variable Display", 22, QFont.Bold))
        head.addWidget(self.title_lbl); head.addStretch()
        self.layout.addLayout(head); self.layout.addSpacing(10)

    def send_whatsapp(self, template, client_id, service_id=None):
        try:
            url = BusinessLogic.prepare_whatsapp_msg(template, client_id, service_id)
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            QMessageBox.warning(self, "WhatsApp", str(e))

    def send_email(self, template, client_id, service_id=None):
        try:
            url = BusinessLogic.prepare_email_msg(template, client_id, service_id)
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            QMessageBox.warning(self, "Email", str(e))

class FinanceTrendChart(QWidget):
    """Custom high-end Bar Chart for Financial Trends."""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(160)
        self.data = [] # List of {"label": str, "value": float}

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        if not self.data: return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Geometry
        w, h = self.width(), self.height()
        margin = 40
        chart_w = w - (margin * 2)
        chart_h = h - (margin * 2)
        
        max_val = max([d['value'] for d in self.data]) if self.data else 0
        if max_val == 0: max_val = 1 # Avoid div by zero
        
        bar_spacing = 20
        total_bars = len(self.data)
        bar_w = (chart_w - (bar_spacing * (total_bars - 1))) / total_bars
        
        # Draw Axis/Grid
        p.setPen(QPen(QColor("#d1d8e0"), 1, Qt.DashLine))
        for i in range(4): # 4 Grid lines
            y = margin + (chart_h / 3) * i
            p.drawLine(margin, y, w - margin, y)
        
        # Draw Bars
        for i, d in enumerate(self.data):
            val_h = (d['value'] / max_val) * chart_h
            x = margin + i * (bar_w + bar_spacing)
            y = margin + chart_h - val_h
            
            rect = QRect(int(x), int(y), int(bar_w), int(val_h))
            
            # Gradient
            grad = QLinearGradient(x, y, x, y + val_h)
            grad.setColorAt(0, QColor(Theme.ACCENT))
            grad.setColorAt(1, QColor(Theme.PRIMARY))
            
            p.setBrush(QBrush(grad))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(rect, 6, 6)
            
            # Labels
            p.setPen(QColor(Theme.SECONDARY))
            p.setFont(QFont("Segoe UI", 10, QFont.Bold))
            p.drawText(int(x), int(h - 10), int(bar_w), 20, Qt.AlignCenter, d['label'])
            
            # Values on top
            if d['value'] > 0:
                p.drawText(int(x), int(y - 25), int(bar_w), 20, Qt.AlignCenter, f"${int(d['value'])}")

class DashboardView(BaseView):
    def __init__(self):
        super().__init__("Panel de Control Principal")
        
        # Top Region: Split Layout (Metrics Matrix | Trend Chart)
        top_container = QHBoxLayout(); top_container.setSpacing(15); top_container.setContentsMargins(0, 5, 0, 5)
        
        # Left Side: Metrics Matrix (Card Grid)
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(10)
        self.stat_active = self._card("ACTIVOS", "0", Theme.SUCCESS)
        self.stat_warn = self._card("PENDIENTES", "0", Theme.WARNING)
        self.stat_expired = self._card("EXPIRADOS", "0", Theme.DANGER)
        self.stat_tickets = self._card("TICKETS", "0", Theme.ACCENT)
        
        metrics_grid.addWidget(self.stat_active, 0, 0)
        metrics_grid.addWidget(self.stat_warn, 0, 1)
        metrics_grid.addWidget(self.stat_expired, 1, 0)
        metrics_grid.addWidget(self.stat_tickets, 1, 1)
        top_container.addLayout(metrics_grid, 1) # Flex 1
        
        # Right Side: Trend Insight Chart
        self.chart_container = QFrame()
        self.chart_container.setStyleSheet(f"background: white; border-radius: 12px; border: 1px solid #d1d8e0;")
        cl = QVBoxLayout(self.chart_container); cl.setContentsMargins(15, 15, 15, 15)
        cl.addWidget(QLabel("📈 TENDENCIA DE INGRESOS (6 M.)"), alignment=Qt.AlignCenter)
        self.chart = FinanceTrendChart()
        cl.addWidget(self.chart)
        top_container.addWidget(self.chart_container, 2) # Flex 2 (Wider chart)
        
        self.layout.addLayout(top_container)
        self.layout.addSpacing(15)
        
        # Bottom Region: Operations (Calendar | Upcoming Expiries)
        cal_lyt = QHBoxLayout(); cal_lyt.setSpacing(15)
        self.cal = QCalendarWidget(); self.cal.setFixedSize(400, 300); cal_lyt.addWidget(self.cal)
        
        vl = QVBoxLayout(); vl.addWidget(QLabel("📅 PRÓXIMOS VENCIMIENTOS (60 DÍAS)"))
        self.table = QTableWidget(0, 4); self.table.setHorizontalHeaderLabels(["Svc", "Cliente", "Fecha", "Acción"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        vl.addWidget(self.table); cal_lyt.addLayout(vl)
        self.layout.addLayout(cal_lyt)

        self.layout.addSpacing(20); self.layout.addWidget(QLabel("📜 ACTIVIDAD RECIENTE EN EL SISTEMA"))
        self.act_table = QTableWidget(0, 3); self.act_table.setHorizontalHeaderLabels(["Hora", "Tipo", "Evento"])
        self.act_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.act_table)
        
        self.refresh_data()

    def _card(self, t, v, c):
        f = QFrame(); f.setStyleSheet(f"background: {c}; border-radius: 12px; padding: 12px; color: white;")
        l = QVBoxLayout(f); l.addWidget(QLabel(t)); val = QLabel(v); val.setFont(QFont("Segoe UI", 22, QFont.Bold)); l.addWidget(val); f.v = val
        return f

    def refresh_data(self):
        BusinessLogic.update_all_service_statuses()
        self.stat_active.v.setText(str(Service.select().where(Service.status == ServiceStatus.ACTIVE).count()))
        self.stat_warn.v.setText(str(Service.select().where(Service.status == ServiceStatus.EXPIRING).count()))
        self.stat_expired.v.setText(str(Service.select().where(Service.status << [ServiceStatus.EXPIRED, ServiceStatus.GRACE]).count()))
        self.stat_tickets.v.setText(str(Ticket.select().where(Ticket.status == 'OPEN').count()))
        
        data = BusinessLogic.get_upcoming_expiries(60)
        self.table.setRowCount(0)
        if not data:
            it = QTableWidgetItem("Sin vencimientos próximos."); it.setTextAlignment(Qt.AlignCenter)
            self.table.insertRow(0); self.table.setItem(0, 0, it); self.table.setSpan(0, 0, 1, 4)
        else:
            for s in data:
                r = self.table.rowCount(); self.table.insertRow(r)
                items = [QTableWidgetItem(s.name), QTableWidgetItem(s.client.fullname), QTableWidgetItem(str(s.expiry_date))]
                for i, it in enumerate(items):
                    it.setTextAlignment(Qt.AlignCenter); self.table.setItem(r, i, it)
                
                act = QWidget(); acl = QHBoxLayout(act); acl.setContentsMargins(0,0,0,0); acl.setAlignment(Qt.AlignCenter); acl.setSpacing(5)
                btn_ren = QPushButton("⟳ RENOVAR"); btn_ren.setFixedSize(90, 24)
                btn_ren.setToolTip("Renovar este servicio inmediatamente")
                btn_ren.setStyleSheet(f"background: {Theme.ACCENT}; color: white; font-size: 9px; font-weight: bold;")
                btn_ren.clicked.connect(lambda ch, _id=s.id: self.quick_renew(_id))
                
                btn_wa = QPushButton("💬"); btn_wa.setFixedSize(30, 24)
                btn_wa.setToolTip("Notificar vencimiento por WhatsApp")
                btn_wa.setStyleSheet(f"background: {Theme.WHATSAPP}; color: white; border-radius: 4px;")
                btn_wa.clicked.connect(lambda ch, _c=s.client.id, _s=s.id: self.send_whatsapp('RENEW_REMINDER', _c, _s))
                
                btn_ml = QPushButton("✉️"); btn_ml.setFixedSize(30, 24)
                btn_ml.setToolTip("Notificar vencimiento por Email")
                btn_ml.setStyleSheet(f"background: {Theme.WARNING}; color: white; border-radius: 4px;")
                btn_ml.clicked.connect(lambda ch, _c=s.client.id, _s=s.id: self.send_email('RENEW_REMINDER', _c, _s))
                
                acl.addWidget(btn_ren); acl.addWidget(btn_wa); acl.addWidget(btn_ml); self.table.setCellWidget(r, 3, act)
        
        # Load Chart Data
        self.chart.set_data(BusinessLogic.get_revenue_history(6))
        self._refresh_activity()

    def _refresh_activity(self):
        self.act_table.setRowCount(0)
        for log in AuditLog.select().order_by(AuditLog.created_at.desc()).limit(10):
            r = self.act_table.rowCount(); self.act_table.insertRow(r)
            self.act_table.setItem(r, 0, QTableWidgetItem(log.created_at.strftime("%H:%M:%S")))
            self.act_table.setItem(r, 1, QTableWidgetItem(log.event_type))
            self.act_table.setItem(r, 2, QTableWidgetItem(log.description))

    def quick_renew(self, _id):
        # Professional Renewal Dialog with Auto-Billing Option
        d = QMessageBox(self)
        d.setWindowTitle("Procesar Renovación")
        d.setText("¿Deseas renovar este servicio por 1 año?")
        d.setIcon(QMessageBox.Question)
        btn_simple = d.addButton("RENOVAR SOLAMENTE", QMessageBox.ActionRole)
        btn_inv = d.addButton("🤖 RENOVAR + FACTURAR", QMessageBox.ActionRole)
        btn_cancel = d.addButton("CANCELAR", QMessageBox.RejectRole)
        
        d.exec()
        if d.clickedButton() == btn_cancel: return
        
        try:
            create_inv = (d.clickedButton() == btn_inv)
            BusinessLogic.mark_renewal_success(_id, create_invoice=create_inv)
            msg = "Servicio renovado." + ("\nFactura generada en Finanzas." if create_inv else "")
            QMessageBox.information(self, "Éxito", msg)
            self.refresh_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

class ClientView(BaseView):
    def __init__(self):
        super().__init__("Base de Clientes")
        bar = QHBoxLayout()
        self.search = QLineEdit(placeholderText="🔍 Buscar cliente por nombre/email...")
        self.search.textChanged.connect(self.refresh_data)
        bar.addWidget(self.search)
        self.btn_new = QPushButton("+ NUEVO CLIENTE")
        self.btn_new.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px; font-weight: bold;")
        self.btn_new.clicked.connect(self.add_client); bar.addWidget(self.btn_new)
        self.layout.addLayout(bar)
        
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nombre", "Email", "WhatsApp", "Servicios", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.layout.addWidget(self.table)
        self.refresh_data()

    def refresh_data(self):
        query = Client.select()
        if self.search.text(): query = query.where(Client.fullname.contains(self.search.text()) | Client.email.contains(self.search.text()))
        self.table.setRowCount(0)
        for c in query:
            r = self.table.rowCount(); self.table.insertRow(r)
            items = [QTableWidgetItem(c.fullname), QTableWidgetItem(c.email), 
                     QTableWidgetItem(c.whatsapp or "-"), QTableWidgetItem(str(c.services.count()))]
            for i, it in enumerate(items):
                it.setTextAlignment(Qt.AlignCenter); self.table.setItem(r, i, it)
            
            act = QWidget(); acl = QHBoxLayout(act); acl.setContentsMargins(0,0,0,0); acl.setSpacing(10); acl.setAlignment(Qt.AlignCenter)
            b_wa = QPushButton("💬"); b_wa.setFixedSize(36, 36); b_wa.setToolTip("Abrir Chat WhatsApp")
            b_wa.setStyleSheet(f"background: transparent; color: {Theme.WHATSAPP}; font-size: 18px;")
            b_wa.clicked.connect(lambda ch, _id=c.id: self.send_whatsapp('WELCOME_CLIENT', _id))
            
            b_ml = QPushButton("✉️"); b_ml.setFixedSize(36, 36); b_ml.setToolTip("Enviar Correo")
            b_ml.setStyleSheet(f"background: transparent; color: {Theme.WARNING}; font-size: 18px;")
            b_ml.clicked.connect(lambda ch, _id=c.id: self.send_email('WELCOME_CLIENT', _id))
            
            b_ed = QPushButton("✏️"); b_ed.setFixedSize(36, 36); b_ed.setToolTip("Editar información del cliente")
            b_ed.clicked.connect(lambda ch, _c=c: self.edit_client(_c))
            b_de = QPushButton("🗑️"); b_de.setFixedSize(36, 36); b_de.setToolTip("Eliminar cliente")
            b_de.clicked.connect(lambda ch, _id=c.id: self.del_client(_id))
            acl.addWidget(b_wa); acl.addWidget(b_ml); acl.addWidget(b_ed); acl.addWidget(b_de)
            self.table.setCellWidget(r, 4, act)

    def add_client(self): self._client_dialog()
    def edit_client(self, c): self._client_dialog(c)

    def _client_dialog(self, c=None):
        d = QDialog(self); d.setWindowTitle("Nuevo Cliente" if not c else f"Editar: {c.fullname}"); d.setMinimumWidth(450)
        fl = QFormLayout(d); fl.setSpacing(12)
        n, e = QLineEdit(c.fullname if c else ""), QLineEdit(c.email if c else "")
        ph, wa = QLineEdit(c.phone if c else ""), QLineEdit(c.whatsapp if c else "")
        tid = QLineEdit(c.tax_id if c else "")
        
        btn = QPushButton("GUARDAR CLIENTE")
        btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 12px; font-weight: bold;")
        
        def save():
            try:
                if not n.text().strip() or not e.text().strip():
                    return QMessageBox.warning(d, "Validación", "Nombre y Email son requeridos.")
                if c: BusinessLogic.update_client(c.id, n.text().strip(), e.text().strip(), ph.text().strip(), wa.text().strip(), tid.text().strip())
                else: BusinessLogic.create_client(n.text().strip(), e.text().strip(), ph.text().strip(), wa.text().strip(), tid.text().strip())
                d.accept(); self.refresh_data()
            except Exception as ex: QMessageBox.critical(d, "Error", str(ex))

        fl.addRow("Nombre Completo:", n); fl.addRow("Email Principal:", e)
        fl.addRow("📞 Celular:", ph); fl.addRow("💬 WhatsApp:", wa)
        fl.addRow("🆔 Tax ID/RUC:", tid)
        fl.addRow("", btn)
        btn.clicked.connect(save); d.exec()

    def del_client(self, _id):
        if QMessageBox.warning(self, "Eliminar", "¿Estás seguro?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            try: BusinessLogic.delete_client(_id); self.refresh_data()
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

class InventoryView(BaseView):
    def __init__(self):
        super().__init__("Gestión de Inventario (Dominios y Hosting)")
        toolbar = QHBoxLayout()
        self.search = QLineEdit(placeholderText="🔍 Buscar dominio o cliente..."); toolbar.addWidget(self.search)
        self.btn_alta = QPushButton("REGISTRAR ALTA"); self.btn_alta.setStyleSheet(f"background: {Theme.SUCCESS}; color: white; padding: 10px;")
        self.btn_alta.clicked.connect(self.add_svc); toolbar.addWidget(self.btn_alta)
        self.layout.addLayout(toolbar)
        
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Servicio", "Cliente", "Tipo", "Vencimiento", "Precio", "Estado", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.layout.addWidget(self.table)
        self.search.textChanged.connect(self.refresh_data)
        self.refresh_data()

    def quick_add_prov(self, combo):
        d = QDialog(self); d.setWindowTitle("Nuevo Proveedor"); fl = QFormLayout(d)
        n = QLineEdit()
        btn = QPushButton("Añadir"); btn.clicked.connect(d.accept)
        fl.addRow("Nombre:", n); fl.addRow(btn)
        if d.exec() and n.text().strip():
            p = BusinessLogic.create_provider(n.text().strip())
            combo.addItem(p.name, p.id); combo.setCurrentText(p.name)

    def quick_add_type(self, combo):
        d = QDialog(self); d.setWindowTitle("Nueva Categoría"); fl = QFormLayout(d)
        n = QLineEdit()
        btn = QPushButton("Añadir"); btn.clicked.connect(d.accept)
        fl.addRow("Nombre:", n); fl.addRow(btn)
        if d.exec() and n.text().strip():
            st = BusinessLogic.create_service_type(n.text().strip().upper())
            combo.addItem(st.name); combo.setCurrentText(st.name)

    def refresh_data(self):
        q = Service.select().where(Service.status != ServiceStatus.CANCELLED)
        if self.search.text(): q = q.where(Service.name.contains(self.search.text()) | Service.client.fullname.contains(self.search.text()))
        self.table.setRowCount(0)
        if not q.exists():
            self.table.insertRow(0)
            self.table.setItem(0, 0, QTableWidgetItem("No se encontraron servicios.")); self.table.setSpan(0, 0, 1, 6)
            return

        for s in q:
            r = self.table.rowCount(); self.table.insertRow(r)
            items = [
                QTableWidgetItem(s.name), 
                QTableWidgetItem(s.client.fullname), 
                QTableWidgetItem(s.type),
                QTableWidgetItem(str(s.expiry_date)), 
                QTableWidgetItem(f"${s.selling_price:.2f}")
            ]
            for i, it in enumerate(items):
                it.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, i, it)
            
            # Status Badge Logic
            st_item = QTableWidgetItem(s.status)
            st_item.setTextAlignment(Qt.AlignCenter)
            if s.status == ServiceStatus.ACTIVE: st_item.setForeground(QColor("#27ae60"))
            elif s.status == ServiceStatus.EXPIRING: st_item.setForeground(QColor("#f39c12"))
            else: st_item.setForeground(QColor("#c0392b"))
            self.table.setItem(r, 5, st_item)
            
            # Actions: Button Group
            actions = QWidget(); al = QHBoxLayout(actions); al.setContentsMargins(0,0,0,0); al.setSpacing(5); al.setAlignment(Qt.AlignCenter)
            b_wa = QPushButton("💬"); b_wa.setFixedSize(32, 32); b_wa.setToolTip("Notificar por WhatsApp")
            b_wa.setStyleSheet(f"color: {Theme.WHATSAPP};")
            b_wa.clicked.connect(lambda ch, _c=s.client.id, _s=s.id: self.send_whatsapp('RENEW_REMINDER', _c, _s))
            
            b_ml = QPushButton("✉️"); b_ml.setFixedSize(32, 32); b_ml.setToolTip("Notificar por Email")
            b_ml.setStyleSheet(f"color: {Theme.WARNING};")
            b_ml.clicked.connect(lambda ch, _c=s.client.id, _s=s.id: self.send_email('RENEW_REMINDER', _c, _s))
            
            b_ed = QPushButton("✏️"); b_ed.setFixedSize(32, 32); b_ed.setToolTip("Editar Detalles"); b_ed.clicked.connect(lambda ch, _s=s: self.edit_svc(_s))
            b_ren = QPushButton("⟳"); b_ren.setFixedSize(32, 32); b_ren.setToolTip("Renovar Servicio"); b_ren.clicked.connect(lambda ch, _id=s.id: self.ren(_id))
            b_baj = QPushButton("✕"); b_baj.setFixedSize(32, 32); b_baj.setToolTip("Dar de Baja"); b_baj.clicked.connect(lambda ch, _id=s.id: self.baj(_id))
            b_not = QPushButton("📝"); b_not.setFixedSize(32, 32); b_not.setToolTip("Notas e Historial"); b_not.clicked.connect(lambda ch, _id=s.id: self.view_notes(_id))
            al.addWidget(b_wa); al.addWidget(b_ml); al.addWidget(b_ed); al.addWidget(b_ren); al.addWidget(b_baj); al.addWidget(b_not)
            self.table.setCellWidget(r, 6, actions)

    def edit_svc(self, s):
        self._svc_dialog(s)

    def add_svc(self):
        self._svc_dialog()

    def _svc_dialog(self, s=None):
        title = "Alta de Nuevo Servicio" if not s else f"Editar Servicio: {s.name}"
        d = QDialog(self); d.setWindowTitle(title); d.setMinimumWidth(550)
        l = QFormLayout(d); l.setSpacing(12); l.setContentsMargins(25, 25, 25, 25)
        
        c = QComboBox(); [c.addItem(cl.fullname, cl.id) for cl in Client.select()]
        if s: c.setCurrentText(s.client.fullname)
        
        p_cont = QWidget(); p_lyt = QHBoxLayout(p_cont); p_lyt.setContentsMargins(0,0,0,0); p_lyt.setSpacing(8)
        p = QComboBox(); [p.addItem(prov.name, prov.id) for prov in Provider.select()]
        if s: p.setCurrentText(s.provider.name)
        btn_p = QPushButton("+"); btn_p.setFixedSize(30, 30); btn_p.clicked.connect(lambda: self.quick_add_prov(p))
        p_lyt.addWidget(p); p_lyt.addWidget(btn_p)
        
        n = QLineEdit(s.name if s else "")
        
        t_cont = QWidget(); t_lyt = QHBoxLayout(t_cont); t_lyt.setContentsMargins(0,0,0,0); t_lyt.setSpacing(8)
        t = QComboBox(); [t.addItem(st.name) for st in ServiceType.select()]
        if s: t.setCurrentText(s.type)
        btn_t = QPushButton("+"); btn_t.setFixedSize(30, 30); btn_t.clicked.connect(lambda: self.quick_add_type(t))
        t_lyt.addWidget(t); t_lyt.addWidget(btn_t)
        
        e = QDateEdit(calendarPopup=True); e.setDate(s.expiry_date if s else datetime.date.today() + datetime.timedelta(days=365))
        pr = QLineEdit(str(s.selling_price) if s else "0.0")
        cost = QLineEdit(str(s.renewal_price) if s else "0.0")
        
        status = QComboBox(); status.addItems([ServiceStatus.ACTIVE, ServiceStatus.EXPIRING, ServiceStatus.EXPIRED, ServiceStatus.GRACE, ServiceStatus.CANCELLED])
        if s: status.setCurrentText(s.status)
        
        auto_r = QCheckBox("Renovación Automática"); auto_r.setChecked(s.auto_renew if s else False)
        notes = QTextEdit(); notes.setPlainText(s.notes if s else ""); notes.setMaximumHeight(80)
        
        btn_save = QPushButton("GUARDAR CAMBIOS" if s else "CREAR SERVICIO")
        btn_save.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 12px; font-weight: bold;")
        
        l.addRow("Cliente:", c)
        l.addRow("Proveedor:", p_cont)
        l.addRow("Nombre/Dominio:", n)
        l.addRow("Categoría:", t_cont)
        l.addRow("Vencimiento:", e)
        l.addRow("Precio Venta:", pr)
        l.addRow("Costo Proveedor:", cost)
        l.addRow("Estado:", status)
        l.addRow("", auto_r)
        l.addRow("Notas Internas:", notes)
        l.addRow("", btn_save)
        
        def save():
            try:
                if not n.text().strip(): return QMessageBox.warning(d, "Error", "El nombre es obligatorio.")
                p_v = float(pr.text().replace(',','.')); p_c = float(cost.text().replace(',','.'))
                
                if s:
                    BusinessLogic.update_service(
                        s.id, c.currentData(), p.currentData(), n.text().strip(),
                        t.currentText(), e.date().toPython(), p_v, p_c,
                        status.currentText(), auto_r.isChecked(), notes.toPlainText()
                    )
                else:
                    BusinessLogic.register_new_service(
                        c.currentData(), p.currentData(), n.text().strip(),
                        t.currentText(), e.date().toPython(), p_v, p_c
                    )
                d.accept(); self.refresh_data()
            except Exception as ex: QMessageBox.critical(d, "Error", str(ex))
            
        btn_save.clicked.connect(save); d.exec()

    def view_notes(self, _id):
        from app.models.database import Service
        s = Service.get_by_id(_id)
        d = QDialog(self); d.setWindowTitle(f"Historial de {s.name}"); d.setMinimumWidth(500)
        l = QVBoxLayout(d); txt = QTextEdit(); txt.setReadOnly(True)
        history = "\n".join([f"[{n.created_at}] {n.content}" for n in s.service_history])
        txt.setPlainText(history or "Sin notas registradas.")
        l.addWidget(txt); new_n = QLineEdit(placeholderText="Añadir nota..."); l.addWidget(new_n)
        btn = QPushButton("Guardar Nota"); btn.clicked.connect(lambda: [BusinessLogic.add_note(new_n.text(), service_id=_id), d.accept()])
        l.addWidget(btn); d.exec()

    def ren(self, _id):
        d = QMessageBox(self)
        d.setWindowTitle("Asistente de Renovación")
        d.setText("Seleccione el modo de renovación para este servicio:")
        btn_manual = d.addButton("Manual (Solo fechas)", QMessageBox.ActionRole)
        btn_auto = d.addButton("Robotizado (Renovar + Facturar)", QMessageBox.ActionRole)
        d.addButton("Cancelar", QMessageBox.RejectRole)
        
        d.exec()
        if d.clickedButton().text() == "Cancelar": return
        
        try:
            do_inv = (d.clickedButton() == btn_auto)
            BusinessLogic.mark_renewal_success(_id, create_invoice=do_inv)
            self.refresh_data()
            if do_inv: QMessageBox.information(self, "Robotizado", "Servicio extendido y factura generada exitosamente.")
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def baj(self, _id):
        if QMessageBox.warning(self, "Baja de Servicio", "¿Estás seguro?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            BusinessLogic.cancel_service(_id)
            self.refresh_data()


class CRMView(BaseView):
    def __init__(self):
        super().__init__("CRM: Soporte y Gestión Comercial")
        tabs = QTabWidget()
        self.layout.addWidget(tabs)
        
        # Tickets Tab
        t_tab = QWidget(); tl = QVBoxLayout(t_tab)
        tb = QHBoxLayout(); self.t_search = QLineEdit(placeholderText="🔍 Buscar tickets..."); tb.addWidget(self.t_search)
        self.btn_nt = QPushButton("+ TICKET"); self.btn_nt.clicked.connect(self.add_ticket); tb.addWidget(self.btn_nt)
        tl.addLayout(tb)
        self.t_table = QTableWidget(0, 5); self.t_table.setHorizontalHeaderLabels(["Sujeto", "Cliente", "Estatus", "Prioridad", "Acciones"])
        self.t_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.t_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.t_table.setSelectionBehavior(QTableWidget.SelectRows)
        tl.addWidget(self.t_table); tabs.addTab(t_tab, "Tickets")
        
        # Offers Tab
        o_tab = QWidget(); ol = QVBoxLayout(o_tab)
        ob = QHBoxLayout(); self.o_search = QLineEdit(placeholderText="🔍 Buscar ofertas..."); ob.addWidget(self.o_search)
        self.btn_no = QPushButton("+ OFERTA"); self.btn_no.clicked.connect(self.add_offer); ob.addWidget(self.btn_no)
        ol.addLayout(ob)
        self.o_table = QTableWidget(0, 5); self.o_table.setHorizontalHeaderLabels(["Asunto", "Cliente", "Vence", "Estatus", "Acciones"])
        self.o_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.o_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.o_table.setSelectionBehavior(QTableWidget.SelectRows)
        ol.addWidget(self.o_table); tabs.addTab(o_tab, "Cotizaciones")

        # Tasks Tab
        tk_tab = QWidget(); tkl = QVBoxLayout(tk_tab)
        tkb = QHBoxLayout(); self.tk_search = QLineEdit(placeholderText="🔍 Buscar tareas..."); tkb.addWidget(self.tk_search)
        self.btn_nk = QPushButton("+ TAREA"); self.btn_nk.clicked.connect(self.add_task); tkb.addWidget(self.btn_nk)
        tkl.addLayout(tkb)
        self.tk_table = QTableWidget(0, 4); self.tk_table.setHorizontalHeaderLabels(["Tarea", "Vence", "Estado", "Acciones"])
        self.tk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tk_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tk_table.setSelectionBehavior(QTableWidget.SelectRows)
        tkl.addWidget(self.tk_table); tabs.addTab(tk_tab, "Tareas")

        # Templates Tab
        tm_tab = QWidget(); tml = QVBoxLayout(tm_tab)
        tmb = QHBoxLayout(); self.tm_search = QLineEdit(placeholderText="🔍 Buscar plantillas..."); tmb.addWidget(self.tm_search)
        self.btn_ntm = QPushButton("+ PLANTILLA"); self.btn_ntm.clicked.connect(self.add_template); tmb.addWidget(self.btn_ntm)
        tml.addLayout(tmb)
        self.tm_table = QTableWidget(0, 4); self.tm_table.setHorizontalHeaderLabels(["Nombre", "Asunto", "Tipo", "Acciones"])
        self.tm_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tm_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tm_table.setSelectionBehavior(QTableWidget.SelectRows)
        tml.addWidget(self.tm_table); tabs.addTab(tm_tab, "Plantillas")
        
        # Events
        self.t_search.textChanged.connect(self.refresh_data)
        self.o_search.textChanged.connect(self.refresh_data)
        self.tk_search.textChanged.connect(self.refresh_data)
        self.tm_search.textChanged.connect(self.refresh_data)
        self.refresh_data()

    def refresh_data(self):
        from app.models.database import Ticket, Offer, Task, MessageTemplate, AuditLog
        
        # Helper for common table styling
        def style_mgr(t):
            t.verticalHeader().setDefaultSectionSize(50)
            t.verticalHeader().setVisible(False)
            t.setStyleSheet("QTableWidget::item { border-bottom: 1px solid #f1f2f6; }")

        # 1. Tickets Table
        style_mgr(self.t_table)
        self.t_table.setRowCount(0)
        t_q = Ticket.select().order_by(Ticket.created_at.desc())
        if self.t_search.text(): t_q = t_q.where(Ticket.subject.contains(self.t_search.text()))
        for t in t_q:
            r = self.t_table.rowCount(); self.t_table.insertRow(r)
            items = [QTableWidgetItem(t.subject), QTableWidgetItem(t.client.fullname), 
                     QTableWidgetItem(t.status), QTableWidgetItem(t.priority)]
            for i, it in enumerate(items):
                it.setTextAlignment(Qt.AlignCenter); self.t_table.setItem(r, i, it)
            
            act = QWidget(); acl = QHBoxLayout(act); acl.setContentsMargins(0,0,0,0); acl.setAlignment(Qt.AlignCenter); acl.setSpacing(8)
            b_dt = QPushButton("ℹ️"); b_dt.setFixedSize(32, 32); b_dt.setToolTip("Ver Detalles")
            b_dt.clicked.connect(lambda ch, _t=t: self.view_ticket_details(_t))
            b_ed = QPushButton("✏️"); b_ed.setFixedSize(32, 32); b_ed.setToolTip("Editar Ticket")
            b_ed.clicked.connect(lambda ch, _t=t: self.edit_ticket(_t))
            b_cl = QPushButton("🏁"); b_cl.setFixedSize(32, 32); b_cl.setToolTip("Cerrar Ticket")
            b_cl.setEnabled(t.status != 'CLOSED'); b_cl.clicked.connect(lambda ch, _id=t.id: self.close_ticket(_id))
            b_de = QPushButton("🗑️"); b_de.setFixedSize(32, 32); b_de.setToolTip("Eliminar Ticket")
            b_de.clicked.connect(lambda ch, _id=t.id: self.delete_ticket(_id))
            acl.addWidget(b_dt); acl.addWidget(b_ed); acl.addWidget(b_cl); acl.addWidget(b_de)
            self.t_table.setCellWidget(r, 4, act)

        # 2. Offers (Cotizaciones) Table
        style_mgr(self.o_table)
        self.o_table.setRowCount(0)
        o_q = Offer.select().order_by(Offer.created_at.desc())
        if self.o_search.text(): o_q = o_q.where(Offer.subject.contains(self.o_search.text()))
        for o in o_q:
            r = self.o_table.rowCount(); self.o_table.insertRow(r)
            items = [QTableWidgetItem(str(o.subject)), QTableWidgetItem(o.client.fullname), 
                     QTableWidgetItem(str(o.expiry_date)), QTableWidgetItem(str(o.status))]
            for i, it in enumerate(items):
                it.setTextAlignment(Qt.AlignCenter); self.o_table.setItem(r, i, it)
            
            act = QWidget(); acl = QHBoxLayout(act); acl.setContentsMargins(0,0,0,0); acl.setAlignment(Qt.AlignCenter); acl.setSpacing(8)
            btn_ok = QPushButton("✅"); btn_ok.setFixedSize(32, 32); btn_ok.setToolTip("Marcar como VENDIDO")
            btn_ok.setEnabled(o.status != 'CLAIMED')
            btn_ok.clicked.connect(lambda ch, _o=o: [setattr(_o, 'status', 'CLAIMED'), _o.save(), self.refresh_data()])
            btn_ed = QPushButton("✏️"); btn_ed.setFixedSize(32, 32); btn_ed.setToolTip("Editar Cotización")
            btn_ed.clicked.connect(lambda ch, _o=o: self.edit_offer(_o))
            btn_de = QPushButton("🗑️"); btn_de.setFixedSize(32, 32); btn_de.setToolTip("Eliminar Cotización")
            btn_de.clicked.connect(lambda ch, _id=o.id: self.delete_offer(_id))
            acl.addWidget(btn_ok); acl.addWidget(btn_ed); acl.addWidget(btn_de)
            self.o_table.setCellWidget(r, 4, act)

        # 3. Tasks (Tareas) Table
        style_mgr(self.tk_table)
        self.tk_table.setRowCount(0)
        tk_q = Task.select().order_by(Task.is_completed.asc(), Task.due_date.asc())
        if self.tk_search.text(): tk_q = tk_q.where(Task.title.contains(self.tk_search.text()))
        for tk in tk_q:
            r = self.tk_table.rowCount(); self.tk_table.insertRow(r)
            items = [QTableWidgetItem(tk.title), QTableWidgetItem(str(tk.due_date)), 
                     QTableWidgetItem("✅ Hecho" if tk.is_completed else "🕒 Pendiente")]
            for i, it in enumerate(items):
                it.setTextAlignment(Qt.AlignCenter); self.tk_table.setItem(r, i, it)
            
            act = QWidget(); acl = QHBoxLayout(act); acl.setContentsMargins(0,0,0,0); acl.setAlignment(Qt.AlignCenter); acl.setSpacing(8)
            btn_ed = QPushButton("✏️"); btn_ed.setFixedSize(32, 32); btn_ed.setToolTip("Editar Tarea")
            btn_ed.clicked.connect(lambda ch, _tk=tk: self.edit_task(_tk))
            btn_dn = QPushButton("✔️"); btn_dn.setFixedSize(32, 32); btn_dn.setToolTip("Marcar como Completada")
            btn_dn.setEnabled(not tk.is_completed)
            btn_dn.clicked.connect(lambda ch, _tk=tk: [setattr(_tk, 'is_completed', True), _tk.save(), self.refresh_data()])
            btn_de = QPushButton("🗑️"); btn_de.setFixedSize(32, 32); btn_de.setToolTip("Eliminar Tarea")
            btn_de.clicked.connect(lambda ch, _id=tk.id: self.delete_task(_id))
            acl.addWidget(btn_ed); acl.addWidget(btn_dn); acl.addWidget(btn_de)
            self.tk_table.setCellWidget(r, 3, act)

        # 4. Templates (Plantillas) Table
        style_mgr(self.tm_table)
        self.tm_table.setRowCount(0)
        tm_q = MessageTemplate.select().order_by(MessageTemplate.name)
        if self.tm_search.text(): tm_q = tm_q.where(MessageTemplate.name.contains(self.tm_search.text()) | MessageTemplate.subject.contains(self.tm_search.text()))
        for tm in tm_q:
            r = self.tm_table.rowCount(); self.tm_table.insertRow(r)
            items = [QTableWidgetItem(tm.name), QTableWidgetItem(tm.subject), QTableWidgetItem(tm.type)]
            for i, it in enumerate(items):
                it.setTextAlignment(Qt.AlignCenter); self.tm_table.setItem(r, i, it)
            
            act = QWidget(); acl = QHBoxLayout(act); acl.setContentsMargins(0,0,0,0); acl.setAlignment(Qt.AlignCenter); acl.setSpacing(8)
            b_pv = QPushButton("📄"); b_pv.setFixedSize(32, 32); b_pv.setToolTip("Previsualizar"); b_pv.clicked.connect(lambda ch, _tm=tm: self.preview_template(_tm))
            b_ed = QPushButton("✏️"); b_ed.setFixedSize(32, 32); b_ed.setToolTip("Editar"); b_ed.clicked.connect(lambda ch, _tm=tm: self.edit_template(_tm))
            b_de = QPushButton("🗑️"); b_de.setFixedSize(32, 32); b_de.setToolTip("Eliminar"); b_de.clicked.connect(lambda ch, _id=tm.id: self.del_template(_id))
            acl.addWidget(b_pv); acl.addWidget(b_ed); acl.addWidget(b_de); self.tm_table.setCellWidget(r, 3, act)

    def view_ticket_details(self, t):
        QMessageBox.information(self, f"Ticket #{t.id}: {t.subject}", f"CLIENTE: {t.client.fullname}\n\nDETALLE:\n{t.description}\n\nESTATUS: {t.status}\nPRIORIDAD: {t.priority}")

    def close_ticket(self, tid):
        if QMessageBox.question(self, "Cerrar Ticket", "¿Cerrar y archivar este ticket?") == QMessageBox.Yes:
            from app.models.database import Ticket
            t = Ticket.get_by_id(tid)
            t.status = 'CLOSED'; t.save()
            AuditLog.create(event_type='TICKET', description=f"Ticket #{tid} cerrado.")
            self.refresh_data()

    def edit_ticket(self, t):
        d = QDialog(self); d.setWindowTitle(f"Editar Ticket #{t.id}"); d.setMinimumWidth(450)
        l = QFormLayout(d); l.setSpacing(10)
        sub = QLineEdit(t.subject)
        desc = QTextEdit(); desc.setPlainText(t.description)
        prio = QComboBox(); prio.addItems(['LOW', 'NORMAL', 'HIGH', 'URGENT']); prio.setCurrentText(t.priority)
        status = QComboBox(); status.addItems(['OPEN', 'PENDING', 'CLOSED']); status.setCurrentText(t.status)
        l.addRow("Asunto:", sub); l.addRow("Descripción:", desc)
        l.addRow("Prioridad:", prio); l.addRow("Estado:", status)
        btn = QPushButton("Guardar Cambios")
        btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;")
        l.addRow(btn)
        def save():
            t.subject = sub.text().strip(); t.description = desc.toPlainText().strip()
            t.priority = prio.currentText(); t.status = status.currentText()
            t.save(); d.accept(); self.refresh_data()
        btn.clicked.connect(save); d.exec()

    def delete_ticket(self, tid):
        if QMessageBox.warning(self, "Eliminar", "¿Eliminar permanentemente este ticket?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            from app.models.database import Ticket
            Ticket.delete_by_id(tid)
            AuditLog.create(event_type='DELETE', description=f"Ticket #{tid} eliminado.")
            self.refresh_data()

    def edit_offer(self, o):
        d = QDialog(self); d.setWindowTitle(f"Editar Cotización #{o.id}"); d.setMinimumWidth(450)
        l = QFormLayout(d); l.setSpacing(10)
        sub = QLineEdit(o.subject)
        content = QTextEdit(); content.setPlainText(o.content)
        exp = QDateEdit(); exp.setCalendarPopup(True); exp.setDate(o.expiry_date)
        status = QComboBox(); status.addItems(['SENT', 'CLAIMED', 'EXPIRED']); status.setCurrentText(o.status)
        l.addRow("Asunto:", sub); l.addRow("Contenido:", content)
        l.addRow("Validez:", exp); l.addRow("Estado:", status)
        btn = QPushButton("Guardar Cambios")
        btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;"); l.addRow(btn)
        def save():
            o.subject = sub.text().strip(); o.content = content.toPlainText()
            o.expiry_date = exp.date().toPython(); o.status = status.currentText()
            o.save(); d.accept(); self.refresh_data()
        btn.clicked.connect(save); d.exec()

    def delete_offer(self, oid):
        if QMessageBox.warning(self, "Eliminar", "¿Eliminar esta cotización?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            from app.models.database import Offer
            Offer.delete_by_id(oid); self.refresh_data()

    def edit_task(self, tk):
        d = QDialog(self); d.setWindowTitle("Editar Tarea"); d.setMinimumWidth(400)
        l = QFormLayout(d); l.setSpacing(10)
        title = QLineEdit(tk.title)
        due = QDateEdit(); due.setCalendarPopup(True); due.setDate(tk.due_date)
        prio = QComboBox(); prio.addItems(['NORMAL', 'HIGH', 'URGENT']); prio.setCurrentText(tk.priority)
        l.addRow("Título:", title); l.addRow("Fecha límite:", due); l.addRow("Prioridad:", prio)
        btn = QPushButton("Guardar Cambios")
        btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;"); l.addRow(btn)
        def save():
            tk.title = title.text().strip(); tk.due_date = due.date().toPython()
            tk.priority = prio.currentText(); tk.save(); d.accept(); self.refresh_data()
        btn.clicked.connect(save); d.exec()

    def delete_task(self, tid):
        if QMessageBox.warning(self, "Eliminar", "¿Eliminar esta tarea?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            from app.models.database import Task
            Task.delete_by_id(tid); self.refresh_data()

    def add_template(self):
        self._template_dialog()

    def edit_template(self, tm):
        self._template_dialog(tm)

    def _template_dialog(self, tm=None):
        d = QDialog(self); d.setWindowTitle("Plantilla de Mensaje" if not tm else f"Editar: {tm.name}"); d.setMinimumWidth(500)
        l = QFormLayout(d)
        n = QLineEdit(tm.name if tm else ""); s = QLineEdit(tm.subject if tm else "")
        b = QTextEdit(); b.setPlainText(tm.body if tm else "")
        t = QComboBox(); t.addItems(["RENEWAL", "WELCOME", "WARNING", "OTHER"])
        if tm: t.setCurrentText(tm.type)
        
        l.addRow("Nombre Interno:", n); l.addRow("Asunto Email:", s); l.addRow("Contenido:", b); l.addRow("Tipo:", t)
        btn = QPushButton("Guardar Cambios" if tm else "Crear Plantilla")
        btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;")
        l.addRow(btn)
        
        def save():
            if not n.text() or not s.text() or not b.toPlainText():
                QMessageBox.warning(d, "Error", "Todos los campos son obligatorios.")
                return
            BusinessLogic.save_template(n.text(), s.text(), b.toPlainText(), t.currentText(), tm.id if tm else None)
            d.accept(); self.refresh_data()

        btn.clicked.connect(save)
        d.exec()

    def del_template(self, _id):
        if QMessageBox.warning(self, "Eliminar", "¿Estás seguro de eliminar esta plantilla?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            BusinessLogic.delete_template(_id)
            self.refresh_data()

    def preview_template(self, tm):
        d = QDialog(self); d.setWindowTitle(f"Vista Previa: {tm.name}"); d.setMinimumWidth(400)
        l = QVBoxLayout(d); l.addWidget(QLabel(f"<b>Asunto:</b> {tm.subject}"))
        txt = QTextEdit(); txt.setPlainText(tm.body); txt.setReadOnly(True); l.addWidget(txt)
        cl = QPushButton("Cerrar"); cl.clicked.connect(d.accept); l.addWidget(cl)
        d.exec()

    def add_ticket(self):
        d = QDialog(self); d.setWindowTitle("Nuevo Ticket"); d.setMinimumWidth(450)
        l = QFormLayout(d); l.setSpacing(10)
        c = QComboBox(); [c.addItem(i.fullname, i.id) for i in Client.select()]
        s = QComboBox(); s.addItem("Soporte General", None); [s.addItem(i.name, i.id) for i in Service.select()]
        sub = QLineEdit(); desc = QTextEdit(); prio = QComboBox(); prio.addItems(["LOW", "NORMAL", "HIGH", "URGENT"])
        l.addRow("Cliente:", c); l.addRow("Servicio:", s); l.addRow("Asunto:", sub); l.addRow("Detalle:", desc); l.addRow("Prioridad:", prio)
        b = QPushButton("Abrir Ticket"); b.clicked.connect(d.accept); l.addRow(b)
        if d.exec():
            BusinessLogic.create_ticket(c.currentData(), s.currentData(), sub.text().strip(), desc.toPlainText().strip(), prio.currentText())
            self.refresh_data()

    def add_task(self):
        d = QDialog(self); d.setWindowTitle("Nueva Tarea"); d.setMinimumWidth(400)
        l = QFormLayout(d); l.setSpacing(10)
        t = QLineEdit(); e = QDateEdit(); e.setCalendarPopup(True); e.setDate(datetime.date.today())
        p = QComboBox(); p.addItems(["NORMAL", "HIGH", "URGENT"])
        l.addRow("Título:", t); l.addRow("Fecha:", e); l.addRow("Prioridad:", p)
        b = QPushButton("Guardar Tarea"); b.clicked.connect(d.accept); l.addRow(b)
        if d.exec():
            BusinessLogic.create_task(t.text().strip(), e.date().toPython(), p.currentText())
            self.refresh_data()

    def add_offer(self):
        d = QDialog(self); d.setWindowTitle("Nueva Cotización"); d.setMinimumWidth(450)
        l = QFormLayout(d); l.setSpacing(10)
        c = QComboBox(); [c.addItem(i.fullname, i.id) for i in Client.select()]
        su = QLineEdit(); co = QTextEdit(); e = QDateEdit(); e.setCalendarPopup(True); e.setDate(datetime.date.today() + datetime.timedelta(days=15))
        l.addRow("Cliente:", c); l.addRow("Asunto:", su); l.addRow("Contenido:", co); l.addRow("Validez:", e)
        b = QPushButton("Registrar Oferta"); b.clicked.connect(d.accept); l.addRow(b)
        if d.exec():
            BusinessLogic.create_offer(c.currentData(), su.text().strip(), co.toPlainText().strip(), e.date().toPython())
            self.refresh_data()

class FacturacionView(BaseView):
    def __init__(self):
        super().__init__("Finanzas y Facturación Profesional")
        hb = QHBoxLayout(); self.summary = QLabel("Cargando sumario..."); hb.addWidget(self.summary)
        self.btn_new = QPushButton("+ FACTURA MANUAL"); self.btn_new.clicked.connect(self.add_inv); hb.addWidget(self.btn_new)
        self.layout.addLayout(hb)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Nro Factura", "Cliente", "Monto", "Pagado", "Estado", "Acciones"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.layout.addWidget(self.table)
        self.refresh_data()

    def add_inv(self):
        d = QDialog(self); d.setWindowTitle("Crear Factura Ad-hoc"); l = QFormLayout(d)
        c = QComboBox(); [c.addItem(cl.fullname, cl.id) for cl in Client.select()]
        num = QLineEdit(f"FAC-{datetime.datetime.now().strftime('%M%S')}")
        amt = QLineEdit("0.0"); due = QDateEdit(); due.setCalendarPopup(True); due.setDate(datetime.date.today())
        l.addRow("Cliente:", c); l.addRow("Nro:", num); l.addRow("Monto:", amt); l.addRow("Vence:", due)
        b = QPushButton("Emitir Factura"); b.clicked.connect(d.accept); l.addRow(b)
        if d.exec():
            BusinessLogic.create_manual_invoice(c.currentData(), num.text(), float(amt.text()), due.date().toPython())
            self.refresh_data()

    def refresh_data(self):
        from app.models.database import Invoice
        self.table.setRowCount(0)
        s = BusinessLogic.get_financial_summary()
        self.summary.setText(f"💰 Sumario: Esperado: ${s['expected']:.2f} | Cobrado: ${s['collected']:.2f} | Pendiente: ${s['pending']:.2f}")

        for inv in Invoice.select():
            r = self.table.rowCount(); self.table.insertRow(r)
            data = [inv.number, inv.client.fullname, f"${inv.total_amount:.2f}", f"${inv.paid_amount:.2f}"]
            for i, val in enumerate(data):
                it = QTableWidgetItem(val); it.setTextAlignment(Qt.AlignCenter); self.table.setItem(r, i, it)
            
            st_item = QTableWidgetItem(inv.status); st_item.setTextAlignment(Qt.AlignCenter)
            if inv.status == 'PAID': st_item.setForeground(QColor(Theme.SUCCESS))
            elif inv.status == 'UNPAID': st_item.setForeground(QColor(Theme.DANGER))
            self.table.setItem(r, 4, st_item)

            # Actions Container
            actions = QWidget(); al = QHBoxLayout(actions); al.setContentsMargins(0,0,0,0); al.setSpacing(5); al.setAlignment(Qt.AlignCenter)

            if inv.status != 'PAID':
                btn = QPushButton("PAGAR"); btn.setFixedSize(60, 30); btn.setToolTip("Registrar Pago")
                btn.clicked.connect(lambda ch, _id=inv.id: self.register_pay(_id))
                btn.setStyleSheet(f"background: {Theme.SUCCESS}; color: white; font-size: 10px; font-weight: bold;")
                al.addWidget(btn)
            
            btn_pdf = QPushButton("📥"); btn_pdf.setFixedSize(32, 32); btn_pdf.setToolTip("Comprobante PDF")
            btn_pdf.clicked.connect(lambda ch, _id=inv.id: self.download_receipt(_id)); al.addWidget(btn_pdf)
            
            btn_del = QPushButton("🗑️"); btn_del.setFixedSize(32, 32); btn_del.setToolTip("Eliminar Factura")
            btn_del.clicked.connect(lambda ch, _id=inv.id: [BusinessLogic.delete_invoice(_id), self.refresh_data()]); al.addWidget(btn_del)
            
            self.table.setCellWidget(r, 5, actions)

    def download_receipt(self, _id):
        p, _ = QFileDialog.getSaveFileName(self, "Guardar Comprobante", f"comprobante_{_id}.pdf", "PDF (*.pdf)")
        if p:
            try:
                BusinessLogic.generate_invoice_pdf(_id, p)
                QMessageBox.information(self, "Éxito", "Comprobante generado correctamente.")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def register_pay(self, _id):
        from app.models.database import Invoice
        inv = Invoice.get_by_id(_id)
        d = QDialog(self); d.setWindowTitle(f"Registrar Pago: {inv.number}"); l = QFormLayout(d)
        amt = QLineEdit(str(inv.total_amount - inv.paid_amount))
        meth = QComboBox(); meth.addItems(["TRANSFERENCIA", "EFECTIVO", "TARJETA"])
        ref = QLineEdit()
        l.addRow("Monto a Pagar:", amt); l.addRow("Método:", meth); l.addRow("Referencia:", ref)
        b = QPushButton("Cargar Pago"); b.clicked.connect(d.accept); l.addRow(b)
        if d.exec():
            try:
                BusinessLogic.add_payment(_id, float(amt.text()), meth.currentText(), ref.text())
                self.refresh_data()
            except Exception as e: QMessageBox.critical(self, "Error", str(e))

class ReportsView(BaseView):
    def __init__(self):
        super().__init__("Reportes Financieros y Auditoría")
        grid = QGridLayout(); self.layout.addLayout(grid)
        
        self.btn_csv = QPushButton("📦 Inventario CSV"); self.btn_csv.clicked.connect(self.export_csv)
        self.btn_prov = QPushButton("🏢 Proveedores CSV"); self.btn_prov.clicked.connect(self.export_prov)
        self.btn_pdf = QPushButton("📅 Reporte Vencimientos (PDF)"); self.btn_pdf.clicked.connect(self.export_pdf)
        
        self.btn_bulk = QPushButton("🤖 FACTURACIÓN MASIVA (30 DÍAS)")
        self.btn_bulk.setStyleSheet(f"background: {Theme.WARNING}; color: white; font-weight: bold;")
        self.btn_bulk.clicked.connect(self.do_bulk_billing)
        
        self.btn_bu = QPushButton("💾 Backup Sistema"); self.btn_bu.clicked.connect(self.do_bu)
        self.btn_re = QPushButton("📂 Restaurar Backup"); self.btn_re.clicked.connect(self.do_re)
        self.btn_purge = QPushButton("🧹 Purgar Historial"); self.btn_purge.clicked.connect(self.do_purge)
        
        grid.addWidget(self.btn_csv, 0, 0); grid.addWidget(self.btn_prov, 0, 1); grid.addWidget(self.btn_pdf, 0, 2)
        grid.addWidget(self.btn_bulk, 1, 0); grid.addWidget(self.btn_bu, 1, 1); grid.addWidget(self.btn_purge, 1, 2)
        
        # Aging / Overdue Invoices
        self.layout.addWidget(QLabel("📅 FACTURACIÓN ATRASADA (Aging Report)"))
        self.aging_table = QTableWidget(0, 3); self.aging_table.setHorizontalHeaderLabels(["Factura", "Días Atraso", "Pendiente"])
        self.aging_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.aging_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.aging_table)

        # Risk Table
        self.layout.addWidget(QLabel("⚠️ CLIENTES EN RIESGO (Vencimientos ignorados)"))
        self.risk_table = QTableWidget(0, 2); self.risk_table.setHorizontalHeaderLabels(["Cliente", "Servicio Exp"])
        self.risk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.risk_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.risk_table)
        self.refresh_data()

    def refresh_data(self):
        # Risk data
        self.risk_table.setRowCount(0)
        clients_risk = Client.select().join(Service).where(Service.status << [ServiceStatus.EXPIRED, ServiceStatus.GRACE]).distinct()
        for c in clients_risk:
            r = self.risk_table.rowCount(); self.risk_table.insertRow(r)
            it0 = QTableWidgetItem(c.fullname); it0.setTextAlignment(Qt.AlignCenter); self.risk_table.setItem(r, 0, it0)
            svcs = ", ".join([s.name for s in c.services.where(Service.status << [ServiceStatus.EXPIRED, ServiceStatus.GRACE])])
            it1 = QTableWidgetItem(svcs); it1.setTextAlignment(Qt.AlignCenter); self.risk_table.setItem(r, 1, it1)
        
        # Aging data
        self.aging_table.setRowCount(0)
        overdue = BusinessLogic.get_aging_report()
        today = datetime.date.today()
        for inv in overdue:
            r = self.aging_table.rowCount(); self.aging_table.insertRow(r)
            days = (today - inv.due_date).days
            items = [QTableWidgetItem(inv.number), QTableWidgetItem(f"{days} días"), QTableWidgetItem(f"${inv.total_amount - inv.paid_amount:.2f}")]
            for i, it in enumerate(items):
                it.setTextAlignment(Qt.AlignCenter); self.aging_table.setItem(r, i, it)

    def export_csv(self):
        p, _ = QFileDialog.getSaveFileName(self, "Exportar CSV", "reporte.csv", "CSV (*.csv)")
        if p: BusinessLogic.export_services_csv(p); QMessageBox.information(self, "Exportar", "Ok.")

    def export_pdf(self):
        p, _ = QFileDialog.getSaveFileName(self, "Exportar PDF", "reporte.pdf", "PDF (*.pdf)")
        if p: BusinessLogic.export_report_pdf(p); QMessageBox.information(self, "Exportar", "Ok.")

    def export_prov(self):
        p, _ = QFileDialog.getSaveFileName(self, "Exportar Proveedores", "proveedores.csv", "CSV (*.csv)")
        if p: BusinessLogic.export_prov_csv(p); QMessageBox.information(self, "Exportar", "Ok.")

    def do_bu(self):
        p = backup_db('dhm_local.db', os.getcwd()); QMessageBox.information(self, "Backup", f"Generado en: {p}")

    def do_re(self):
        p, _ = QFileDialog.getOpenFileName(self, "Seleccionar Respaldo", "", "DB (*.db)")
        if p and restore_db(p, 'dhm_local.db'): QMessageBox.information(self, "Restaurar", "Ok. Reinicie.")

    def do_purge(self):
        if QMessageBox.warning(self, "Purgar Historial", "¿Eliminar registros de más de 90 días?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            c = BusinessLogic.purge_logs()
            QMessageBox.information(self, "Mantenimiento", f"Se eliminaron {c} registros antiguos.")
            self.refresh_data()

    def do_bulk_billing(self):
        msg = "¿Deseas generar facturas automáticamente de todos los servicios que vencen en los próximos 30 días?"
        if QMessageBox.question(self, "Robotizar Facturación", msg) == QMessageBox.Yes:
            count = BusinessLogic.generate_bulk_invoices(30)
            QMessageBox.information(self, "Proceso Completado", f"Se han generado {count} facturas nuevas exitosamente.")
            self.refresh_data()

class ConfigView(BaseView):
    def __init__(self):
        super().__init__("⚙️ PANEL DE CONFIGURACIÓN")
        tabs = QTabWidget(); self.layout.addWidget(tabs)
        
        # --- Providers Tab ---
        p_tab = QWidget(); p_lyt = QVBoxLayout(p_tab)
        btn_add_p = QPushButton("+ NUEVO PROVEEDOR")
        btn_add_p.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 8px; font-weight: bold;")
        btn_add_p.clicked.connect(self.add_provider)
        self.p_table = QTableWidget(0, 3); self.p_table.setHorizontalHeaderLabels(["Nombre", "Sitio Web", "Acciones"])
        self.p_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.p_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.p_table.setSelectionBehavior(QTableWidget.SelectRows)
        p_lyt.addWidget(btn_add_p); p_lyt.addWidget(self.p_table)
        tabs.addTab(p_tab, "Proveedores")
        
        # --- Categories Tab ---
        c_tab = QWidget(); c_lyt = QVBoxLayout(c_tab)
        btn_add_st = QPushButton("+ NUEVA CATEGORÍA")
        btn_add_st.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 8px; font-weight: bold;")
        btn_add_st.clicked.connect(self.add_stype)
        self.st_table = QTableWidget(0, 3); self.st_table.setHorizontalHeaderLabels(["Categoría", "Descripción", "Acciones"])
        self.st_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.st_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.st_table.setSelectionBehavior(QTableWidget.SelectRows)
        c_lyt.addWidget(btn_add_st); c_lyt.addWidget(self.st_table)
        tabs.addTab(c_tab, "Tipos de Servicio / Categorías")
        
        self.refresh_data()

    def refresh_data(self):
        # Providers
        self.p_table.setRowCount(0); self.p_table.verticalHeader().setDefaultSectionSize(45); self.p_table.verticalHeader().setVisible(False)
        for p in Provider.select():
            r = self.p_table.rowCount(); self.p_table.insertRow(r)
            for i, val in enumerate([p.name, p.website or "-"]):
                it = QTableWidgetItem(val); it.setTextAlignment(Qt.AlignCenter)
                self.p_table.setItem(r, i, it)
            act = QWidget(); al = QHBoxLayout(act); al.setContentsMargins(0,0,0,0); al.setAlignment(Qt.AlignCenter); al.setSpacing(8)
            b_ed = QPushButton("✏️"); b_ed.setFixedSize(32, 32); b_ed.setToolTip("Editar Proveedor")
            b_ed.clicked.connect(lambda ch, _p=p: self.edit_provider(_p))
            b_de = QPushButton("🗑️"); b_de.setFixedSize(32, 32); b_de.setToolTip("Eliminar Proveedor")
            b_de.clicked.connect(lambda ch, _id=p.id: self.delete_provider(_id))
            al.addWidget(b_ed); al.addWidget(b_de); self.p_table.setCellWidget(r, 2, act)
        
        # Categories
        self.st_table.setRowCount(0); self.st_table.verticalHeader().setDefaultSectionSize(45); self.st_table.verticalHeader().setVisible(False)
        for st in ServiceType.select():
            r = self.st_table.rowCount(); self.st_table.insertRow(r)
            for i, val in enumerate([st.name, st.description or "-"]):
                it = QTableWidgetItem(val); it.setTextAlignment(Qt.AlignCenter)
                self.st_table.setItem(r, i, it)
            act = QWidget(); al = QHBoxLayout(act); al.setContentsMargins(0,0,0,0); al.setAlignment(Qt.AlignCenter); al.setSpacing(8)
            b_ed = QPushButton("✏️"); b_ed.setFixedSize(32, 32); b_ed.setToolTip("Editar Categoría")
            b_ed.clicked.connect(lambda ch, _st=st: self.edit_stype(_st))
            b_de = QPushButton("🗑️"); b_de.setFixedSize(32, 32); b_de.setToolTip("Eliminar Categoría")
            b_de.clicked.connect(lambda ch, _id=st.id: self.delete_stype(_id))
            al.addWidget(b_ed); al.addWidget(b_de); self.st_table.setCellWidget(r, 2, act)

    def add_provider(self):
        d = QDialog(self); d.setWindowTitle("Nuevo Proveedor"); fl = QFormLayout(d)
        n, w = QLineEdit(), QLineEdit()
        btn = QPushButton("Guardar"); btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;"); btn.clicked.connect(d.accept)
        fl.addRow("Nombre:", n); fl.addRow("Web:", w); fl.addRow(btn)
        if d.exec() and n.text().strip(): BusinessLogic.create_provider(n.text().strip(), w.text().strip()); self.refresh_data()

    def edit_provider(self, p):
        d = QDialog(self); d.setWindowTitle(f"Editar: {p.name}"); fl = QFormLayout(d)
        n, w = QLineEdit(p.name), QLineEdit(p.website or "")
        btn = QPushButton("Guardar"); btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;"); btn.clicked.connect(d.accept)
        fl.addRow("Nombre:", n); fl.addRow("Web:", w); fl.addRow(btn)
        if d.exec() and n.text().strip():
            p.name = n.text().strip(); p.website = w.text().strip(); p.save(); self.refresh_data()

    def delete_provider(self, pid):
        if QMessageBox.warning(self, "Eliminar Proveedor", "¿Eliminar este proveedor? Los servicios asociados perderán su referencia.", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            Provider.delete_by_id(pid); self.refresh_data()

    def add_stype(self):
        d = QDialog(self); d.setWindowTitle("Nueva Categoría"); fl = QFormLayout(d)
        n, ds = QLineEdit(), QLineEdit()
        btn = QPushButton("Guardar"); btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;"); btn.clicked.connect(d.accept)
        fl.addRow("Nombre (ej. SEO):", n); fl.addRow("Descripción:", ds); fl.addRow(btn)
        if d.exec() and n.text().strip(): BusinessLogic.create_service_type(n.text().strip().upper(), ds.text().strip()); self.refresh_data()

    def edit_stype(self, st):
        d = QDialog(self); d.setWindowTitle(f"Editar: {st.name}"); fl = QFormLayout(d)
        n, ds = QLineEdit(st.name), QLineEdit(st.description or "")
        btn = QPushButton("Guardar"); btn.setStyleSheet(f"background: {Theme.ACCENT}; color: white; padding: 10px;"); btn.clicked.connect(d.accept)
        fl.addRow("Nombre:", n); fl.addRow("Descripción:", ds); fl.addRow(btn)
        if d.exec() and n.text().strip():
            st.name = n.text().strip().upper(); st.description = ds.text().strip(); st.save(); self.refresh_data()

    def delete_stype(self, sid):
        if QMessageBox.warning(self, "Eliminar Categoría", "¿Eliminar esta categoría de servicio?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            ServiceType.delete_by_id(sid); self.refresh_data()

class AuditLogView(BaseView):
    def __init__(self):
        super().__init__("Bitácora de Eventos (Auditoría)")
        self.search = QLineEdit(placeholderText="🔍 Filtrar bitácora por texto o tipo...")
        self.search.textChanged.connect(self.refresh_data)
        self.layout.addWidget(self.search)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Fecha/Hora", "Evento", "Descripción"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.layout.addWidget(self.table)
        self.refresh_data()

    def refresh_data(self):
        from app.models.database import AuditLog
        self.table.setRowCount(0)
        q = AuditLog.select().order_by(AuditLog.created_at.desc())
        if self.search.text():
            q = q.where(AuditLog.description.contains(self.search.text()) | AuditLog.event_type.contains(self.search.text()))
        logs = q.limit(200)
        for log in logs:
            r = self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(log.created_at)))
            self.table.setItem(r, 1, QTableWidgetItem(log.event_type))
            self.table.setItem(r, 2, QTableWidgetItem(log.description))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DHM Pro | Professional Reseller Management - Windows 11")
        self.resize(1280, 850)
        
        # Professional App-Wide Styles
        self.setStyleSheet(f"""
            QMainWindow, QDialog, QWidget {{ 
                background-color: {Theme.BG}; 
                font-family: 'Segoe UI Variable Text', 'Segoe UI', system-ui; 
                color: {Theme.PRIMARY};
            }}
            
            /* Enhanced Inputs & Form Fields */
            QLineEdit, QDateEdit, QComboBox, QTextEdit {{
                background-color: white;
                border: 1px solid #d1d8e0;
                border-radius: 6px;
                padding: 10px 15px;
                color: {Theme.PRIMARY};
                font-size: 13px;
                min-height: 40px; /* Better click ergonomics */
            }}
            QLineEdit:focus {{ border: 2px solid {Theme.ACCENT}; background-color: #fcfdfe; }}

            /* Critical Fix for Editable Cells in Tables */
            QTableWidget QLineEdit {{
                min-height: 35px;
                border: 2px solid {Theme.ACCENT};
                border-radius: 0px;
                padding: 5px;
            }}
            
            /* Professional Dashboard Cards & Frames */
            QFrame {{ border-radius: 8px; }}
            
            /* Main Buttons */
            QPushButton {{
                background-color: {Theme.ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 13px;
                min-height: 40px;
            }}
            QPushButton:hover {{ background-color: #2980b9; }}
            QPushButton:disabled {{ background-color: #bdc3c7; }}

            /* Action Buttons in Tables */
            QTableWidget QPushButton {{
                background-color: transparent;
                color: {Theme.SECONDARY};
                border-radius: 18px; 
                padding: 0px;
                min-width: 36px;
                max-width: 36px;
                min-height: 36px;
                max-height: 36px;
                font-size: 18px;
            }}
            QTableWidget QPushButton:hover {{ 
                background-color: #ebf3f9; 
                color: {Theme.ACCENT};
            }}

            /* Table Readability Overhaul */
            QTableWidget {{
                background-color: white;
                border: 1px solid #d1d8e0;
                border-radius: 8px;
                gridline-color: transparent;
                selection-background-color: #f1f7fe;
                selection-color: {Theme.PRIMARY};
                outline: none;
            }}
            QHeaderView::section {{
                background-color: #f8f9fa;
                color: {Theme.SECONDARY};
                padding: 12px;
                border: none;
                border-bottom: 2px solid #dcdde1;
                font-weight: bold;
                font-size: 11px;
                text-transform: uppercase;
            }}
            QTableWidget::item {{
                padding: 0px; 
                margin: 0px;
                border-bottom: 1px solid #f1f2f6;
            }}
            
            /* Critical Fix: Center items & expand editor to fill cell */
            QTableWidget QLineEdit {{
                padding: 0px;
                margin: 0px;
                border: 2px solid {Theme.ACCENT};
                background: white;
                selection-background-color: {Theme.ACCENT};
                qproperty-alignment: 'AlignCenter';
            }}
            
            /* Tabs */
            QTabBar::tab {{
                background: transparent;
                padding: 15px 25px;
                color: {Theme.SECONDARY};
                font-weight: bold;
                margin-right: 5px;
            }}
            QTabBar::tab:selected {{
                color: {Theme.ACCENT};
                border-bottom: 4px solid {Theme.ACCENT};
            }}
            
            /* Subtle & Elegant ToolTips */
            QToolTip {{
                background-color: #2f3640;
                color: white;
                border: 1px solid #3498db;
                border-radius: 4px;
                padding: 6px;
                font-size: 11px;
            }}
        """)
        
        initialize_db()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        lyt = QHBoxLayout(main_widget); lyt.setContentsMargins(0,0,0,0); lyt.setSpacing(0)
        
        # Sidebar Navigation
        self.sidebar = QFrame(); self.sidebar.setFixedWidth(260); self.sidebar.setStyleSheet(f"background: {Theme.PRIMARY}; border: none;")
        sl = QVBoxLayout(self.sidebar); sl.setContentsMargins(20, 50, 20, 20)
        
        brand = QLabel("DHM PRO v1.2 GOLD"); brand.setStyleSheet("color: white; font-size: 20px; font-weight: bold; margin-bottom: 40px;")
        sl.addWidget(brand)
        
        self.stack = QStackedWidget()
        
        # UI Polish: Force minimum row height for all future tables
        QApplication.instance().setStyleSheet(self.styleSheet() + "\nQHeaderView { min-height: 45px; }")

        nav = [
            ("🏠 DASHBOARD", DashboardView()),
            ("👥 CLIENTES", ClientView()),
            ("📦 INVENTARIO", InventoryView()),
            ("🎟️ CRM", CRMView()),
            ("📊 FINANZAS", FacturacionView()),
            ("⚙️ CONFIG", ConfigView()),
            ("📊 REPORTES", ReportsView()),
            ("📜 BITÁCORA", AuditLogView())
        ]
        
        for i, (name, view) in enumerate(nav):
            # Apply row height to each view's table(s) if they exist
            if hasattr(view, 'table'): 
                view.table.verticalHeader().setDefaultSectionSize(50)
                view.table.verticalHeader().setVisible(False)
            if hasattr(view, 'tm_table'): view.tm_table.verticalHeader().setDefaultSectionSize(50)
            if hasattr(view, 'o_table'): view.o_table.verticalHeader().setDefaultSectionSize(50)
            if hasattr(view, 'tk_table'): view.tk_table.verticalHeader().setDefaultSectionSize(50)
            if hasattr(view, 'aging_table'): view.aging_table.verticalHeader().setDefaultSectionSize(50)
            if hasattr(view, 'risk_table'): view.risk_table.verticalHeader().setDefaultSectionSize(50)
            if hasattr(view, 'act_table'): view.act_table.verticalHeader().setDefaultSectionSize(50)
        
        for i, (name, view) in enumerate(nav):
            b = QPushButton(f"  {name}")
            b.setCheckable(True); b.setAutoExclusive(True)
            b.setMinimumHeight(50)
            b.setStyleSheet("""
                QPushButton {
                    background: transparent; color: #a4b0be; text-align: left; 
                    padding: 10px; font-size: 13px; font-weight: bold; border: none;
                }
                QPushButton:hover { background: #2f3640; color: white; }
                QPushButton:checked { 
                    background: #3498db; color: white; border-right: 4px solid white; 
                }
            """)
            if i == 0: b.setChecked(True)
            b.clicked.connect(lambda ch, idx=i: self.stack.setCurrentIndex(idx))
            sl.addWidget(b); self.stack.addWidget(view)
        
        sl.addStretch()
        sl.addWidget(QLabel("DHM ENTERPRISE © 2026")); sl.addSpacing(10)
        
        lyt.addWidget(self.sidebar)
        lyt.addWidget(self.stack)
        
        # In-app background scan
        self.timer = QTimer(self); self.timer.timeout.connect(self.scan_reminders); self.timer.start(1200000); self.scan_reminders()

    def scan_reminders(self):
        n = BusinessLogic.generate_reminders_for_day()
        if n > 0: QMessageBox.warning(self, "Recordatorios Activos", f"Se han generado {n} alertas críticas para el día de hoy.")

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    login = LoginDialog()
    if login.exec(): 
        win = MainWindow()
        win.show()
        sys.exit(app.exec())
    else: 
        sys.exit(0)
