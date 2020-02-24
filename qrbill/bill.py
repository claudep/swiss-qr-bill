import re
from datetime import date
from decimal import Decimal
from io import BytesIO

import qrcode
import qrcode.image.svg
import svgwrite
from iso3166 import countries
from stdnum import iban, iso11649
from stdnum.ch import esr

IBAN_ALLOWED_COUNTRIES = ['CH', 'LI']
QR_IID = {"start": 30000, "end": 31999}
AMOUNT_REGEX = r'^\d{1,9}\.\d{2}$'
DATE_REGEX = r'(\d{4})-(\d{2})-(\d{2})'
MM_TO_UU = 3.543307

# Annex D: Multilingual headings
LABELS = {
    'Payment part': {'de': 'Zahlteil', 'fr': 'Section paiement', 'it': 'Sezione pagamento'},
    'Account / Payable to': {
        'de': 'Konto / Zahlbar an',
        'fr': 'Compte / Payable à',
        'it': 'Conto / Pagabile a',
    },
    'Reference': {'de': 'Referenz', 'fr': 'Référence', 'it': 'Riferimento'},
    'Additional information': {
        'de': 'Zusätzliche Informationen',
        'fr': 'Informations supplémentaires',
        'it': 'Informazioni supplementari',
    },
    'Currency': {'de': 'Währung', 'fr': 'Monnaie', 'it': 'Valuta'},
    'Amount': {'de': 'Betrag', 'fr': 'Montant', 'it': 'Importo'},
    'Receipt': {'de': 'Empfangsschein', 'fr': 'Récépissé', 'it': 'Ricevuta'},
    'Acceptance point': {'de': 'Annahmestelle', 'fr': 'Point de dépôt', 'it': 'Punto di accettazione'},
    'Separate before paying in': {
        'de': 'Vor der Einzahlung abzutrennen',
        'fr': 'A détacher avant le versement',
        'it': 'Da staccare prima del versamento',
    },
    'Payable by': {'de': 'Zahlbar durch', 'fr': 'Payable par', 'it': 'Pagabile da'},
    'Payable by (name/address)': {
        'de': 'Zahlbar durch (Name/Adresse)',
        'fr': 'Payable par (nom/adresse)',
        'it': 'Pagabile da (nome/indirizzo)',
    },
    # The extra ending space allows to differentiate from the other 'Payable by' above.
    'Payable by ': {'de': 'Zahlbar bis', 'fr': 'Payable jusqu’au', 'it': 'Pagabile fino al'},
    'In favour of': {'de': 'Zugunsten', 'fr': 'En faveur de', 'it': 'A favore di'},
}


class Address:
    def __init__(self, *, name=None, street=None, house_num=None, pcode=None, city=None, country=None):
        self.name = (name or '').strip()
        if not (1 <= len(self.name) <= 70):
            raise ValueError("An address name should have between 1 and 70 characters.")
        self.street = (street or '').strip()
        if len(self.street) > 70:
            raise ValueError("A street cannot have more than 70 characters.")
        self.house_num = (house_num or '').strip()
        if len(self.house_num) > 16:
            raise ValueError("A house number cannot have more than 16 characters.")
        self.pcode = (pcode or '').strip()
        if not self.pcode:
            raise ValueError("Postal code is mandatory")
        elif len(self.pcode) > 16:
            raise ValueError("A postal code cannot have more than 16 characters.")
        self.city = (city or '').strip()
        if not self.city:
            raise ValueError("City is mandatory")
        elif len(self.city) > 35:
            raise ValueError("A city cannot have more than 35 characters.")
        country = (country or '').strip()
        # allow users to write the country as if used in an address in the local language
        if not country or country.lower() in ['schweiz', 'suisse', 'svizzera', 'svizra']:
            country = 'CH'
        if country.lower() in ['fürstentum liechtenstein']:
            country = 'LI'
        try:
            self.country = countries.get(country).alpha2
        except KeyError:
            raise ValueError("The country code '%s' is not valid" % country)
        self.country = countries.get(country).alpha2

    def data_list(self):
        """Return address values as a list, appropriate for qr generation."""
        # 'S': structured address
        return [
            'S', self.name, self.street, self.house_num, self.pcode,
            self.city, self.country
        ]

    def as_paragraph(self):
        lines = [self.name, "%s-%s %s" % (self.country, self.pcode, self.city)]
        if self.street:
            if self.house_num:
                lines.insert(1, " ".join([self.street, self.house_num]))
            else:
                lines.insert(1, self.street)
        return lines


