import unittest
import datetime
from app.models.database import db, Service, Client, Provider, ServiceStatus
from app.services.logic import BusinessLogic

class TestBusinessRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app.models.database import AuditLog, Reminder
        # Create temp DB in memory for tests
        db.init(':memory:')
        db.connect()
        db.create_tables([Client, Provider, Service, AuditLog, Reminder])
        
        cls.client = Client.create(fullname="Test Client", email="test@test.com")
        cls.provider = Provider.create(name="Test Provider")

    @classmethod
    def tearDownClass(cls):
        db.close()

    def test_registration_date_validation(self):
        # Should fail if expiry is today or past
        with self.assertRaises(ValueError):
            BusinessLogic.register_new_service(
                self.client.id, self.provider.id, "fail.com", "DOMAIN", 
                datetime.date.today(), 10.0
            )

    def test_fsm_transition_grace_redemption(self):
        # Manual service creation with past expiry
        past_expiry = datetime.date.today() - datetime.timedelta(days=20)
        s = Service.create(
            client=self.client, provider=self.provider, name="grace.com",
            expiry_date=past_expiry, status=ServiceStatus.ACTIVE
        )
        
        BusinessLogic.update_all_service_statuses()
        s_updated = Service.get_by_id(s.id)
        # 20 days past should be GRACE according to logic (15 < 20 <= 30)
        self.assertEqual(s_updated.status, ServiceStatus.GRACE)

    def test_cancelled_renewal_block(self):
        s = Service.create(
            client=self.client, provider=self.provider, name="cancel.com",
            expiry_date=datetime.date.today() + datetime.timedelta(days=365),
            status=ServiceStatus.CANCELLED
        )
        
        with self.assertRaises(ValueError):
            BusinessLogic.mark_renewal_success(s.id)

if __name__ == '__main__':
    unittest.main()
