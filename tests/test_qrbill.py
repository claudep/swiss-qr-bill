import unittest

from qrbill import QRBill
from qrbill.errors import ValidationError


class QRBillInitializationTest(unittest.TestCase):

    def test_mandatory_field(self):
        bill = QRBill()

        self.assertEqual(repr(bill), f"<{bill.__class__.__name__} (account:None, creditor:None, amount:None)>")


class QRBillTest(unittest.TestCase):

    def setUp(self) -> None:
        self.bill = QRBill()

    def test_account(self):
        self.bill.account = "CH4689144414967843158"  # w/o spacing
        self.assertEqual(self.bill.account, "CH46 8914 4414 9678 4315 8")

        self.bill.account = "CH46 8914 4414 9678 4315 8"  # w/ spacing
        self.assertEqual(self.bill.account, "CH46 8914 4414 9678 4315 8")

        with self.assertRaisesRegex(ValidationError, "Invalid IBAN number"):
            self.bill.account = "CH4689144414967843159"  # wrong IBAN (last digit)

        with self.assertRaisesRegex(ValidationError, "IBAN must start with: CH, LI"):
            self.bill.account = "ES8930044489487486953677"  # unsupported country

    def test_creditor(self):
        pass

    def test_ultimate_creditor(self):
        with self.assertRaises(NotImplementedError):
            self.bill.ultimate_creditor = "Not None"  # Reserved for future use

    def test_currency(self):
        for c in ["CHF", "EUR"]:
            self.bill.currency = c
            self.assertEqual(self.bill.currency, c)

        with self.assertRaises(ValidationError):
            self.bill.currency = "USD"

    def test_amount(self):
        self.bill.amount = .05
        self.assertEqual(self.bill.amount, "0.05")

        self.bill.amount = 100
        self.assertEqual(self.bill.amount, "100.00")

        self.bill.amount = 1000
        self.assertEqual(self.bill.amount, "1 000.00")

        with self.assertRaises(ValidationError):
            self.bill.amount = 1000000000  # must be < 1 000 000 000.00

    def test_debtor(self):
        pass

    def test_ref_type(self):
        self.assertEqual(self.bill.ref_type, "NON")

    def test_ref_number(self):

        self.bill.ref_number = "RF18000000000539007547034"  # ref number according iso11649
        self.assertEqual(self.bill.ref_type, "SCOR")

        self.bill.ref_number = "00 00000 00000 00000 00000 01236"  # ref number according to ERS
        self.assertEqual(self.bill.ref_type, "QRR")

        with self.assertRaises(ValidationError):
            self.bill.ref_number = "123"  # wrong ref number

    def test_unstructured_message(self):
        pass

    def test_billing_info(self):
        pass

    def test_language(self):
        for language in ["en", "de", "fr", "it"]:
            self.bill.language = language
            self.assertEqual(self.bill.language, language)

        with self.assertRaises(ValidationError):
            self.bill.language = "es"  # spanish


if __name__ == '__main__':
    unittest.main()
