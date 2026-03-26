import datetime
from app.models.database import (
    initialize_db, Provider, Client, Service, ServiceType, ServiceStatus, 
    Ticket, Offer, Task, MessageTemplate, Invoice, Note, Payment
)

def seed_data():
    initialize_db()
    
    # 0. ServiceTypes (Categories)
    ServiceType.get_or_create(name='DOMAIN')
    ServiceType.get_or_create(name='HOSTING')
    ServiceType.get_or_create(name='SSL')
    ServiceType.get_or_create(name='SEO')
    ServiceType.get_or_create(name='MANTENIMIENTO')
    
    # 1. Providers
    p1 = Provider.get_or_create(name='Namecheap', website='https://namecheap.com')[0]
    p2 = Provider.get_or_create(name='BanaHosting', website='https://banahosting.com')[0]
    
    # 2. Clients
    c1 = Client.get_or_create(fullname='Jaime Gómex', email='jaime@correo.com', tax_id='JG-123', phone='12345678', whatsapp='12345678', is_vip=True)[0]
    c2 = Client.get_or_create(fullname='Corporación Nexus', email='info@nexus.com', tax_id='NEX-882', phone='98765432', whatsapp='98765432')[0]
    
    # 3. Services
    today = datetime.date.today()
    s1 = Service.get_or_create(
        client=c1, provider=p1, name='nexus-cloud.com', type='DOMAIN', 
        status=ServiceStatus.ACTIVE, expiry_date=today + datetime.timedelta(days=300), 
        selling_price=15.0
    )[0]
    
    s2 = Service.get_or_create(
        client=c2, provider=p2, name='Plan Hosting Gold', type='HOSTING', 
        status=ServiceStatus.EXPIRING, expiry_date=today + datetime.timedelta(days=5), 
        selling_price=120.0
    )[0]

    # 4. Note & Invoices
    Note.create(client=c1, content="Cliente prefiere contacto por Telegram.")
    inv = Invoice.create(client=c1, number="INV-001", due_date=today, total_amount=15.0, paid_amount=15.0, status='PAID')
    Payment.create(invoice=inv, amount=15.0, method='TRANSFER', reference='REF-992')
    
    # 5. Tickets & Offers
    Ticket.create(client=c1, service=s1, subject='Cambio de DNS', description='Solicita cambiar a NS de Cloudflare', priority='HIGH')
    Offer.create(client=c2, subject='Cotización Servidor Dedicado', content='Propuesta por 12 meses con IP fija', expiry_date=today + datetime.timedelta(days=15))
    
    # 6. Templates
    MessageTemplate.get_or_create(name='RENEW_REMINDER', subject='Vencimiento Próximo de {service}', body='Hola {client}, tu servicio {service} vence el {date}. Por favor contacta soporte para renovar.', type='RENEWAL')
    MessageTemplate.get_or_create(name='WELCOME_CLIENT', subject='Bienvenido a DHM Pro', body='Hola {client}, gracias por confiar en nosotros para tus servicios de Dominio y Hosting.', type='WELCOME')
    MessageTemplate.get_or_create(name='SUSPENSION_NOTICE', subject='Servicio Suspendido - {service}', body='Estimado {client}, tu servicio {service} ha sido suspendido por falta de pago.', type='WARNING')

    print("Success: DHM Pro Granular Seed Completed (All entities populated).")

if __name__ == "__main__":
    seed_data()
