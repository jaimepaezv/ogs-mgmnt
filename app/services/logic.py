import datetime
import os
from fpdf import FPDF
from peewee import fn, JOIN
from app.models.database import initialize_db, Provider, Client, Service, ServiceStatus, ServiceType, Reminder, AuditLog, Offer, Note

class BusinessLogic:
    @staticmethod
    def update_all_service_statuses():
        """Recalculates status for all services based on current date."""
        today = datetime.date.today()
        services = Service.select()
        updated_count = 0
        
        for s in services:
            old_status = str(s.status)
            new_status = old_status
            
            # 1. Simple State Machine Logic
            if s.expiry_date < today:
                # Expired states
                diff = (today - s.expiry_date).days
                if diff <= 15:
                    new_status = ServiceStatus.EXPIRED
                elif 15 < diff <= 30:
                    new_status = ServiceStatus.GRACE
                elif 30 < diff <= 60:
                    new_status = ServiceStatus.REDEMPTION
                else:
                    new_status = ServiceStatus.CANCELLED
            elif s.expiry_date <= (today + datetime.timedelta(days=30)):
                # Expiring soon
                new_status = ServiceStatus.EXPIRING
            else:
                # Active
                new_status = ServiceStatus.ACTIVE
            
            if new_status != old_status:
                s.status = new_status
                s.save()
                AuditLog.create(
                    event_type='UPDATE',
                    description=f"Automated Status Change: {s.name} from {old_status} to {new_status}"
                )
                updated_count += 1
        
        return updated_count

    @staticmethod
    def mark_renewal_success(service_id, payment_amount=None, create_invoice=False):
        """Logic for manual renewal update with state-based rules + Automated Billing."""
        from app.models.database import Invoice, InvoiceItem, Payment
        s = Service.get_by_id(service_id)
        
        if s.status == ServiceStatus.CANCELLED:
            raise ValueError("No se puede renovar un servicio CANCELADO. Realice una Nueva Alta.")
        
        # Redemption case warning
        if s.status == ServiceStatus.REDEMPTION:
            AuditLog.create(event_type='WARNING', description=f"Renovación tardía en REDEMPTION para {s.name}. Verificar multa.")
        
        # Expiry Logic: Always +1 year from current expiry to maintain cycle
        new_expiry = s.expiry_date.replace(year=s.expiry_date.year + 1)
        old_expiry = s.expiry_date
        s.expiry_date = new_expiry
        s.status = ServiceStatus.ACTIVE
        s.save()
        
        inv = None
        if create_invoice:
            # Generate Automated Invoice
            inv_no = f"R-{datetime.date.today().year}-{s.id:04d}"
            inv = Invoice.create(
                client=s.client, 
                number=inv_no, 
                due_date=datetime.date.today(), 
                total_amount=s.selling_price,
                status='PAID' if payment_amount else 'UNPAID',
                paid_amount=payment_amount or 0.0,
                notes=f"Factura automática por renovación de {s.name}"
            )
            InvoiceItem.create(
                invoice=inv, 
                service=s, 
                description=f"Renovación de servicio: {s.name} (Ciclo {old_expiry} a {new_expiry})",
                unit_price=s.selling_price
            )
            if payment_amount:
                Payment.create(invoice=inv, amount=payment_amount, method='TRANSFER', reference='AUTO-RENEWAL')

        AuditLog.create(
            event_type='RENEW',
            description=f"Renovación exitosa: {s.name} ({'Con Factura' if create_invoice else 'Sin Factura'})"
        )
        return s, inv

    @staticmethod
    def generate_bulk_invoices(days=30):
        """Bulk Billing Engine: Generates invoices for all services expiring in the next X days."""
        from app.models.database import Invoice, InvoiceItem
        today = datetime.date.today()
        target_date = today + datetime.timedelta(days=days)
        
        # Find active services expiring within the window that don't have a pending invoice
        query = Service.select().where(
            (Service.status << [ServiceStatus.ACTIVE, ServiceStatus.EXPIRING]),
            (Service.expiry_date <= target_date),
            (Service.expiry_date >= today)
        )
        
        count = 0
        for s in query:
            # Check if an invoice for this service in this cycle already exists to avoid duplicates
            exists = InvoiceItem.select().join(Invoice).where(
                InvoiceItem.service == s,
                Invoice.created_at >= (datetime.datetime.now() - datetime.timedelta(days=60))
            ).exists()
            
            if not exists:
                inv_no = f"AUTO-{today.month:02d}{today.day:02d}-{s.id}"
                inv = Invoice.create(
                    client=s.client, 
                    number=inv_no, 
                    due_date=s.expiry_date, 
                    total_amount=s.selling_price,
                    status='UNPAID'
                )
                InvoiceItem.create(
                    invoice=inv, 
                    service=s, 
                    description=f"Pre-facturación por renovación: {s.name} (Vence {s.expiry_date})",
                    unit_price=s.selling_price
                )
                count += 1
        
        AuditLog.create(event_type='BILLING', description=f"Facturación masiva completada: {count} facturas generadas.")
        return count

    @staticmethod
    def get_upcoming_expiries(days=30):
        """Returns services expiring in X days."""
        limit = datetime.date.today() + datetime.timedelta(days=days)
        return Service.select().where(
            (Service.expiry_date <= limit) & 
            (Service.status != ServiceStatus.CANCELLED)
        ).order_by(Service.expiry_date)

    @staticmethod
    def cancel_service(service_id, reason="User Request"):
        """Flow for marking a service as CANCELLED (Baja)."""
        s = Service.get_by_id(service_id)
        old_status = s.status
        s.status = ServiceStatus.CANCELLED
        s.save()
        AuditLog.create(
            event_type='CANCEL',
            description=f"Service Cancelled: {s.name} (Baja). Old status: {old_status}. Reason: {reason}"
        )

    @staticmethod
    def register_new_service(client_id, provider_id, name, stype, expiry, price, cost=0.0):
        """Flow for 'Alta' (New Service) with date and margin validations."""
        today = datetime.date.today()
        if expiry <= today:
            raise ValueError("La fecha de expiración debe ser futura.")
        
        # Rule: Selling price should not be lower than cost (Warn only)
        if price < cost:
            AuditLog.create(event_type='WARNING', description=f"Precio venta (${price}) inferior al coste (${cost}) para {name}")

        s = Service.create(
            client=client_id,
            provider=provider_id,
            name=name,
            type=stype,
            registration_date=today,
            expiry_date=expiry,
            renewal_price=cost,
            selling_price=price,
            status=ServiceStatus.ACTIVE
        )
        AuditLog.create(
            event_type='CREATE',
            description=f"Alta de Servicio: {name} (Vence: {expiry})"
        )
        return s

    @staticmethod
    def create_ticket(client_id, service_id, subject, description, priority='NORMAL'):
        """Creates a professional ticket with auditing."""
        from app.models.database import Ticket
        t = Ticket.create(
            client=client_id, service=service_id, 
            subject=subject, description=description, 
            priority=priority, status='OPEN'
        )
        AuditLog.create(event_type='TICKET', description=f"Nuevo Ticket [{t.id}]: {subject}")
        return t

    @staticmethod
    def export_prov_csv(filepath):
        """Reports: Services grouped by Provider to CSV."""
        import pandas as pd
        q = Provider.select(Provider.name, fn.COUNT(Service.id).alias('count')).join(Service, JOIN.LEFT_OUTER).group_by(Provider.name)
        data = [{'Proveedor': r.name, 'Cant. Servicios': r.count} for r in q]
        pd.DataFrame(data).to_csv(filepath, index=False, encoding='utf-8-sig', sep=';')
        AuditLog.create(event_type='EXPORT', description="Exportación CSV por proveedor.")
        return filepath

    @staticmethod
    def create_client(fullname, email, phone=None, whatsapp=None, tax_id=None):
        """Creates a new client with auditing."""
        c = Client.create(fullname=fullname, email=email, phone=phone, whatsapp=whatsapp, tax_id=tax_id)
        AuditLog.create(event_type='CREATE', description=f"Nuevo Cliente: {fullname}")
        return c

    @staticmethod
    def update_client(client_id, fullname, email, phone=None, whatsapp=None, tax_id=None):
        """Updates client data with auditing."""
        c = Client.get_by_id(client_id)
        c.fullname, c.email = fullname, email
        c.phone, c.whatsapp, c.tax_id = phone, whatsapp, tax_id
        c.save()
        AuditLog.create(event_type='UPDATE', description=f"Cliente actualizado: {fullname}")
        return c

    @staticmethod
    def create_provider(name, website=""):
        p = Provider.create(name=name, website=website)
        AuditLog.create(event_type='CREATE', description=f"Proveedor añadido: {name}")
        return p

    @staticmethod
    def create_service_type(name, description=""):
        st = ServiceType.create(name=name, description=description)
        AuditLog.create(event_type='CREATE', description=f"Nueva Categoría: {name}")
        return st

    @staticmethod
    def delete_client(client_id):
        """Safely deletes a client if they have no active services."""
        c = Client.get_by_id(client_id)
        if c.services.count() > 0:
            raise ValueError("No se puede eliminar un cliente con servicios asociados.")
        name = c.fullname
        c.delete_instance()
        AuditLog.create(event_type='DELETE', description=f"Cliente eliminado: {name}")

    @staticmethod
    def update_service(service_id, client_id, provider_id, name, stype, expiry, price, cost, status, auto_renew=False, notes=""):
        """Updates ALL service details with auditing."""
        s = Service.get_by_id(service_id)
        s.client = client_id
        s.provider = provider_id
        s.name = name
        s.type = stype
        s.expiry_date = expiry
        s.selling_price = price
        s.renewal_price = cost
        s.status = status
        s.auto_renew = auto_renew
        s.notes = notes
        s.save()
        AuditLog.create(event_type='UPDATE', description=f"Servicio actualizado: {name} (ID: {service_id})")
        return s

    @staticmethod
    def update_ticket_status(ticket_id, new_status):
        """Updates ticket status with auditing."""
        from app.models.database import Ticket
        t = Ticket.get_by_id(ticket_id)
        old = t.status
        t.status = new_status
        t.save()
        AuditLog.create(event_type='TICKET_UPDATE', description=f"Ticket {t.id} cambió de {old} a {new_status}")

    @staticmethod
    def create_task(title, due_date, priority='NORMAL'):
        """Creates a system task."""
        from app.models.database import Task
        tk = Task.create(title=title, due_date=due_date, priority=priority)
        AuditLog.create(event_type='TASK', description=f"Nueva Tarea: {title}")
        return tk

    @staticmethod
    def create_offer(client_id, subject, content, expiry_date):
        """Creates a commercial offer/quote."""
        from app.models.database import Offer
        o = Offer.create(client=client_id, subject=subject, content=content, expiry_date=expiry_date)
        AuditLog.create(event_type='OFFER', description=f"Nueva Cotización: {subject} para Cliente {client_id}")
        return o

    @staticmethod
    def export_services_csv(filepath):
        """Reports: Full Services inventory to CSV with Excel-friendly encoding."""
        import pandas as pd
        services = (Service.select(Service, Client, Provider)
                   .join(Client).switch(Service)
                   .join(Provider))
        
        data = []
        for s in services:
            data.append({
                'ID': s.id,
                'Nombre': s.name,
                'Tipo': s.type,
                'Cliente': s.client.fullname,
                'Proveedor': s.provider.name,
                'Ref. Costo': f"{s.renewal_price:.2f}",
                'PVP Venta': f"{s.selling_price:.2f}",
                'F. Registro': s.registration_date,
                'F. Vencimiento': s.expiry_date,
                'Estatus': s.status
            })
        
        df = pd.DataFrame(data)
        # Use utf-8-sig for Excel compatibility on Windows
        df.to_csv(filepath, index=False, encoding='utf-8-sig', sep=';')
        AuditLog.create(event_type='EXPORT', description=f"Exportación CSV de inventario: {len(data)} registros.")
        return filepath

    @staticmethod
    def generate_reminders_for_day():
        """Scheduler logic with catch-up: runs every time the app starts or periodically."""
        today = datetime.date.today()
        # Intervals: 90/60/30/15/7/3/1 days
        intervals = sorted([90, 60, 30, 15, 7, 3, 1], reverse=True)
        
        created_count = 0
        services = Service.select().where(Service.status != ServiceStatus.CANCELLED)
        
        for s in services:
            days_to_expiry = (s.expiry_date - today).days
            
            for cad in intervals:
                # If we are within the alert window for this level
                if days_to_expiry <= cad:
                    # Idempotency: Has this alert ever been fired for THIS specific expiry expiration cycle?
                    # We check for a reminder for this cadence in the last year before its expiry
                    exists = Reminder.select().where(
                        (Reminder.service == s) & 
                        (Reminder.cadence_days == cad) &
                        (Reminder.trigger_date >= s.expiry_date - datetime.timedelta(days=365))
                    ).exists()
                    
                    if not exists:
                        Reminder.create(
                            service=s,
                            trigger_date=today,
                            cadence_days=cad,
                            message_type='EXPIRY_WARNING'
                        )
                        created_count += 1
                        AuditLog.create(event_type='REMINDER', description=f"Triggered {cad}d alert for {s.name}")
                    
                    # We break to only process the most urgent interval that hasn't been fired yet.
                    break
        
        return created_count

    @staticmethod
    def snooze_reminder(reminder_id, days=1):
        """Move trigger_date of a reminder to the future."""
        r = Reminder.get_by_id(reminder_id)
        r.trigger_date = datetime.date.today() + datetime.timedelta(days=days)
        r.save()
        AuditLog.create(event_type='UPDATE', description=f"Reminder {reminder_id} snoozed by {days} days.")

    @staticmethod
    def get_financial_summary():
        """Returns { 'expected': float, 'collected': float, 'pending': float } based on Invoices and Payments."""
        from app.models.database import Invoice, Payment
        expected = float(Invoice.select(fn.SUM(Invoice.total_amount)).scalar() or 0.0)
        collected = float(Payment.select(fn.SUM(Payment.amount)).scalar() or 0.0)
        return {"expected": expected, "collected": collected, "pending": expected - collected}

    @staticmethod
    def get_revenue_history(months=6):
        """Fetches aggregated payment data for the last X months for trend analysis."""
        from app.models.database import Payment
        history = []
        today = datetime.date.today()
        
        for i in range(months - 1, -1, -1):
            date = today - datetime.timedelta(days=i*30)
            month = date.strftime("%b")
            # Filter payments for that specific month/year
            month_sum = float(Payment.select(fn.SUM(Payment.amount)).where(
                (fn.strftime('%m', Payment.payment_date) == f"{date.month:02d}"),
                (fn.strftime('%Y', Payment.payment_date) == str(date.year))
            ).scalar() or 0.0)
            history.append({"label": month, "value": month_sum})
            
        return history

    @staticmethod
    def get_service_distribution():
        """Aggregates services by type for visual breakdown."""
        from app.models.database import Service
        data = Service.select(Service.type, fn.COUNT(Service.id).alias('count')).group_by(Service.type)
        return [{"label": d.type, "value": d.count} for d in data]

    @staticmethod
    def add_payment(invoice_id, amount, method='TRANSFER', ref=''):
        """Registers a payment and updates invoice status automatically."""
        from app.models.database import Invoice, Payment
        inv = Invoice.get_by_id(invoice_id)
        
        # Create Payment
        Payment.create(invoice=inv, amount=amount, method=method, reference=ref)
        
        # Update Invoice paid amount
        inv.paid_amount += amount
        if inv.paid_amount >= inv.total_amount:
            inv.status = 'PAID'
        elif inv.paid_amount > 0:
            inv.status = 'PARTIAL'
        
        inv.save()
        AuditLog.create(event_type='PAYMENT', description=f"Pago de ${amount} para Factura {inv.number}")
        return inv

    @staticmethod
    def create_manual_invoice(client_id, number, amount, due_date):
        """Creates an invoice manually."""
        from app.models.database import Invoice
        inv = Invoice.create(client=client_id, number=number, total_amount=amount, due_date=due_date)
        AuditLog.create(event_type='INVOICE', description=f"Factura manual creada: {number} por ${amount}")
        return inv

    @staticmethod
    def delete_invoice(invoice_id):
        """Deletes an invoice with auditing."""
        from app.models.database import Invoice
        inv = Invoice.get_by_id(invoice_id)
        num = inv.number
        inv.delete_instance(recursive=True)
        AuditLog.create(event_type='DELETE', description=f"Factura eliminada: {num}")

    @staticmethod
    def get_aging_report():
        """Returns unpaid/partial invoices that are past their due date."""
        from app.models.database import Invoice
        today = datetime.date.today()
        return Invoice.select().where(
            (Invoice.due_date < today) & 
            (Invoice.status << ['UNPAID', 'PARTIAL'])
        ).order_by(Invoice.due_date)

    @staticmethod
    def get_at_risk_clients():
        """Clients with at least one service in EXPIRED, GRACE or REDEMPTION status."""
        at_risk = Client.select().join(Service).where(
            Service.status << [ServiceStatus.EXPIRED, ServiceStatus.GRACE, ServiceStatus.REDEMPTION]
        ).distinct()
        return at_risk

    @staticmethod
    def get_services_by_provider_report():
        """Returns list of providers and their service counts."""
        return Provider.select(Provider.name, fn.COUNT(Service.id).alias('count')).join(Service, JOIN.LEFT_OUTER).group_by(Provider.name)

    @staticmethod
    def get_client_history(client_id):
        """Returns all services (active/cancelled) and notes for a client."""
        client = Client.get_by_id(client_id)
        return {
            "services": list(client.services),
            "notes": list(client.notes.order_by(Note.created_at.desc())),
            "invoices": list(client.invoices)
        }

    @staticmethod
    def export_report_pdf(filepath, title="Reporte Ejecutivo de Vencimientos"):
        """Generates a professional PDF report with modern styling and summaries."""
        pdf = FPDF()
        pdf.add_page()
        
        # Header Branding
        pdf.set_font("Helvetica", 'B', 18)
        pdf.set_text_color(30, 39, 46) # Theme.PRIMARY-ish
        pdf.cell(190, 15, "DHM PRO | MANAGEMENT REPORT", ln=True, align='C')
        pdf.set_font("Helvetica", 'I', 10)
        pdf.cell(190, 5, f"Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
        pdf.ln(10)
        
        pdf.set_font("Helvetica", 'B', 14)
        pdf.cell(190, 10, title, ln=True, align='L')
        pdf.ln(5)
        
        # Table Header
        pdf.set_fill_color(52, 152, 219) # Theme.ACCENT
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(60, 10, " Servicio", 1, 0, 'L', True)
        pdf.cell(50, 10, " Cliente", 1, 0, 'L', True)
        pdf.cell(40, 10, " Vencimiento", 1, 0, 'C', True)
        pdf.cell(40, 10, " Estado", 1, 1, 'C', True)

        # Table Body
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", '', 9)
        
        # Optimized query for reporting
        services = (Service.select(Service, Client)
                   .join(Client)
                   .where(Service.status != ServiceStatus.CANCELLED)
                   .order_by(Service.expiry_date))
        
        for s in services:
            # Alternate row colors
            # pdf.set_fill_color(245, 246, 250) # Very light gray
            pdf.cell(60, 8, f" {s.name}", 1)
            pdf.cell(50, 8, f" {s.client.fullname}", 1)
            pdf.cell(40, 8, f" {str(s.expiry_date)}", 1, 0, 'C')
            
            # Highlight Expired/Expiring
            if s.status in [ServiceStatus.EXPIRED, ServiceStatus.GRACE, ServiceStatus.REDEMPTION]:
                pdf.set_text_color(232, 65, 24) # Theme.DANGER
            elif s.status == ServiceStatus.EXPIRING:
                pdf.set_text_color(243, 156, 18) # Theme.WARNING
            else:
                pdf.set_text_color(0, 0, 0)
                
            pdf.cell(40, 8, f" {s.status}", 1, 1, 'C')
            pdf.set_text_color(0, 0, 0) # Reset

        pdf.ln(10)
        pdf.set_font("Helvetica", 'B', 10)
        pdf.cell(190, 10, f"Resumen: Total de {len(services)} servicios activos analizados.", ln=True)
        
        pdf.output(filepath)
        AuditLog.create(event_type='EXPORT', description=f"Reporte PDF generado: {title}")
        return filepath
    @staticmethod
    def generate_invoice_pdf(invoice_id, filepath):
        """Generates a professional PDF receipt for an invoice."""
        from app.models.database import Invoice
        inv = Invoice.get_by_id(invoice_id)
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(190, 10, f"COMPROBANTE DE FACTURACION", ln=True, align='C')
        pdf.set_font("Arial", '', 12)
        pdf.cell(190, 10, f"Factura Nro: {inv.number}", ln=True, align='C')
        pdf.ln(10)
        
        # Client Data
        pdf.set_font("Arial", 'B', 12); pdf.cell(100, 10, "CLIENTE:"); pdf.ln()
        pdf.set_font("Arial", '', 10); pdf.cell(100, 10, f"Nombre: {inv.client.fullname}"); pdf.ln()
        pdf.cell(100, 10, f"Email: {inv.client.email}"); pdf.ln(15)
        
        # Financial Details
        pdf.set_font("Arial", 'B', 12); pdf.cell(100, 10, "DETALLE FINANCIERO:"); pdf.ln()
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(60, 10, "Monto Total", 1); pdf.cell(60, 10, "Total Pagado", 1); pdf.cell(60, 10, "Pendiente", 1); pdf.ln()
        
        pdf.set_font("Arial", '', 10)
        pdf.cell(60, 10, f"${inv.total_amount:.2f}", 1)
        pdf.cell(60, 10, f"${inv.paid_amount:.2f}", 1)
        pdf.cell(60, 10, f"${inv.total_amount - inv.paid_amount:.2f}", 1); pdf.ln(15)
        
        # Payments Table
        pdf.set_font("Arial", 'B', 12); pdf.cell(100, 10, "HISTORIAL DE ABONOS:"); pdf.ln()
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(45, 10, "Fecha", 1); pdf.cell(45, 10, "Metodo", 1); pdf.cell(45, 10, "Ref", 1); pdf.cell(45, 10, "Monto", 1); pdf.ln()
        
        pdf.set_font("Arial", '', 10)
        for p in inv.payments:
            pdf.cell(45, 10, str(p.payment_date), 1)
            pdf.cell(45, 10, str(p.method), 1)
            pdf.cell(45, 10, str(p.reference or "-"), 1)
            pdf.cell(45, 10, f"${p.amount:.2f}", 1); pdf.ln()
            
        pdf.ln(10)
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(190, 10, f"Generado por DHM Pro el {datetime.datetime.now()}", 0, 0, 'C')
        
        pdf.output(filepath)
        return filepath
    def purge_logs(days=90):
        """Retention policy: Deletes old logs to keep DB healthy."""
        limit = datetime.datetime.now() - datetime.timedelta(days=days)
        q = AuditLog.delete().where(AuditLog.created_at < limit)
        c = q.execute()
        AuditLog.create(event_type='MAINTENANCE', description=f"Purgado de bitácora: {c} registros eliminados (> {days} días)")
        return c

    @staticmethod
    def prepare_whatsapp_msg(template_name, client_id, service_id=None):
        """Bridge between Templates and WhatsApp API."""
        import urllib.parse
        from app.models.database import MessageTemplate, Client, Service
        
        c = Client.get_by_id(client_id)
        phone = c.whatsapp or c.phone
        if not phone:
            raise ValueError("El cliente no tiene número de teléfono o WhatsApp configurado.")
            
        # Standardize phone (digits only)
        clean_phone = "".join(filter(str.isdigit, phone))
        
        tm = MessageTemplate.get_or_none(name=template_name)
        msg_body = tm.body if tm else f"Hola {c.fullname}, te contacto de DHM PRO..."
            
        # Dynamic Placeholders
        msg_body = BusinessLogic._populate_placeholders(msg_body, c, service_id)
            
        encoded_msg = urllib.parse.quote(msg_body)
        url = f"https://wa.me/{clean_phone}?text={encoded_msg}"
        
        AuditLog.create(event_type='COMM', description=f"Preparado link WhatsApp para {c.fullname}")
        return url

    @staticmethod
    def prepare_email_msg(template_name, client_id, service_id=None):
        """Bridge between Templates and System Email Client (mailto)."""
        import urllib.parse
        from app.models.database import MessageTemplate, Client, Service
        
        c = Client.get_by_id(client_id)
        email = c.email
        if not email:
            raise ValueError("El cliente no tiene un email configurado.")
            
        tm = MessageTemplate.get_or_none(name=template_name)
        subject = tm.subject if tm else "Notificación de DHM PRO"
        body = tm.body if tm else "Hola, le contactamos por su servicio..."
        
        # Populate placeholders in both subject and body
        subject = BusinessLogic._populate_placeholders(subject, c, service_id)
        body = BusinessLogic._populate_placeholders(body, c, service_id)
        
        encoded_subject = urllib.parse.quote(subject)
        encoded_body = urllib.parse.quote(body)
        
        url = f"mailto:{email}?subject={encoded_subject}&body={encoded_body}"
        
        AuditLog.create(event_type='COMM', description=f"Preparado link Email para {c.fullname}")
        return url

    @staticmethod
    def _populate_placeholders(text, client, service_id=None):
        """Internal helper to swap {tags} with DB values."""
        from app.models.database import Service
        text = text.replace("{client}", client.fullname)
        if service_id:
            s = Service.get_by_id(service_id)
            text = text.replace("{service}", s.name)
            text = text.replace("{date}", str(s.expiry_date))
            text = text.replace("{amount}", f"${s.selling_price:.2f}")
        return text

    @staticmethod
    def add_note(content, client_id=None, service_id=None):
        """Adds an internal note for a client or service."""
        from app.models.database import Note
        n = Note.create(client=client_id, service=service_id, content=content)
        target = f"Cliente {client_id}" if client_id else f"Servicio {service_id}"
        AuditLog.create(event_type='NOTE', description=f"Nota añadida para {target}")
        return n

    @staticmethod
    def save_template(name, subject, body, ttype, template_id=None):
        """Creates or updates a message template."""
        from app.models.database import MessageTemplate
        if template_id:
            tm = MessageTemplate.get_by_id(template_id)
            tm.name, tm.subject, tm.body, tm.type = name, subject, body, ttype
            tm.save()
            AuditLog.create(event_type='UPDATE', description=f"Plantilla actualizada: {name}")
        else:
            tm = MessageTemplate.create(name=name, subject=subject, body=body, type=ttype)
            AuditLog.create(event_type='CREATE', description=f"Plantilla creada: {name}")
        return tm

    @staticmethod
    def delete_template(template_id):
        """Deletes a template with auditing."""
        from app.models.database import MessageTemplate
        tm = MessageTemplate.get_by_id(template_id)
        name = tm.name
        tm.delete_instance()
        AuditLog.create(event_type='DELETE', description=f"Plantilla eliminada: {name}")
