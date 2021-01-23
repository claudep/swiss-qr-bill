import re
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path

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
BILL_HEIGHT = '105mm'
RECEIPT_WIDTH = '62mm'
PAYMENT_WIDTH = '148mm'
MAX_CHARS_PAYMENT_LINE = 48
MAX_CHARS_RECEIPT_LINE = 38
A4 = ('210mm', '297mm')

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
    @classmethod
    def create(cls, **kwargs):
        if kwargs.get('line1') or kwargs.get('line2'):
            for arg_name in ('street', 'house_num', 'pcode', 'city'):
                if kwargs.pop(arg_name, False):
                    raise ValueError("When providing line1 or line2, you cannot provide %s" % arg_name)
            if not kwargs.get('line2'):
                raise ValueError("line2 is mandatory for combined address type.")
            return CombinedAddress(**kwargs)
        else:
            kwargs.pop('line1', None)
            kwargs.pop('line2', None)
            return StructuredAddress(**kwargs)

    @staticmethod
    def parse_country(country):
        country = (country or '').strip()
        # allow users to write the country as if used in an address in the local language
        if not country or country.lower() in ['schweiz', 'suisse', 'svizzera', 'svizra']:
            country = 'CH'
        if country.lower() in ['fürstentum liechtenstein']:
            country = 'LI'
        try:
            return countries.get(country).alpha2
        except KeyError:
            raise ValueError("The country code '%s' is not an ISO 3166 valid code" % country)

    @staticmethod
    def _split_lines(lines, max_chars):
        """
        Each line should be no more than `max_chars` chars, splitting on spaces
        (if possible).
        """
        for line in lines:
            if len(line) <= max_chars:
                yield line
            else:
                chunks = line.split(' ')
                line2 = ''
                while chunks:
                    if line2 and len(line2 + chunks[0]) + 1 > max_chars:
                        yield line2
                        line2 = ''
                    line2 += (' ' if line2 else '') + chunks[0]
                    chunks = chunks[1:]
                if line2:
                    yield line2


class CombinedAddress(Address):
    """
    Combined address
    (name, line1, line2, country)
    """
    combined = True

    def __init__(self, *, name=None, line1=None, line2=None, country=None):
        self.name = (name or '').strip()
        self.line1 = (line1 or '').strip()
        if not (0 <= len(self.line1) <= 70):
            raise ValueError("An address line should have between 0 and 70 characters.")
        self.line2 = (line2 or '').strip()
        if not (0 <= len(self.line2) <= 70):
            raise ValueError("An address line should have between 0 and 70 characters.")
        self.country = self.parse_country(country)

    def data_list(self):
        # 'K': combined address
        return [
            'K', self.name, self.line1, self.line2, '', '', self.country
        ]

    def as_paragraph(self, max_chars=MAX_CHARS_PAYMENT_LINE):
        return self._split_lines([self.name, self.line1, self.line2], max_chars)


class StructuredAddress(Address):
    """
    Structured address
    (name, street, house_num, pcode, city, country)
    """
    combined = False

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
        self.country = self.parse_country(country)

    def data_list(self):
        """Return address values as a list, appropriate for qr generation."""
        # 'S': structured address
        return [
            'S', self.name, self.street, self.house_num, self.pcode,
            self.city, self.country
        ]

    def as_paragraph(self, max_chars=MAX_CHARS_PAYMENT_LINE):
        lines = [self.name, "%s-%s %s" % (self.country, self.pcode, self.city)]
        if self.street:
            if self.house_num:
                lines.insert(1, " ".join([self.street, self.house_num]))
            else:
                lines.insert(1, self.street)
        return self._split_lines(lines, max_chars)


