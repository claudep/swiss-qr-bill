import re
from datetime import date
from io import BytesIO

import qrcode
import qrcode.image.svg
import svgwrite
import validators
from iso3166 import countries

IBAN_CH_LENGTH = 21
AMOUNT_REGEX = r'\d{0,9}\.\d{2}'
DATE_REGEX = r'(\d{4})-(\d{2})-(\d{2})'
MM_TO_UU = 3.543307


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
            due_date = date(*[int(g)for g in m.groups()])
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
        x = 230 + (qr_width * 0.52)
        y = 98 + (qr_width * 0.52)
        group.translate(tx=x, ty=y)

    def draw_blank_rect(self, dwg, x, y, width, height):
        """Draw a empty blank rect with corners (e.g. amount, debtor)"""
        stroke_info = {'stroke': 'black', 'stroke_width': '0.7mm', 'stroke_linecap': 'square'}
        grp = dwg.add(dwg.g())
        grp.add(dwg.line((0, 0), (0, 8.5), **stroke_info))
        grp.add(dwg.line((0, 0), (8.5, 0), **stroke_info))
        grp.add(dwg.line((0, height), (0, add_mm(height, '-3mm')), **stroke_info))
        grp.add(dwg.line((0, height), ('3mm', height), **stroke_info))
        grp.add(dwg.line((add_mm(width, '-3mm'), 0), (width, 0), **stroke_info))
        grp.add(dwg.line((width, 0), (width, 8.5), **stroke_info))
        grp.add(dwg.line((add_mm(width, '-3mm'), height), (width, height), **stroke_info))
        grp.add(dwg.line((width, height), (width, add_mm(height, '-3mm')), **stroke_info))
        grp.translate(tx=float(x[:-2]) * MM_TO_UU, ty=float(y[:-2]) * MM_TO_UU)

    def as_svg(self, file_name):
        bill_height = '105mm'
        receipt_width = '62mm'
        payment_width = '148mm'
        margin = '5mm'
        payment_left = add_mm(receipt_width, margin)
        payment_detail_left = add_mm(payment_left, '70mm')
        title_font_info = {'font_size': 11, 'font_family': 'helvetica', 'font_weight': 'bold'}
        font_info = {'font_size': 10, 'font_family': 'helvetica'}
        head_font_info = {'font_size': 8, 'font_family': 'helvetica', 'font_weight': 'bold'}

        dwg = svgwrite.Drawing(
            size=(add_mm(receipt_width, payment_width), bill_height),  # A4 width, A6 height.
            filename=file_name,
        )
        dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill='white'))  # Force white background

        # Receipt
        y_pos = 15
        line_space = 3.5
        dwg.add(dwg.text("Receipt", (margin, '10mm'), **title_font_info))
        dwg.add(dwg.text("Account / Payable to", (margin, '%smm' % y_pos), **head_font_info))
        y_pos += line_space
        dwg.add(dwg.text(
            format_iban(self.account), (margin, '%smm' % y_pos), **font_info
        ))
        y_pos += line_space
        for line_text in self.creditor.as_paragraph():
            dwg.add(dwg.text(line_text, (margin, '%smm' % y_pos), **font_info))
            y_pos += line_space

        if self.ref_number:
            dwg.add(dwg.text("Reference", (margin, '%smm' % y_pos), **head_font_info))
            y_pos += line_space
            dwg.add(dwg.text(self.ref_number, (margin, '%smm' % y_pos), **font_info))
            y_pos += line_space

        dwg.add(dwg.text("Payable by", (margin, '%smm' % y_pos), **head_font_info))
        y_pos += line_space
        if self.debtor:
            for line_text in self.debtor.as_paragraph():
                dwg.add(dwg.text(line_text, (margin, '%smm' % y_pos), **font_info))
                y_pos += line_space

        dwg.add(dwg.text("Currency", (margin, '80mm'), **head_font_info))
        dwg.add(dwg.text("Amount", (add_mm(margin, '12mm'), '80mm'), **head_font_info))
        dwg.add(dwg.text(self.currency, (margin, '85mm'), **font_info))
        dwg.add(dwg.text(self.amount or '', (add_mm(margin, '12mm'), '85mm'), **font_info))
        # Right-aligned
        dwg.add(dwg.text(
            "Acceptance point", (add_mm(receipt_width, '-' + margin), '90mm'),
            text_anchor='end', **head_font_info
        ))
        # Separation line between receipt and payment parts
        dwg.add(dwg.line(
            start=(receipt_width, 0), end=(receipt_width, bill_height),
            stroke='black', stroke_dasharray='2 2'
        ))

        # Payment part
        dwg.add(dwg.text("Payment part", (payment_left, '10mm'), **title_font_info))
        dwg.add(dwg.text("Supports", (payment_left, '16mm'), **head_font_info))
        dwg.add(dwg.text("Credit transfer", (payment_left, '21mm'), **font_info))

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
        path.translate(tx=230, ty=100)
        # Limit scaling to some max dimensions
        scale_factor = 3 - (max(im.width - 60, 0) * 0.05)
        path.scale(sx=scale_factor, sy=scale_factor)
        dwg.add(path)

        self.draw_swiss_cross(dwg, im.width * scale_factor)

        dwg.add(dwg.text("Currency", (payment_left, '80mm'), **head_font_info))
        dwg.add(dwg.text("Amount", (add_mm(payment_left, '12mm'), '80mm'), **head_font_info))
        dwg.add(dwg.text(self.currency, (payment_left, '85mm'), **font_info))
        if self.amount:
            dwg.add(dwg.text(self.amount, (add_mm(payment_left, '12mm'), '85mm'), **font_info))
        else:
            self.draw_blank_rect(
                dwg, x=add_mm(receipt_width, margin, '12mm'), y='83mm',
                width='40mm', height='15mm'
            )

        # Right side of the bill
        y_pos = 10
        line_space = 3.5

        def add_header(text):
            nonlocal dwg, payment_detail_left, y_pos
            y_pos += 1
            dwg.add(dwg.text(text, (payment_detail_left, '%smm' % y_pos), **head_font_info))
            y_pos += line_space

        add_header("Account / Payable to")
        dwg.add(dwg.text(
            format_iban(self.account), (payment_detail_left, '%smm' % y_pos), **font_info
        ))
        y_pos += line_space

        for line_text in self.creditor.as_paragraph():
            dwg.add(dwg.text(line_text, (payment_detail_left, '%smm' % y_pos), **font_info))
            y_pos += line_space

        if self.ref_number:
            add_header("Reference")
            dwg.add(dwg.text(self.ref_number, (payment_detail_left, '%smm' % y_pos), **font_info))
            y_pos += line_space

        if self.extra_infos:
            add_header("Additional information")
            if '##' in self.extra_infos:
                extra_infos = self.extra_infos.split('##')
                extra_infos[1] = '##' + extra_infos[1]
            else:
                extra_infos = [self.extra_infos]
            # TODO: handle line breaks for long infos (mandatory 5mm margin)
            for info in wrap_infos(extra_infos):
                dwg.add(dwg.text(info, (payment_detail_left, '%smm' % y_pos), **font_info))
                y_pos += line_space

        add_header("Payable by")
        if self.debtor:
            for line_text in self.debtor.as_paragraph():
                dwg.add(dwg.text(line_text, (payment_detail_left, '%smm' % y_pos), **font_info))
                y_pos += line_space
        else:
            # The specs recomment at least 2.5 x 6.5 cm
            self.draw_blank_rect(
                dwg, x=payment_detail_left, y='%smm' % y_pos,
                width='65mm', height='25mm'
            )
            y_pos += 28

        if self.final_creditor:
            add_header("In favor of")
            for line_text in self.final_creditor.as_paragraph():
                dwg.add(dwg.text(line_text, (payment_detail_left, '%smm' % y_pos), **font_info))
                y_pos += line_space

        if self.due_date:
            add_header("Due date")
            dwg.add(dwg.text(
                format_date(self.due_date), (payment_detail_left, '%smm' % y_pos), **font_info
            ))
            y_pos += line_space

        dwg.save()


def add_mm(*mms):
    """Utility to allow additions of '23mm'-type strings."""
    return '%smm' % str(sum(int(mm[:-2]) for mm in mms))


def format_iban(iban):
    if not iban:
        return ''
    return '%s %s %s %s %s %s' % (
        iban[:4], iban[4:8], iban[8:12], iban[12:16], iban[16:20], iban[20:]
    )


def format_date(date_):
    if not date_:
        return ''
    return date_.strftime('%d.%m.%Y')


def wrap_infos(infos):
    for text in infos:
        while(text):
            yield text[:42]
            text = text[42:]
