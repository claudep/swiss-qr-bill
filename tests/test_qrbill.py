import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

from qrbill import QRBill
from qrbill.bill import format_iban, format_ref_number


class QRBillTests(unittest.TestCase):
    def test_mandatory_fields(self):
        with self.assertRaisesRegex(ValueError, "The account parameter is mandatory"):
            QRBill()
        with self.assertRaisesRegex(ValueError, "Creditor information is mandatory"):
            QRBill(account="CH4431999123000889012")

    def test_account(self):
        with self.assertRaisesRegex(ValueError, "IBAN must have exactly 21 characters"):
            bill = QRBill(
                account="CH44319991230008890",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        with self.assertRaisesRegex(ValueError, "Sorry, the IBAN is not valid"):
            bill = QRBill(
                account="CH4431999123000899012",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        with self.assertRaisesRegex(ValueError, "IBAN must start with: CH, LI"):
            bill = QRBill(
                account="DE 44 3199 9123 0008 89012",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        # Spaces are auto-stripped
        bill = QRBill(
            account="CH 44 3199 9123 0008 89012",
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
            },
        )
        self.assertEqual(bill.account, "CH4431999123000889012")
        self.assertEqual(format_iban('CH4431999123000889012'), 'CH44 3199 9123 0008 8901 2')

    def test_country(self):
        bill_data = {
            'account': 'CH4431999123000889012',
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
                account="CH 44 3199 9123 0008 89012",
                currency="USD",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        bill = QRBill(
                account="CH 44 3199 9123 0008 89012",
                currency="CHF",
                creditor={
                    'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                },
            )
        self.assertEqual(bill.currency, "CHF")
        bill = QRBill(
            account="CH 44 3199 9123 0008 89012",
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
                    account="CH 44 3199 9123 0008 89012",
                    amount=value,
                    creditor={
                        'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                    },
                )

        valid_inputs = [
            (".5", "0.50"),
            ("42", "42.00"),
            ("001'800", "1800.00"),
            (" 3.45 ", "3.45"),
            (Decimal("35.9"), "35.90"),
        ]
        for value, expected in valid_inputs:
            bill = QRBill(
                    account="CH 44 3199 9123 0008 89012",
                    amount=value,
                    creditor={
                        'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
                    },
                )
            self.assertEqual(bill.amount, expected)

    def test_minimal_data(self):
        bill = QRBill(
            account="CH 44 3199 9123 0008 89012",
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        )
        self.assertEqual(
            bill.qr_data(),
            'SPC\r\n0100\r\n1\r\nCH4431999123000889012\r\nS\r\nJane\r\n\r\n\r\n'
            '1000\r\nLausanne\r\nCH\r\n\r\n\r\n\r\n\r\n\r\n\r\n\r\nCHF\r\n'
            '\r\n\r\n\r\n\r\n\r\n\r\nNON\r\n\r\n\r\nEPD'
        )
        with tempfile.NamedTemporaryFile(suffix='.svg') as fh:
            bill.as_svg(fh.name)
            content = fh.read().decode()
        self.assertTrue(content.startswith('<?xml version="1.0" encoding="utf-8" ?>'))

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
            amount='1949.75',
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
            'SPC\r\n0100\r\n1\r\nCH4431999123000889012\r\nS\r\nRobert Schneider AG\r\n'
            'Rue du Lac\r\n1268\r\n2501\r\nBiel\r\nCH\r\n\r\n\r\n\r\n\r\n\r\n\r\n'
            '1949.75\r\nCHF\r\nS\r\nPia-Maria Rutschmann-Schnyder\r\nGrosse Marktgasse\r\n'
            '28\r\n9400\r\nRorschach\r\nCH\r\nQRR\r\n210000000003139471430009017\r\n'
            'Order of 15.09.2019##S1/01/20170309/11/10201409/20/14000000/22/36958/30/CH106017086'
            '/40/1020/41/3010\r\nEPD'
        )
        with tempfile.NamedTemporaryFile(suffix='.svg') as fh:
            bill.as_svg(fh.name)
            content = fh.read().decode()
        self.assertTrue(content.startswith('<?xml version="1.0" encoding="utf-8" ?>'))
        # Test the Payable by section:
        self.assertIn(
            '<text {font8} {x} y="52.5mm">Payable by</text>'
            '<text {font10} {x} y="56.0mm">Pia-Maria Rutschmann-Schnyder</text>'
            '<text {font10} {x} y="59.5mm">Grosse Marktgasse 28</text>'
            '<text {font10} {x} y="63.0mm">CH-9400 Rorschach</text>'
            '<text {font8} {x} y="67.5mm">Payable by </text>'
            '<text {font10} {x} y="71.0mm">31.10.2019</text>'.format(
                font8='font-family="helvetica" font-size="8" font-weight="bold"',
                font10='font-family="helvetica" font-size="10"',
                x='x="137.0mm"'
            ),
            content
        )

    def test_format_reference(self):
        bill = QRBill(
            account="CH 44 3199 9123 0008 89012",
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        )
        self.assertEqual(format_ref_number(bill), '')

        bill.ref_number = '210000000003139471430009017'
        self.assertEqual(format_ref_number(bill), '210000000003139471430009017')

        bill.ref_type = 'QRR'
        bill.ref_number = '210000000003139471430009017'
        self.assertEqual(format_ref_number(bill), '21 00000 00003 13947 14300 09017')

        bill.ref_type = 'SCOR'
        bill.ref_number = 'RF18539007547034'
        self.assertEqual(format_ref_number(bill), 'RF18 5390 0754 7034')


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
                sys.executable, 'scripts/qrbill', '--account', 'CH 44 3199 9123 0008 89012',
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
