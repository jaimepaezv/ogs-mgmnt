import unittest
import datetime
from app.models.database import db, Client, Service, Ticket, AuditLog, ServiceStatus, Provider
from app.services.logic import BusinessLogic

class TestCRMLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init(':memory:')
        db.connect()
        db.create_tables([Client, Provider, Service, Ticket, AuditLog])
        cls.client = Client.create(fullname="CRM Client", email="crm@test.com")
        cls.prov = Provider.create(name="ProvX")
        cls.svc = Service.create(
            client=cls.client, provider=cls.prov, name="SvcX", 
            type="DOMAIN", registration_date=datetime.date.today(),
            expiry_date=datetime.date.today()+datetime.timedelta(days=365),
            status=ServiceStatus.ACTIVE
        )

    @classmethod
    def tearDownClass(cls):
        db.close()

    def test_ticket_creation_and_audit(self):
        # 1. Create Ticket
        t = BusinessLogic.create_ticket(self.client.id, self.svc.id, "Test Subject", "Test Desc")
        self.assertEqual(t.status, 'OPEN')
        
        # 2. Check Audit Log
        last_log = AuditLog.select().order_by(AuditLog.created_at.desc()).first()
        self.assertIn("Nuevo Ticket", last_log.description)
        self.assertEqual(last_log.event_type, 'TICKET')

    def test_ticket_update_and_audit(self):
        t = Ticket.create(client=self.client, subject="Sub", description="Desc", status='OPEN')
        BusinessLogic.update_ticket_status(t.id, 'CLOSED')
        
        t_refreshed = Ticket.get_by_id(t.id)
        self.assertEqual(t_refreshed.status, 'CLOSED')
        
        last_log = AuditLog.select().order_by(AuditLog.created_at.desc()).first()
        self.assertIn("cambió de OPEN a CLOSED", last_log.description)

if __name__ == '__main__':
    unittest.main()
