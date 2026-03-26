import datetime
from peewee import *
import os

# Database Path
DB_PATH = os.path.join(os.getcwd(), 'dhm_local.db')
db = SqliteDatabase(DB_PATH)

class BaseModel(Model):
    class Meta:
        database = db

class Provider(BaseModel):
    name = CharField(unique=True)
    website = CharField(null=True)
    support_email = CharField(null=True)
    encrypted_credentials = TextField(null=True) # JSON-like encrypted creds
    notes = TextField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)

class Client(BaseModel):
    fullname = CharField()
    tax_id = CharField(unique=True, null=True)
    email = CharField(unique=True)
    phone = CharField(null=True)
    whatsapp = CharField(null=True)
    address = TextField(null=True)
    is_vip = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)

class Contact(BaseModel):
    client = ForeignKeyField(Client, backref='contacts')
    name = CharField()
    role = CharField(null=True)
    email = CharField(null=True)
    phone = CharField(null=True)

class ServiceType(BaseModel):
    name = CharField(unique=True) # DOMAIN, HOSTING, etc.
    description = TextField(null=True)

class ServiceStatus:
    DRAFT = 'DRAFT'
    ACTIVE = 'ACTIVE'
    EXPIRING = 'EXPIRING'
    EXPIRED = 'EXPIRED'
    GRACE = 'GRACE'
    REDEMPTION = 'REDEMPTION'
    CANCELLED = 'CANCELLED'
    TRANSFERRING = 'TRANSFERRING'

class Service(BaseModel):
    client = ForeignKeyField(Client, backref='services')
    provider = ForeignKeyField(Provider, backref='services')
    name = CharField() # e.g. "example.com"
    type = CharField() # Keeping as CharField for simplicity but could be FK if needed. User asked to add types.
    status = CharField(default=ServiceStatus.ACTIVE)
    registration_date = DateField(null=True)
    expiry_date = DateField()
    renewal_price = FloatField(default=0.0)
    selling_price = FloatField(default=0.0)
    auto_renew = BooleanField(default=False)
    notes = TextField(null=True)

class Ticket(BaseModel):
    client = ForeignKeyField(Client, backref='tickets')
    service = ForeignKeyField(Service, backref='tickets', null=True)
    subject = CharField()
    description = TextField()
    status = CharField(default='OPEN') # OPEN, CLOSED, PENDING
    priority = CharField(default='NORMAL') # LOW, NORMAL, HIGH, URGENT
    created_at = DateTimeField(default=datetime.datetime.now)

class Offer(BaseModel):
    client = ForeignKeyField(Client, backref='offers')
    subject = CharField()
    content = TextField()
    expiry_date = DateField()
    status = CharField(default='SENT') # SENT, CLAIMED, EXPIRED, IGNORED
    created_at = DateTimeField(default=datetime.datetime.now)

class Task(BaseModel):
    title = CharField()
    description = TextField(null=True)
    due_date = DateTimeField(null=True)
    is_completed = BooleanField(default=False)
    priority = CharField(default='NORMAL')
    created_at = DateTimeField(default=datetime.datetime.now)

class MessageTemplate(BaseModel):
    name = CharField(unique=True)
    subject = CharField()
    body = TextField()
    type = CharField() # RENEWAL, WELCOME, OFFER

class Invoice(BaseModel):
    client = ForeignKeyField(Client, backref='invoices')
    number = CharField(unique=True)
    issue_date = DateField(default=datetime.date.today)
    due_date = DateField()
    total_amount = FloatField()
    paid_amount = FloatField(default=0.0)
    status = CharField(default='UNPAID') # UNPAID, PARTIAL, PAID, CANCELLED
    notes = TextField(null=True)

class Payment(BaseModel):
    invoice = ForeignKeyField(Invoice, backref='payments')
    amount = FloatField()
    payment_date = DateField(default=datetime.date.today)
    method = CharField(default='CASH') # CASH, TRANSFER, OTHER
    reference = CharField(null=True)

class Note(BaseModel):
    client = ForeignKeyField(Client, backref='client_history', null=True)
    service = ForeignKeyField(Service, backref='service_history', null=True)
    content = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)

class InvoiceItem(BaseModel):
    invoice = ForeignKeyField(Invoice, backref='items')
    service = ForeignKeyField(Service, backref='invoice_items', null=True)
    description = CharField()
    quantity = IntegerField(default=1)
    unit_price = FloatField()

class Reminder(BaseModel):
    service = ForeignKeyField(Service, backref='reminders')
    trigger_date = DateField()
    sent_at = DateTimeField(null=True)
    message_type = CharField(default='EXPIRY_WARNING')
    cadence_days = IntegerField() # e.g. 30, 15, 7, 1

class AuditLog(BaseModel):
    event_type = CharField() # LOGIN, CREATE, UPDATE, DELETE, ERROR
    description = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)

def initialize_db():
    db.connect()
    db.create_tables([
        Provider, Client, Contact, Service, ServiceType,
        Ticket, Offer, Task, MessageTemplate,
        Invoice, InvoiceItem, Payment, Note, AuditLog, Reminder
    ], safe=True)
    db.close()

if __name__ == "__main__":
    initialize_db()
    print(f"Database initialized at: {DB_PATH}")