class QRBill:
    """This class represents a Swiss QR Bill."""
    # Header fields
    qr_type = 'SPC'  # Swiss Payments Code
    version = '0200'
    coding = 1  # Latin character set
    allowed_currencies = ('CHF', 'EUR')
    # QR reference, Creditor Reference (ISO 11649), without reference
    reference_types = ('QRR', 'SCOR', 'NON')

    title_font_info = {'font_size': 12, 'font_family': 'Helvetica', 'font_weight': 'bold'}
    font_info = {'font_size': 10, 'font_family': 'Helvetica'}
    head_font_info = {'font_size': 8, 'font_family': 'Helvetica', 'font_weight': 'bold'}
    proc_font_info = {'font_size': 7, 'font_family': 'Helvetica'}

    def __init__(
            self, account=None, creditor=None, final_creditor=None, amount=None,
            currency='CHF', due_date=None, debtor=None, ref_number=None, extra_infos='',
            alt_procs=(), language='en', top_line=True, payment_line=True):
        """
        Arguments
        ---------
        account: str
            IBAN of the creditor (must start with 'CH' or 'LI')
        creditor: Address
            Address (combined or structured) of the creditor
        final_creditor: Address
            (for future use)
        amount: str
        currency: str
            two values allowed: 'CHF' and 'EUR'
        due_date: str (YYYY-MM-DD)
        debtor: Address
            Address (combined or structured) of the debtor
        extra_infos: str
            Extra information aimed for the bill recipient
        alt_procs: list of str (max 2)
            two additional fields for alternative payment schemes
        language: str
            language of the output (ISO, 2 letters): 'en', 'de', 'fr' or 'it'
        top_line: bool
            print a horizontal line at the top of the bill
        payment_line: bool
            print a vertical line between the receipt and the bill itself
        """
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
            self.creditor = Address.create(**creditor)
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
                self.debtor = Address.create(**debtor)
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

        if len(alt_procs) > 2:
            raise ValueError("Only two lines allowed in alternative procedure parameters")
        if any(len(el) > 100 for el in alt_procs):
            raise ValueError("An alternative procedure line cannot be longer than 100 characters")
        self.alt_procs = list(alt_procs)

        # Meta-information
        if language not in ['en', 'de', 'fr', 'it']:
            raise ValueError("Language should be 'en', 'de', 'fr', or 'it'")
        self.language = language
        self.top_line = top_line
        self.payment_line = payment_line

    def qr_data(self):
        """
        Return data to be encoded in the QR code in the standard text
        representation.
        """
        values = [self.qr_type or '', self.version or '', self.coding or '', self.account or '']
        values.extend(self.creditor.data_list())
        values.extend(self.final_creditor.data_list() if self.final_creditor else [''] * 7)
        values.extend([self.amount or '', self.currency or ''])
        values.extend(self.debtor.data_list() if self.debtor else [''] * 7)
        values.extend([self.ref_type or '', self.ref_number or '', self.extra_infos or ''])
        values.append('EPD')
        values.extend(self.alt_procs)
        return "\r\n".join([str(v) for v in values])

    def qr_image(self):
        factory = qrcode.image.svg.SvgPathImage
        return qrcode.make(
            self.qr_data(),
            image_factory=factory,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
        )

    def draw_swiss_cross(self, dwg, grp, qr_width):
        group = grp.add(dwg.g(id="swiss-cross"))
        group.add(
            dwg.polygon(points=[
                (18.3, 0.7), (1.6, 0.7), (0.7, 0.7), (0.7, 1.6), (0.7, 18.3), (0.7, 19.1),
                (1.6, 19.1), (18.3, 19.1), (19.1, 19.1), (19.1, 18.3), (19.1, 1.6), (19.1, 0.7)
            ], fill='black')
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

    def draw_blank_rect(self, dwg, grp, x, y, width, height):
        """Draw a empty blank rect with corners (e.g. amount, debtor)"""
        # 0.75pt ~= 0.26mm
        stroke_info = {'stroke': 'black', 'stroke_width': '0.26mm', 'stroke_linecap': 'square'}
        rect_grp = grp.add(dwg.g())
        rect_grp.add(dwg.line((x, y), (x, add_mm(y, mm(2))), **stroke_info))
        rect_grp.add(dwg.line((x, y), (add_mm(x, mm(3)), y), **stroke_info))
        rect_grp.add(dwg.line((x, add_mm(y, height)), (x, add_mm(y, height, mm(-2))), **stroke_info))
        rect_grp.add(dwg.line((x, add_mm(y, height)), (add_mm(x, mm(3)), add_mm(y, height)), **stroke_info))
        rect_grp.add(dwg.line((add_mm(x, width, mm(-3)), y), (add_mm(x, width), y), **stroke_info))
        rect_grp.add(dwg.line((add_mm(x, width), y), (add_mm(x, width), add_mm(y, mm(2))), **stroke_info))
        rect_grp.add(dwg.line(
            (add_mm(x, width, mm(-3)), add_mm(y, height)), (add_mm(x, width), add_mm(y, height)),
            **stroke_info
        ))
        rect_grp.add(dwg.line(
            (add_mm(x, width), add_mm(y, height)), (add_mm(x, width), add_mm(y, height, mm(-2))),
            **stroke_info
        ))

    def label(self, txt):
        return txt if self.language == 'en' else LABELS[txt][self.language]

    def as_svg(self, file_out, full_page=False):
        """
        Format as SVG and write the result to file_out.
        file_out can be a str, a pathlib.Path or a file-like object open in text
        mode.
        """
        if full_page:
            dwg = svgwrite.Drawing(
                size=A4,
                viewBox=('0 0 %f %f' % (mm(A4[0]), mm(A4[1]))),
            )
        else:
            dwg = svgwrite.Drawing(
                size=(A4[0], BILL_HEIGHT),  # A4 width, A6 height.
                viewBox=('0 0 %f %f' % (mm(A4[0]), mm(BILL_HEIGHT))),
            )
        dwg.add(dwg.rect(insert=(0, 0), size=('100%', '100%'), fill='white'))  # Force white background

        bill_group = self.draw_bill(dwg)
        if full_page:
            self.transform_to_full_page(dwg, bill_group)

        if isinstance(file_out, (str, Path)):
            dwg.saveas(file_out)
        else:
            dwg.write(file_out)

    def transform_to_full_page(self, dwg, bill):
        """Renders to a A4 page, adding bill in a group element.

        Adds a note about separating the bill as well.

        :param dwg: The svg drawing.
        :param bill: The svg group containing regular sized bill drawing.
        """
        y_offset = mm(A4[1]) - mm(BILL_HEIGHT)
        bill.translate(tx=0, ty=y_offset)

        # add text snippet
        x_center = mm(A4[0]) / 2
        y_pos = y_offset - mm(2)

        dwg.add(dwg.text(
            self.label("Separate before paying in"),
            (x_center, y_pos),
            text_anchor="middle",
            font_style="italic",
            **self.font_info)
        )

    def draw_bill(self, dwg):
        """Draw the bill in SVG format."""
        margin = mm(5)
        payment_left = add_mm(RECEIPT_WIDTH, margin)
        payment_detail_left = add_mm(payment_left, mm(70))

        grp = dwg.add(dwg.g())
        # Receipt
        y_pos = 15
        line_space = 3.5
        grp.add(dwg.text(self.label("Receipt"), (margin, mm(10)), **self.title_font_info))
        grp.add(dwg.text(self.label("Account / Payable to"), (margin, mm(y_pos)), **self.head_font_info))
        y_pos += line_space
        grp.add(dwg.text(
            iban.format(self.account), (margin, mm(y_pos)), **self.font_info
        ))
        y_pos += line_space
        for line_text in self.creditor.as_paragraph(max_chars=MAX_CHARS_RECEIPT_LINE):
            grp.add(dwg.text(line_text, (margin, mm(y_pos)), **self.font_info))
            y_pos += line_space

        if self.ref_number:
            y_pos += 1
            grp.add(dwg.text(self.label("Reference"), (margin, mm(y_pos)), **self.head_font_info))
            y_pos += line_space
            grp.add(dwg.text(format_ref_number(self), (margin, mm(y_pos)), **self.font_info))
            y_pos += line_space

        y_pos += 1
        grp.add(dwg.text(
            self.label("Payable by") if self.debtor else self.label("Payable by (name/address)"),
            (margin, mm(y_pos)), **self.head_font_info
        ))
        y_pos += line_space
        if self.debtor:
            for line_text in self.debtor.as_paragraph(max_chars=MAX_CHARS_RECEIPT_LINE):
                grp.add(dwg.text(line_text, (margin, mm(y_pos)), **self.font_info))
                y_pos += line_space
        else:
            self.draw_blank_rect(
                dwg, grp, x=margin, y=mm(y_pos),
                width=mm(52), height=mm(25)
            )
            y_pos += 28

        grp.add(dwg.text(self.label("Currency"), (margin, mm(80)), **self.head_font_info))
        grp.add(dwg.text(self.label("Amount"), (add_mm(margin, mm(12)), mm(80)), **self.head_font_info))
        grp.add(dwg.text(self.currency, (margin, mm(85)), **self.font_info))
        if self.amount:
            grp.add(dwg.text(format_amount(self.amount), (add_mm(margin, mm(12)), mm(85)), **self.font_info))
        else:
            self.draw_blank_rect(
                dwg, grp, x=add_mm(margin, mm(25)), y=mm(77),
                width=mm(27), height=mm(11)
            )

        # Right-aligned
        grp.add(dwg.text(
            self.label("Acceptance point"), (add_mm(RECEIPT_WIDTH, margin * -1), mm(91)),
            text_anchor='end', **self.head_font_info
        ))

        # Top separation line
        if self.top_line:
            grp.add(dwg.line(
                start=(0, mm(0.141)), end=(add_mm(RECEIPT_WIDTH, PAYMENT_WIDTH), mm(0.141)),
                stroke='black', stroke_dasharray='2 2'
            ))

        # Separation line between receipt and payment parts
        if self.payment_line:
            grp.add(dwg.line(
                start=(mm(RECEIPT_WIDTH), 0), end=(mm(RECEIPT_WIDTH), mm(BILL_HEIGHT)),
                stroke='black', stroke_dasharray='2 2'
            ))
            grp.add(dwg.text(
                "✂", insert=(add_mm(RECEIPT_WIDTH, mm(-1.5)), 40),
                font_size=16, font_family='Helvetica', rotate=[90]
            ))

        # Payment part
        grp.add(dwg.text(self.label("Payment part"), (payment_left, mm(10)), **self.title_font_info))

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
        grp.add(path)

        self.draw_swiss_cross(dwg, grp, im.width * scale_factor)

        grp.add(dwg.text(self.label("Currency"), (payment_left, mm(80)), **self.head_font_info))
        grp.add(dwg.text(self.label("Amount"), (add_mm(payment_left, mm(12)), mm(80)), **self.head_font_info))
        grp.add(dwg.text(self.currency, (payment_left, mm(85)), **self.font_info))
        if self.amount:
            grp.add(dwg.text(format_amount(self.amount), (add_mm(payment_left, mm(12)), mm(85)), **self.font_info))
        else:
            self.draw_blank_rect(
                dwg, grp, x=add_mm(RECEIPT_WIDTH, margin, mm(12)), y=mm(83),
                width=mm(40), height=mm(15)
            )

        # Right side of the bill
        y_pos = 10
        line_space = 3.5

        def add_header(text):
            nonlocal dwg, grp, payment_detail_left, y_pos
            y_pos += 1
            grp.add(dwg.text(text, (payment_detail_left, mm(y_pos)), **self.head_font_info))
            y_pos += line_space

        add_header(self.label("Account / Payable to"))
        grp.add(dwg.text(
            iban.format(self.account), (payment_detail_left, mm(y_pos)), **self.font_info
        ))
        y_pos += line_space

        for line_text in self.creditor.as_paragraph():
            grp.add(dwg.text(line_text, (payment_detail_left, mm(y_pos)), **self.font_info))
            y_pos += line_space

        if self.ref_number:
            add_header(self.label("Reference"))
            grp.add(dwg.text(
                format_ref_number(self), (payment_detail_left, mm(y_pos)), **self.font_info
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
                grp.add(dwg.text(info, (payment_detail_left, mm(y_pos)), **self.font_info))
                y_pos += line_space

        if self.debtor:
            add_header(self.label("Payable by"))
            for line_text in self.debtor.as_paragraph():
                grp.add(dwg.text(line_text, (payment_detail_left, mm(y_pos)), **self.font_info))
                y_pos += line_space
        else:
            add_header(self.label("Payable by (name/address)"))
            # The specs recomment at least 2.5 x 6.5 cm
            self.draw_blank_rect(
                dwg, grp, x=payment_detail_left, y=mm(y_pos),
                width=mm(65), height=mm(25)
            )
            y_pos += 28

        if self.final_creditor:
            add_header(self.label("In favor of"))
            for line_text in self.final_creditor.as_paragraph():
                grp.add(dwg.text(line_text, (payment_detail_left, mm(y_pos)), **self.font_info))
                y_pos += line_space

        if self.due_date:
            add_header(self.label("Payable by "))
            grp.add(dwg.text(
                format_date(self.due_date), (payment_detail_left, mm(y_pos)), **self.font_info
            ))
            y_pos += line_space

        # Bottom section
        y_pos = mm(94)
        for alt_proc_line in self.alt_procs:
            grp.add(dwg.text(
                alt_proc_line, (payment_left, y_pos), **self.proc_font_info
            ))
            y_pos += mm(2.2)
        return grp


def add_mm(*mms):
    """Utility to allow additions of '23mm'-type strings."""
    return sum(
        mm(float(m[:-2])) if isinstance(m, str) else m for m in mms
    )


def mm(val):
    """Convert val (as mm, either number of '12mm' str) into user units."""
    try:
        val = float(val.rstrip('mm'))
    except AttributeError:
        pass
    return round(val * MM_TO_UU, 5)


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
            yield text[:MAX_CHARS_PAYMENT_LINE]
            text = text[MAX_CHARS_PAYMENT_LINE:]