class QRBill:
    """This class represents a Swiss QR Bill."""
    # Header fields
    qr_type = 'SPC'  # Swiss Payments Code
    version = '0200'
    coding = 1  # Latin character set
    allowed_currencies = ('CHF', 'EUR')
    # QR reference, Creditor Reference (ISO 11649), without reference
    reference_types = ('QRR', 'SCOR', 'NON')

    def __init__(
            self, account=None, creditor=None, final_creditor=None, amount=None,
            currency='CHF', due_date=None, debtor=None, ref_number=None, extra_infos='',
            language='en'):
        # Account (IBAN) validation
        if not account:
            raise ValueError("The account parameter is mandatory")
        if not iban.is_valid(account):
            raise ValueError("Sorry, the IBAN is not valid")
        self.account = iban.validate(account)
        if self.account[:2] not in IBAN_ALLOWED_COUNTRIES:
            raise ValueError("IBAN must start with: %s" % ", ".join(IBAN_ALLOWED_COUNTRIES))
        iban_iid = int(self.account[4:9])
        if QR_IID["start"] <= iban_iid <= QR_IID["end"]:
            self.account_is_qriban = True
        else:
            self.account_is_qriban = False

        if amount is not None:
            if isinstance(amount, Decimal):
                amount = str(amount)
            elif not isinstance(amount, str):
                raise ValueError("Amount can only be specified as str or Decimal.")
            # remove commonly used thousands separators
            amount = amount.replace("'", "").strip()
            # people often don't add .00 for amounts without cents/rappen
            if "." not in amount:
                amount = amount + ".00"
            # support lazy people who write 12.1 instead of 12.10
            if amount[-2] == '.':
                amount = amount + '0'
            # strip leading zeros
            amount = amount.lstrip("0")
            # some people tend to strip the leading zero on amounts below 1 CHF/EUR
            # and with removing leading zeros, we would have removed the zero before
            # the decimal delimiter anyway
            if amount[0] == ".":
                amount = "0" + amount
            m = re.match(AMOUNT_REGEX, amount)
            if not m:
                raise ValueError(
                    "If provided, the amount must match the pattern '###.##'"
                    " and cannot be larger than 999'999'999.99"
                )
        self.amount = amount
        if currency not in self.allowed_currencies:
            raise ValueError("Currency can only contain: %s" % ", ".join(self.allowed_currencies))
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
            # The standard says ultimate creditor is reserved for future use.
            # The online validator does not properly validate QR-codes where
            # this is set, saying it must not (yet) be used.
            raise ValueError("final creditor is reserved for future use, must not be used")
        else:
            self.final_creditor = final_creditor
        if debtor is not None:
            try:
                self.debtor = Address(**debtor)
            except ValueError as err:
                raise ValueError("The debtor address is invalid: %s" % err)
        else:
            self.debtor = debtor

        if not ref_number:
            self.ref_type = 'NON'
            self.ref_number = None
        elif ref_number.strip()[:2].upper() == "RF":
            if iso11649.is_valid(ref_number):
                self.ref_type = 'SCOR'
                self.ref_number = iso11649.validate(ref_number)
            else:
                raise ValueError("The reference number is invalid")
        elif esr.is_valid(ref_number):
            self.ref_type = 'QRR'
            self.ref_number = esr.format(ref_number).replace(" ", "")
        else:
            raise ValueError("The reference number is invalid")

        # A QRR reference number must only be used with a QR-IBAN and
        # with a QR-IBAN, a QRR reference number must be used
        if self.account_is_qriban:
            if self.ref_type != 'QRR':
                raise ValueError("A QR-IBAN requires a QRR reference number")
        else:
            if self.ref_type == 'QRR':
                raise ValueError("A QRR reference number is only allowed for a QR-IBAN")

        if extra_infos and len(extra_infos) > 140:
            raise ValueError("Additional information cannot contain more than 140 characters")
        self.extra_infos = extra_infos
        if language not in ['en', 'de', 'fr', 'it']:
            raise ValueError("Language should be 'en', 'de', 'fr', or 'it'")
        self.language = language

    def qr_data(self):
        """Return data to be encoded in the QR code."""
        values = [self.qr_type or '', self.version or '', self.coding or '', self.account or '']
        values.extend(self.creditor.data_list())
        values.extend(self.final_creditor.data_list() if self.final_creditor else [''] * 7)
        values.extend([self.amount or '', self.currency or ''])
        values.extend(self.debtor.data_list() if self.debtor else [''] * 7)
        values.extend([self.ref_type or '', self.ref_number or '', self.extra_infos or '', 'EPD'])
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
        x = 250 + (qr_width * 0.52)
        y = 58 + (qr_width * 0.52)
        group.translate(tx=x, ty=y)

    def draw_blank_rect(self, dwg, x, y, width, height):
        """Draw a empty blank rect with corners (e.g. amount, debtor)"""
        stroke_info = {'stroke': 'black', 'stroke_width': '0.7mm', 'stroke_linecap': 'square'}
        grp = dwg.add(dwg.g())
        grp.add(dwg.line((x, y), (x, add_mm(y, '2mm')), **stroke_info))
        grp.add(dwg.line((x, y), (add_mm(x, '3mm'), y), **stroke_info))
        grp.add(dwg.line((x, add_mm(y, height)), (x, add_mm(y, height, '-2mm')), **stroke_info))
        grp.add(dwg.line((x, add_mm(y, height)), (add_mm(x, '3mm'), add_mm(y, height)), **stroke_info))
        grp.add(dwg.line((add_mm(x, width, '-3mm'), y), (add_mm(x, width), y), **stroke_info))
        grp.add(dwg.line((add_mm(x, width), y), (add_mm(x, width), add_mm(y, '2mm')), **stroke_info))
        grp.add(dwg.line(
            (add_mm(x, width, '-3mm'), add_mm(y, height)), (add_mm(x, width), add_mm(y, height)),
            **stroke_info
        ))
        grp.add(dwg.line(
            (add_mm(x, width), add_mm(y, height)), (add_mm(x, width), add_mm(y, height, '-2mm')),
            **stroke_info
        ))

    def label(self, txt):
        return txt if self.language == 'en' else LABELS[txt][self.language]

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
        dwg.add(dwg.text(self.label("Receipt"), (margin, '10mm'), **title_font_info))
        dwg.add(dwg.text(self.label("Account / Payable to"), (margin, '%smm' % y_pos), **head_font_info))
        y_pos += line_space
        dwg.add(dwg.text(
            iban.format(self.account), (margin, '%smm' % y_pos), **font_info
        ))
        y_pos += line_space
        for line_text in self.creditor.as_paragraph():
            dwg.add(dwg.text(line_text, (margin, '%smm' % y_pos), **font_info))
            y_pos += line_space

        if self.ref_number:
            y_pos += 1
            dwg.add(dwg.text(self.label("Reference"), (margin, '%smm' % y_pos), **head_font_info))
            y_pos += line_space
            dwg.add(dwg.text(format_ref_number(self), (margin, '%smm' % y_pos), **font_info))
            y_pos += line_space

        y_pos += 1
        dwg.add(dwg.text(
            self.label("Payable by") if self.debtor else self.label("Payable by (name/address)"),
            (margin, '%smm' % y_pos), **head_font_info
        ))
        y_pos += line_space
        if self.debtor:
            for line_text in self.debtor.as_paragraph():
                dwg.add(dwg.text(line_text, (margin, '%smm' % y_pos), **font_info))
                y_pos += line_space
        else:
            self.draw_blank_rect(
                dwg, x=margin, y='%smm' % y_pos,
                width='52mm', height='25mm'
            )
            y_pos += 28

        dwg.add(dwg.text(self.label("Currency"), (margin, '80mm'), **head_font_info))
        dwg.add(dwg.text(self.label("Amount"), (add_mm(margin, '12mm'), '80mm'), **head_font_info))
        dwg.add(dwg.text(self.currency, (margin, '85mm'), **font_info))
        if self.amount:
            dwg.add(dwg.text(format_amount(self.amount), (add_mm(margin, '12mm'), '85mm'), **font_info))
        else:
            self.draw_blank_rect(
                dwg, x=add_mm(margin, '25mm'), y='77mm',
                width='27mm', height='11mm'
            )

        # Right-aligned
        dwg.add(dwg.text(
            self.label("Acceptance point"), (add_mm(receipt_width, '-' + margin), '91mm'),
            text_anchor='end', **head_font_info
        ))
        # Separation line between receipt and payment parts
        dwg.add(dwg.line(
            start=(receipt_width, 0), end=(receipt_width, bill_height),
            stroke='black', stroke_dasharray='2 2'
        ))
        dwg.add(dwg.text(
            "✂", insert=(add_mm(receipt_width, '-1.5mm'), 40),
            font_size=16, font_family='helvetica', rotate=[90]
        ))

        # Payment part
        dwg.add(dwg.text(self.label("Payment part"), (payment_left, '10mm'), **title_font_info))

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
        path.translate(tx=250, ty=60)
        # Limit scaling to some max dimensions
        scale_factor = 3 - (max(im.width - 60, 0) * 0.05)
        path.scale(sx=scale_factor, sy=scale_factor)
        dwg.add(path)

        self.draw_swiss_cross(dwg, im.width * scale_factor)

        dwg.add(dwg.text(self.label("Currency"), (payment_left, '80mm'), **head_font_info))
        dwg.add(dwg.text(self.label("Amount"), (add_mm(payment_left, '12mm'), '80mm'), **head_font_info))
        dwg.add(dwg.text(self.currency, (payment_left, '85mm'), **font_info))
        if self.amount:
            dwg.add(dwg.text(format_amount(self.amount), (add_mm(payment_left, '12mm'), '85mm'), **font_info))
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

        add_header(self.label("Account / Payable to"))
        dwg.add(dwg.text(
            iban.format(self.account), (payment_detail_left, '%smm' % y_pos), **font_info
        ))
        y_pos += line_space

        for line_text in self.creditor.as_paragraph():
            dwg.add(dwg.text(line_text, (payment_detail_left, '%smm' % y_pos), **font_info))
            y_pos += line_space

        if self.ref_number:
            add_header(self.label("Reference"))
            dwg.add(dwg.text(
                format_ref_number(self), (payment_detail_left, '%smm' % y_pos), **font_info
            ))
            y_pos += line_space

        if self.extra_infos:
            add_header(self.label("Additional information"))
            if '##' in self.extra_infos:
                extra_infos = self.extra_infos.split('##')
                extra_infos[1] = '##' + extra_infos[1]
            else:
                extra_infos = [self.extra_infos]
            # TODO: handle line breaks for long infos (mandatory 5mm margin)
            for info in wrap_infos(extra_infos):
                dwg.add(dwg.text(info, (payment_detail_left, '%smm' % y_pos), **font_info))
                y_pos += line_space

        if self.debtor:
            add_header(self.label("Payable by"))
            for line_text in self.debtor.as_paragraph():
                dwg.add(dwg.text(line_text, (payment_detail_left, '%smm' % y_pos), **font_info))
                y_pos += line_space
        else:
            add_header(self.label("Payable by (name/address)"))
            # The specs recomment at least 2.5 x 6.5 cm
            self.draw_blank_rect(
                dwg, x=payment_detail_left, y='%smm' % y_pos,
                width='65mm', height='25mm'
            )
            y_pos += 28

        if self.final_creditor:
            add_header(self.label("In favor of"))
            for line_text in self.final_creditor.as_paragraph():
                dwg.add(dwg.text(line_text, (payment_detail_left, '%smm' % y_pos), **font_info))
                y_pos += line_space

        if self.due_date:
            add_header(self.label("Payable by "))
            dwg.add(dwg.text(
                format_date(self.due_date), (payment_detail_left, '%smm' % y_pos), **font_info
            ))
            y_pos += line_space

        dwg.save()


def add_mm(*mms):
    """Utility to allow additions of '23mm'-type strings."""
    return '%smm' % str(sum(float(mm[:-2]) for mm in mms))


def format_ref_number(bill):
    if not bill.ref_number:
        return ''
    num = bill.ref_number
    if bill.ref_type == "QRR":
        return esr.format(num)
    elif bill.ref_type == "SCOR":
        return iso11649.format(num)
    else:
        return num


def format_date(date_):
    if not date_:
        return ''
    return date_.strftime('%d.%m.%Y')


def format_amount(amount_):
    return '{:,.2f}'.format(float(amount_)).replace(",", " ")


def wrap_infos(infos):
    for text in infos:
        while(text):
            yield text[:42]
            text = text[42:]
