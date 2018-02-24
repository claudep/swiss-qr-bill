import re
from io import BytesIO

import qrcode
import qrcode.image.svg
import svgwrite
import validators
from iso3166 import countries

IBAN_CH_LENGTH = 21
AMOUNT_REGEX = r'\d{0,9}\.\d{2}'
DATE_REGEX = r'\d{4}-\d{2}-\d{2}'


class Address:
    def __init__(self, *, name='', street='', house_num='', pcode=None, city=None, country=None):
        if not (1 < len(name or '') < 70):
            raise ValueError("An address name should have between 1 and 70 characters.")
        self.name = name
        if street and len(street) > 70:
            raise ValueError("A street cannot have more than 70 characters.")
        self.street = street
        if house_num and len(house_num) > 16:
            raise ValueError("A house number cannot have more than 16 characters.")
        self.house_num = house_num
        if not pcode:
            raise ValueError("Postal code is mandatory")
        elif len(pcode) > 16:
            raise ValueError("A postal code cannot have more than 16 characters.")
        self.pcode = pcode
        if not city:
            raise ValueError("City is mandatory")
        elif len(city) > 35:
            raise ValueError("A city cannot have more than 35 characters.")
        self.city = city
        if not country:
            country = 'CH'
        try:
            countries.get(country)
        except KeyError:
            raise ValueError("The country code '%s' is not valid" % country)
        self.country = countries.get(country).alpha2

    def data_list(self):
        """Return address values as a list, appropriate for qr generation."""
        return [
            self.name, self.street, self.house_num or '', self.pcode or '',
            self.city, self.country
        ]

    def as_paragraph(self):
        lines = [self.name, "%s-%s %s" % (self.country, self.pcode, self.city)]
        if self.street:
            if self.house_num is not None:
                lines.insert(1, " ".join([self.street, self.house_num or '']))
            else:
                lines.insert(1, self.street)
        return lines


