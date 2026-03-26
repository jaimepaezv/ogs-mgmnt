import unittest
import datetime
from app.models.database import db, Client, Invoice, Payment, AuditLog
from app.services.logic import BusinessLogic

class TestFinanceLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db.init(':memory:')
        db.connect()
        db.create_tables([Client, Invoice, Payment, AuditLog])
        cls.client = Client.create(fullname="Finance Client", email="fin@test.com")

    @classmethod
    def tearDownClass(cls):
        db.close()

    def test_payment_status_transitions(self):
        # 1. Create Invoice
        inv = Invoice.create(
            client=self.client, number="INV-001", 
            due_date=datetime.date.today(), total_amount=100.0
        )
        self.assertEqual(inv.status, 'UNPAID')

        # 2. Add Partial Payment
        BusinessLogic.add_payment(inv.id, 40.0)
        inv_refreshed = Invoice.get_by_id(inv.id)
        self.assertEqual(inv_refreshed.status, 'PARTIAL')
        self.assertEqual(inv_refreshed.paid_amount, 40.0)

        # 3. Add Full Payment
        BusinessLogic.add_payment(inv.id, 60.0)
        inv_final = Invoice.get_by_id(inv.id)
        self.assertEqual(inv_final.status, 'PAID')
        self.assertEqual(inv_final.paid_amount, 100.0)

    def test_aging_report(self):
        # Create an overdue invoice
        past_date = datetime.date.today() - datetime.timedelta(days=10)
        Invoice.create(
            client=self.client, number="INV-OLD", 
            due_date=past_date, total_amount=50.0, status='UNPAID'
        )
        
        report = BusinessLogic.get_aging_report()
        numbers = [i.number for i in report]
        self.assertIn("INV-OLD", numbers)

if __name__ == '__main__':
    unittest.main()
