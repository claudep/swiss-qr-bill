import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

from qrbill import QRBill
from qrbill.bill import Address, format_ref_number, format_amount


class AddressTests(unittest.TestCase):
    def test_name_limit(self):
        err_msg = "An address name should have between 1 and 70 characters."
        defaults = {'pcode': '1234', 'city': 'Somewhere'}
        with self.assertRaisesRegex(ValueError, err_msg):
            Address(name='', **defaults)
        with self.assertRaisesRegex(ValueError, err_msg):
            Address(name='a' * 71, **defaults)
        Address(name='a', **defaults)
        # Spaces are stripped
        addr = Address(name='  {}  '.format('a' * 70), **defaults)
        self.assertEqual(addr.name, 'a' * 70)


class QRBillTests(unittest.TestCase):
    def test_mandatory_fields(self):
        with self.assertRaisesRegex(ValueError, "The account parameter is mandatory"):
            QRBill()
        with self.assertRaisesRegex(ValueError, "Creditor information is mandatory"):
            QRBill(account="CH5380005000010283664")

    def test_account(self):
        with self.assertRaisesRegex(ValueError, "Sorry, the IBAN is not valid"):
            bill = QRBill(
                account="CH53800050000102836",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        with self.assertRaisesRegex(ValueError, "Sorry, the IBAN is not valid"):
            bill = QRBill(
                account="CH5380005000010288664",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        with self.assertRaisesRegex(ValueError, "IBAN must start with: CH, LI"):
            bill = QRBill(
                account="DE 89 37040044 0532013000",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        # Spaces are auto-stripped
        bill = QRBill(
            account="CH 53 8000 5000 0102 83664",
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
            },
        )
        self.assertEqual(bill.account, "CH5380005000010283664")

    def test_country(self):
        bill_data = {
            'account': 'CH5380005000010283664',
            'creditor': {
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        }
        # Switzerland - German/French/Italian/Romansh/English/code
        for country_name in ('Schweiz', 'Suisse', 'Svizzera', 'Svizra', 'Switzerland', 'CH'):
            bill_data['creditor']['country'] = country_name
            bill = QRBill(**bill_data)
            self.assertEqual(bill.creditor.country, 'CH')

        # Liechtenstein - short and long names/code
        for country_name in ('Liechtenstein', 'Fürstentum Liechtenstein', 'LI'):
            bill_data['creditor']['country'] = country_name
            bill = QRBill(**bill_data)
            self.assertEqual(bill.creditor.country, 'LI')

        with self.assertRaisesRegex(ValueError, "The country code 'XY' is not valid"):
            bill_data['creditor']['country'] = 'XY'
            bill = QRBill(**bill_data)

    def test_currency(self):
        with self.assertRaisesRegex(ValueError, "Currency can only contain: CHF, EUR"):
            bill = QRBill(
                account="CH 53 8000 5000 0102 83664",
                currency="USD",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        bill = QRBill(
                account="CH 53 8000 5000 0102 83664",
                currency="CHF",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        self.assertEqual(bill.currency, "CHF")
        bill = QRBill(
            account="CH 53 8000 5000 0102 83664",
            currency="EUR",
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
            },
        )
        self.assertEqual(bill.currency, "EUR")

    def test_amount(self):
        amount_err = (
            "If provided, the amount must match the pattern '###.##' and cannot "
            "be larger than 999'999'999.99"
        )
        type_err = "Amount can only be specified as str or Decimal."
        unvalid_inputs = [
            ("1234567890.00", amount_err),  # Too high value
            ("1.001", amount_err),  # More than 2 decimals
            (Decimal("1.001"), amount_err),  # Same but with Decimal type
            ("CHF800", amount_err),  # Currency included
            (1.35, type_err),  # Float are not accepted (rounding issues)
        ]
        for value, err in unvalid_inputs:
            with self.assertRaisesRegex(ValueError, err):
                bill = QRBill(
                    account="CH 53 8000 5000 0102 83664",
                    amount=value,
                    creditor={
                        'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                    },
                )

        valid_inputs = [
            (".5", "0.50", "0.50"),
            ("42", "42.00", "42.00"),
            ("001'800", "1800.00", "1 800.00"),
            (" 3.45 ", "3.45", "3.45"),
            ("9'999'999.4 ", "9999999.40", "9 999 999.40"),
            (Decimal("35.9"), "35.90", "35.90"),
        ]
        for value, expected, printed in valid_inputs:
            bill = QRBill(
                    account="CH 53 8000 5000 0102 83664",
                    amount=value,
                    creditor={
                        'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                    },
                )
            self.assertEqual(bill.amount, expected)
            self.assertEqual(format_amount(bill.amount), printed)

    def test_minimal_data(self):
        bill = QRBill(
            account="CH 53 8000 5000 0102 83664",
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        )
        self.assertEqual(
            bill.qr_data(),
            'SPC\r\n0200\r\n1\r\nCH5380005000010283664\r\nS\r\nJane\r\n\r\n\r\n'
            '1000\r\nLausanne\r\nCH\r\n\r\n\r\n\r\n\r\n\r\n\r\n\r\n\r\nCHF\r\n'
            '\r\n\r\n\r\n\r\n\r\n\r\n\r\nNON\r\n\r\n\r\nEPD'
        )
        with tempfile.NamedTemporaryFile(suffix='.svg') as fh:
            bill.as_svg(fh.name)
            content = fh.read().decode()
        self.assertTrue(content.startswith('<?xml version="1.0" encoding="utf-8" ?>'))

    def test_ultimate_creditor(self):
        bill_data = {
            'account': "CH 53 8000 5000 0102 83664",
            'creditor': {
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
            'final_creditor': {
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        }
        with self.assertRaisesRegex(ValueError, "final creditor is reserved for future use, must not be used"):
            QRBill(**bill_data)

    def test_spec_example1(self):
        bill = QRBill(
            account='CH4431999123000889012',
            creditor={
                'name': 'Robert Schneider AG',
                'street': 'Rue du Lac',
                'house_num': '1268',
                'pcode': '2501',
                'city': 'Biel',
                'country': 'CH',
            },
            amount='1949.7',
            currency='CHF',
            due_date='2019-10-31',
            debtor={
                'name': 'Pia-Maria Rutschmann-Schnyder',
                'street': 'Grosse Marktgasse',
                'house_num': '28',
                'pcode': '9400',
                'city': 'Rorschach',
                'country': 'CH',
            },
            ref_number='210000000003139471430009017',
            extra_infos=(
                'Order of 15.09.2019##S1/01/20170309/11/10201409/20/1400'
                '0000/22/36958/30/CH106017086/40/1020/41/3010'
            )
        )
        '''
        AP1 – Parameters UV1;1.1;1278564;1A-2F-43-AC-9B-33-21-B0-CC-D4-
        28-56;TCXVMKC22;2019-02-10T15: 12:39; 2019-02-
        10T15:18:16¶
        AP2 – Parameters XY2;2a-2.2r;_R1-CH2_ConradCH-2074-1_33
        50_2019-03-13T10:23:47_16,99_0,00_0,00_
        0,00_0,00_+8FADt/DQ=_1==
        '''
        self.assertEqual(
            bill.qr_data(),
            'SPC\r\n0200\r\n1\r\nCH4431999123000889012\r\nS\r\nRobert Schneider AG\r\n'
            'Rue du Lac\r\n1268\r\n2501\r\nBiel\r\nCH\r\n\r\n\r\n\r\n\r\n\r\n\r\n\r\n'
            '1949.70\r\nCHF\r\nS\r\nPia-Maria Rutschmann-Schnyder\r\nGrosse Marktgasse\r\n'
            '28\r\n9400\r\nRorschach\r\nCH\r\nQRR\r\n210000000003139471430009017\r\n'
            'Order of 15.09.2019##S1/01/20170309/11/10201409/20/14000000/22/36958/30/CH106017086'
            '/40/1020/41/3010\r\nEPD'
        )
        with tempfile.NamedTemporaryFile(suffix='.svg') as fh:
            bill.as_svg(fh.name)
            content = fh.read().decode()
        self.assertTrue(content.startswith('<?xml version="1.0" encoding="utf-8" ?>'))
        font8 = 'font-family="helvetica" font-size="8" font-weight="bold"'
        font10 = 'font-family="helvetica" font-size="10"'
        # Test the Payable by section:
        self.assertIn(
            '<text {font8} {x} y="52.5mm">Payable by</text>'
            '<text {font10} {x} y="56.0mm">Pia-Maria Rutschmann-Schnyder</text>'
            '<text {font10} {x} y="59.5mm">Grosse Marktgasse 28</text>'
            '<text {font10} {x} y="63.0mm">CH-9400 Rorschach</text>'
            '<text {font8} {x} y="67.5mm">Payable by </text>'
            '<text {font10} {x} y="71.0mm">31.10.2019</text>'.format(
                font8=font8, font10=font10, x='x="137.0mm"'
            ),
            content
        )
        # IBAN formatted
        self.assertIn(
            '<text {font10} x="5mm" y="18.5mm">CH44 3199 9123 0008 8901 2</text>'.format(
                font10=font10
            ),
            content
        )
        # amount formatted
        self.assertIn(
            '<text {font10} x="17.0mm" y="85mm">1 949.70</text>'.format(
                font10=font10
            ),
            content
        )

    def test_reference(self):
        min_data = {
            'account': "CH 53 8000 5000 0102 83664",
            'creditor': {
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        }
        bill = QRBill(**min_data)
        self.assertEqual(bill.ref_type, 'NON')
        self.assertEqual(format_ref_number(bill), '')

        bill = QRBill(**min_data, ref_number='RF18539007547034')
        self.assertEqual(bill.ref_type, 'SCOR')
        self.assertEqual(format_ref_number(bill), 'RF18 5390 0754 7034')
        with self.assertRaisesRegex(ValueError, "The reference number is invalid"):
            bill = QRBill(**min_data, ref_number='RF19539007547034')
        with self.assertRaisesRegex(ValueError, "A QRR reference number is only allowed for a QR-IBAN"):
            bill = QRBill(**min_data, ref_number='18 78583')

        min_data = {
            'account': "CH 44 3199 9123 0008 89012",
            'creditor': {
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        }
        bill = QRBill(**min_data, ref_number='210000000003139471430009017')
        self.assertEqual(bill.ref_type, 'QRR')
        self.assertEqual(format_ref_number(bill), '21 00000 00003 13947 14300 09017')

        # check leading zeros
        bill = QRBill(**min_data, ref_number='18 78583')
        self.assertEqual(bill.ref_type, 'QRR')
        self.assertEqual(format_ref_number(bill), '00 00000 00000 00000 00018 78583')

        # invalid QRR
        with self.assertRaisesRegex(ValueError, "The reference number is invalid"):
            bill = QRBill(**min_data, ref_number='18539007547034')
        with self.assertRaisesRegex(ValueError, "The reference number is invalid"):
            bill = QRBill(**min_data, ref_number='ref-number')
        with self.assertRaisesRegex(ValueError, "A QR-IBAN requires a QRR reference number"):
            bill = QRBill(**min_data, ref_number='RF18539007547034')


class CommandLineTests(unittest.TestCase):
    def test_no_args(self):
        out, err = subprocess.Popen(
            [sys.executable, 'scripts/qrbill'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).communicate()
        self.assertTrue(
            'error: the following arguments are required: --account, --creditor-name, '
            '--creditor-postalcode, --creditor-city' in err.decode()
        )

    def test_minimal_args(self):
        with tempfile.NamedTemporaryFile(suffix='.svg') as tmp:
            out, err = subprocess.Popen([
                sys.executable, 'scripts/qrbill', '--account', 'CH 53 8000 5000 0102 83664',
                '--creditor-name',  'Jane', '--creditor-postalcode', '1000',
                '--creditor-city', 'Lausanne',
                '--output', tmp.name,
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            self.assertEqual(err, b'')

    def test_svg_result(self):
        with tempfile.NamedTemporaryFile(suffix='.svg') as tmp:
            cmd = [
                sys.executable, 'scripts/qrbill', '--account', 'CH 44 3199 9123 0008 89012',
                '--creditor-name',  'Jane', '--creditor-postalcode', '1000',
                '--creditor-city', 'Lausanne', '--reference-number', '210000000003139471430009017',
                '--extra-infos', 'Order of 15.09.2019', '--output', tmp.name,
            ]
            out, err = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).communicate()
            svg_content = tmp.read().decode('utf-8')
            self.assertIn('Reference', svg_content)
            self.assertIn('Order of 15.09.2019', svg_content)


if __name__ == '__main__':
    unittest.main()