class QRBill:
    """This class represents a Swiss QR Bill."""
    # Header fields
    qr_type = 'SPC'  # Swiss Payments Code
    version = '0100'
    coding = 1  # Latin character set
    allowed_currencies = ('CHF', 'EUR')
    # QR reference, Creditor Reference (ISO 11649), without reference
    reference_types = ('QRR', 'SCOR', 'NON')

    def __init__(
            self, account=None, creditor=None, final_creditor=None, amount=None,
            currency='CHF', due_date=None, debtor=None, ref_number=None, extra_infos=''):
        # Account (IBAN) validation
        if not account:
            raise ValueError("The account parameter is mandatory")
        account = account.replace(' ', '')
        if account and len(account) != IBAN_CH_LENGTH:
            raise ValueError("IBAN must have exactly 21 characters")
        elif account and not validators.iban(account):
            raise ValueError("Sorry, the IBAN is not valid")
        self.account = account

        if amount is not None:
            m = re.match(AMOUNT_REGEX, amount)
            if not m:
                raise ValueError("If provided, the amount must match the pattern '###.##'")
        self.amount = amount
        if currency not in self.allowed_currencies:
            raise ValueError("Currency can only contains: %s" % ", ".join(self.allowed_currencies))
        self.currency = currency
        if due_date:
            m = re.match(DATE_REGEX, due_date)
            if not m:
                raise ValueError("The date must match the pattern 'YYYY-MM-DD'")
        self.due_date = due_date
        if not creditor:
            raise ValueError("Creditor information is mandatory")
        try:
            self.creditor = Address(**creditor)
        except ValueError as err:
            raise ValueError("The creditor address is invalid: %s" % err)
        if final_creditor is not None:
            try:
                self.final_creditor = Address(**final_creditor)
            except ValueError as err:
                raise ValueError("The final creditor address is invalid: %s" % err)
        else:
            self.final_creditor = final_creditor
        if debtor is not None:
            try:
                self.debtor = Address(**debtor)
            except ValueError as err:
                raise ValueError("The debtor address is invalid: %s" % err)
        else:
            self.debtor = debtor
        if ref_number is None:
            self.ref_type = 'NON'
        elif len(ref_number) == 27:
            self.ref_type = 'QRR'
        else:
            self.ref_type = 'SCOR'
        self.ref_number = ref_number
        if len(extra_infos) > 140:
            raise ValueError("Additional information cannot contain more than 140 characters")
        self.extra_infos = extra_infos

    def qr_data(self):
        """Return data to be encoded in the QR code."""
        values = [self.qr_type, self.version, self.coding, self.account]
        values.extend(self.creditor.data_list())
        values.extend(self.final_creditor.data_list() if self.final_creditor else [''] * 6)
        values.extend([self.amount or '', self.currency, self.due_date or ''])
        values.extend(self.debtor.data_list() if self.debtor else [''] * 6)
        values.extend([self.ref_type, self.ref_number or '', self.extra_infos])
        return "\r\n".join([str(v) for v in values])

    def qr_image(self):
        factory = qrcode.image.svg.SvgPathImage
        return qrcode.make(
            self.qr_data(),
            image_factory=factory,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
        )

    def draw_swiss_cross(self, dwg, qr_width):
        group = dwg.add(dwg.g(id="swiss-cross"))
        group.add(
            dwg.polygon(points=[
                (18.3, 0.7), (1.6, 0.7), (0.7, 0.7), (0.7, 1.6), (0.7, 18.3), (0.7, 19.1),
                (1.6, 19.1), (18.3, 19.1), (19.1, 19.1), (19.1, 18.3), (19.1, 1.6), (19.1, 0.7)
            ])
        )
        group.add(
            dwg.rect(insert=(8.3, 4), size=(3.3, 11), fill='white')
        )
        group.add(
            dwg.rect(insert=(4.4, 7.9), size=(11, 3.3), fill='white')
        )
        group.add(
            dwg.polygon(points=[
                (0.7, 1.6), (0.7, 18.3), (0.7, 19.1), (1.6, 19.1), (18.3, 19.1), (19.1, 19.1),
                (19.1, 18.3), (19.1, 1.6), (19.1, 0.7), (18.3, 0.7), (1.6, 0.7), (0.7, 0.7)],
                fill='none', stroke='white', stroke_width=1.4357,
            )
        )
        x = 7 + (qr_width * 1.6)
        y = 98 + (qr_width * 1.6)
        group.translate(tx=x, ty=y)

    def as_svg(self, file_name):
        left_margin = '5mm'
        col_offset = '80mm'

        dwg = svgwrite.Drawing(
            size=('148mm', '105mm'),  # A6 horiz.
            filename=file_name,
        )
        dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill='white'))  # Force white background
        dwg.add(dwg.text(
            "QR-bill payment part", (left_margin, '10mm'), font_size=11, font_family='helvetica', font_weight='bold'
        ))
        dwg.add(dwg.text(
            "Supports", (left_margin, '16mm'), font_size=10.5, font_family='helvetica', font_weight='bold'
        ))
        dwg.add(dwg.text(
            "Credit transfer", (left_margin, '21mm'), font_size=11, font_family='helvetica'
        ))

        # Get QR code SVG from qrcode lib, read it and redraw path in svgwrite drawing.
        buff = BytesIO()
        im = self.qr_image()
        im.save(buff)
        m = re.search(r'<path [^>]*>', buff.getvalue().decode())
        if not m:
            raise Exception("Unable to extract path data from the QR code SVG image")
        m = re.search(r' d=\"([^\"]*)\"', m.group())
        if not m:
            raise Exception("Unable to extract path d attributes from the SVG QR code source")
        path_data = m.groups()[0]
        path = dwg.path(
            d=path_data,
            style="fill:#000000;fill-opacity:1;fill-rule:nonzero;stroke:none",
        )
        path.translate(tx=10, ty=100)
        path.scale(sx=3, sy=3)
        dwg.add(path)

        self.draw_swiss_cross(dwg, im.width)

        dwg.add(dwg.text(
            "Currency", (left_margin, '90mm'), font_size=10.5, font_family='helvetica', font_weight='bold'
        ))
        dwg.add(dwg.text(
            "Amount", ('25mm', '90mm'), font_size=10.5, font_family='helvetica', font_weight='bold'
        ))
        dwg.add(dwg.text(
            self.currency, (left_margin, '95mm'), font_size=11, font_family='helvetica'
        ))
        dwg.add(dwg.text(
            self.amount or '', ('25mm', '95mm'), font_size=11, font_family='helvetica'
        ))

        # Right side of the bill
        y_pos = 10
        dwg.add(dwg.text(
            "Account", (col_offset, '%smm' % y_pos), font_size=10.5, font_family='helvetica', font_weight='bold'
        ))
        y_pos += 5
        dwg.add(dwg.text(
            self.account, (col_offset, '%smm' % y_pos), font_size=11, font_family='helvetica'
        ))
        y_pos += 5

        dwg.add(dwg.text(
            "Creditor", (col_offset, '%smm' % y_pos), font_size=10.5, font_family='helvetica', font_weight='bold'
        ))
        y_pos += 5
        for line_text in self.creditor.as_paragraph():
            dwg.add(dwg.text(
                line_text, (col_offset, '%smm' % y_pos), font_size=11, font_family='helvetica'
            ))
            y_pos += 5

        if self.final_creditor:
            dwg.add(dwg.text(
                "Ultimate creditor", (col_offset, '%smm' % y_pos), font_size=10.5,
                font_family='helvetica', font_weight='bold'
            ))
            y_pos += 5
            for line_text in self.final_creditor.as_paragraph():
                dwg.add(dwg.text(
                    line_text, (col_offset, '%smm' % y_pos), font_size=11, font_family='helvetica'
                ))
                y_pos += 5

        if self.ref_number:
            dwg.add(dwg.text(
                "Reference number", (col_offset, '%smm' % y_pos), font_size=10.5,
                font_family='helvetica', font_weight='bold'
            ))
            y_pos += 5
            dwg.add(dwg.text(
                self.ref_number, (col_offset, '%smm' % y_pos), font_size=11, font_family='helvetica'
            ))
            y_pos += 5

        if self.extra_infos:
            dwg.add(dwg.text(
                "Additional information", (col_offset, '%smm' % y_pos), font_size=10.5,
                font_family='helvetica', font_weight='bold'
            ))
            y_pos += 5
            if '##' in self.extra_infos:
                extra_infos = self.extra_infos.split('##')
                extra_infos[1] = '##' + extra_infos[1]
            else:
                extra_infos = [self.extra_infos]
            for info in extra_infos:
                dwg.add(dwg.text(
                    info, (col_offset, '%smm' % y_pos), font_size=11, font_family='helvetica'
                ))
                y_pos += 5

        dwg.add(dwg.text(
            "Debtor", (col_offset, '%smm' % y_pos), font_size=10.5, font_family='helvetica', font_weight='bold'
        ))
        y_pos += 5
        if self.debtor:
            for line_text in self.debtor.as_paragraph():
                dwg.add(dwg.text(
                    line_text, (col_offset, '%smm' % y_pos), font_size=11, font_family='helvetica'
                ))
                y_pos += 5

        if self.due_date:
            dwg.add(dwg.text(
                "Due date", (col_offset, '%smm' % y_pos), font_size=10.5, font_family='helvetica', font_weight='bold'
            ))
            y_pos += 5
            dwg.add(dwg.text(
                self.due_date, (col_offset, '%smm' % y_pos), font_size=11, font_family='helvetica'
            ))
            y_pos += 5

        dwg.save()
