import subprocess
import sys
import tempfile
import unittest

from qrbill import QRBill


class QRBillTests(unittest.TestCase):
    def test_mandatory_fields(self):
        with self.assertRaises(ValueError, msg="The account parameter is mandatory"):
            QRBill()
        with self.assertRaises(ValueError, msg="Creditor information is mandatory"):
            QRBill(account="CH4431999123000889012")

    def test_account(self):
        with self.assertRaises(ValueError, msg="IBAN must have exactly 21 characters"):
            bill = QRBill(
                account="CH44319991230008890",
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

    def test_minimal_data(self):
        bill = QRBill(
            account="CH 44 3199 9123 0008 89012",
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne',
            },
        )
        self.assertEqual(
            bill.qr_data(),
            'SPC\r\n0100\r\n1\r\nCH4431999123000889012\r\nJane\r\n\r\n\r\n'
            '1000\r\nLausanne\r\nCH\r\n\r\n\r\n\r\n\r\n\r\n\r\n\r\nCHF\r\n'
            '\r\n\r\n\r\n\r\n\r\n\r\n\r\nNON\r\n\r\n'
        )

    def test_spec_example1(self):
        bill = QRBill(
            account='CH4431999123000889012',
            creditor={
                'name': 'Robert Schneider AG',
                'street': 'Rue du Lac',
                'house_num': '1268/2/22',
                'pcode': '2501',
                'city': 'Biel',
                'country': 'CH',
            },
            final_creditor={
                'name': 'Robert Schneider Services Switzerland AG',
                'street': 'Rue du Lac',
                'house_num': '1268/3/1',
                'pcode': '2501',
                'city': 'Biel',
                'country': 'CH',
            },
            amount='123949.75',
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
        with tempfile.NamedTemporaryFile(suffix='.svg') as fh:
            bill.as_svg(fh.name)
            content = fh.read().decode()
        self.assertTrue(content.startswith('<?xml version="1.0" encoding="utf-8" ?>'))


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


if __name__ == '__main__':
    unittest.main()
