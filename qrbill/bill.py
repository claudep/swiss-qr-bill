from decimal import Decimal

import qrcode.image.svg
from qrcode import QRCode
from stdnum import iban, iso11649
from stdnum.ch import esr

from qrbill.address import Address
from qrbill.errors import MissingAttributeError, ConversionError, ValidationError
from qrbill.printer import SVGPrinter, Printer

IBAN_ALLOWED_COUNTRIES = ["CH", "LI"]
QR_IID = {"start": 30000, "end": 31999}
AMOUNT_REGEX = r"^\d{1,9}\.\d{2}$"
DATE_REGEX = r"(\d{4})-(\d{2})-(\d{2})"
MM_TO_UU = 3.543307

# Annex D: Multilingual headings
LABELS = {
    "Payment part": {"de": "Zahlteil", "fr": "Section paiement", "it": "Sezione pagamento"},
    "Account / Payable to": {
        "de": "Konto / Zahlbar an",
        "fr": "Compte / Payable à",
        "it": "Conto / Pagabile a",
    },
    "Reference": {"de": "Referenz", "fr": "Référence", "it": "Riferimento"},
    "Additional information": {
        "de": "Zusätzliche Informationen",
        "fr": "Informations supplémentaires",
        "it": "Informazioni supplementari",
    },
    "Currency": {"de": "Währung", "fr": "Monnaie", "it": "Valuta"},
    "Amount": {"de": "Betrag", "fr": "Montant", "it": "Importo"},
    "Receipt": {"de": "Empfangsschein", "fr": "Récépissé", "it": "Ricevuta"},
    "Acceptance point": {"de": "Annahmestelle", "fr": "Point de dépôt", "it": "Punto di accettazione"},
    "Separate before paying in": {
        "de": "Vor der Einzahlung abzutrennen",
        "fr": "A détacher avant le versement",
        "it": "Da staccare prima del versamento",
    },
    "Payable by": {"de": "Zahlbar durch", "fr": "Payable par", "it": "Pagabile da"},
    "Payable by (name/address)": {
        "de": "Zahlbar durch (Name/Adresse)",
        "fr": "Payable par (nom/adresse)",
        "it": "Pagabile da (nome/indirizzo)",
    },
    # The extra ending space allows to differentiate from the other "Payable by" above.
    "Payable by ": {"de": "Zahlbar bis", "fr": "Payable jusqu’au", "it": "Pagabile fino al"},
    "In favour of": {"de": "Zugunsten", "fr": "En faveur de", "it": "A favore di"},
}


class QRBill:
    """This class represents a Swiss QR Bill."""
    # Header
    qr_type = "SPC"  # Swiss Payments Code
    qr_version = "0200"  # Version of the specification
    coding_type = 1  # Latin character set
    allowed_currencies = ("CHF", "EUR")
    # QR reference, Creditor Reference (ISO 11649), without reference
    reference_types = ("QRR", "SCOR", "NON")
    trailer = "EPD"  # End Payment Data

    def __init__(self, account=None, creditor=None, ultimate_creditor=None, amount=None, currency="CHF", debtor=None,
                 ref_number=None, unstructured_message=None, billing_info=None, language="en", printer=SVGPrinter()):
        """

        :param account: IBAN of the payment recipient (creditor)
        :param creditor: Address of the creditor (as instance of Address or as dict)
        :param ultimate_creditor: Reserved for future use
        :param amount:
        :param currency:
        :param debtor: Address of the debtor (as instance of Address or as dict)
        :param ref_number:
        :param unstructured_message: payment purpose or additional textual information
        :param billing_info: coded information for automated booking of the payment
        :param language:
        :param printer: Class used to draw the bill: default SVGPrinter
        """
        # Creditor information
        self.account = account
        # Creditor
        self.creditor = self._convert_address(creditor)
        # Ultimate creditor
        self.ultimate_creditor = ultimate_creditor
        # Payment amount information
        self.amount = amount
        self.currency = currency
        # Ultimate debtor
        self.debtor = debtor
        # Payment reference
        self.ref_number = ref_number
        # Additional information
        self.unstructured_message = unstructured_message
        self.billing_info = billing_info

        # Internal
        self.language = language
        self.printer = printer

    def __repr__(self):
        return f"<{self.__class__.__name__} (account:{self.account}, creditor:{self.creditor}, amount:{self.amount})>"

    # Creditor information
    @property
    def account(self):
        return self._account

    @account.setter
    def account(self, account):
        """ Account number (IBAN) according ISO-13616

        Only IBANs with CH or LI country code are permitted.

        :param account: Account number (IBAN) according ISO-13616
        """
        if not account:
            self._account = None
            return

        if not iban.is_valid(account):
            raise ValidationError("Invalid IBAN number")

        account = iban.validate(account)

        if account[:2] not in IBAN_ALLOWED_COUNTRIES:
            raise ValidationError("IBAN must start with: %s" % ", ".join(IBAN_ALLOWED_COUNTRIES))

        account = iban.format(account, separator=" ")

        self._account = account

    @property
    def iban_iid(self):
        return int(self.account[5:9])

    @property
    def is_iban_iid(self):
        return QR_IID["start"] <= self.iban_iid <= QR_IID["end"]

    # Creditor
    @property
    def creditor(self):
        return self._creditor

    @creditor.setter
    def creditor(self, creditor):
        if not creditor:
            self._creditor = None
        self._creditor = self._convert_address(creditor)

    # Ultimate Creditor
    @property
    def ultimate_creditor(self):
        return self._final_creditor

    @ultimate_creditor.setter
    def ultimate_creditor(self, final_creditor):
        """ Reserved for further use"""
        if not final_creditor:
            self._final_creditor = None
        else:
            raise NotImplementedError("Ultimate creditor is reserved for future use, must not be used")

    # Payment amount information
    @property
    def currency(self):
        return self._currency

    @currency.setter
    def currency(self, currency):
        """ Payment currency

        Only CHF and EUR are permitted.

        :param currency: 3-digit alphanumeric currency code according to ISO 4217
        :return:
        """
        if currency not in self.allowed_currencies:
            raise ValidationError("Currency can only contain: %s" % ", ".join(self.allowed_currencies))
        self._currency = currency

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, amount):
        """ Payment amount

        A whitespace is used to separate thousands and a full stop as decimal separator. No leading zeros should be
        used. The value must be smaller than one billion (1 000 000 000.00)

        :param amount: Payment amount
        :return:
        """

        if amount is not None:

            if isinstance(amount, str):
                amount = amount.replace("'", "").strip()
                amount = Decimal(amount)
            elif not isinstance(amount, (int, float)):
                raise ValidationError("Amount can only be specified as str or Decimal.")

            # Use blank (space) as thousands separator
            amount = f"{amount:,.2f}".replace(",", " ")

            if len(amount) > 14:
                raise ValidationError("Value must be smaller than one billion (1 000 000 000.00)")

        self._amount = amount

    # Ultimate debtor
    @property
    def debtor(self):
        return self._debtor

    @debtor.setter
    def debtor(self, debtor):
        if not debtor:
            self._debtor = None

        self._debtor = self._convert_address(debtor)

    # Payment reference
    @property
    def ref_type(self):
        if not self.ref_number:
            return "NON"

        if iso11649.is_valid(self.ref_number):
            return "SCOR"

        if esr.is_valid(self.ref_number):
            return "QRR"

    @property
    def ref_number(self):
        return self._ref_number

    @ref_number.setter
    def ref_number(self, ref_number):
        """ Reference

        Is either a QR reference or an ISO 11649 creditor reference

        :param ref_number:
        :return:
        """
        if not ref_number:
            self._ref_number = None

        elif iso11649.is_valid(ref_number):
            self._ref_number = iso11649.format(ref_number)

        elif esr.is_valid(ref_number):
            self._ref_number = esr.format(ref_number)

        else:
            raise ValidationError(f"Invalid reference number {ref_number}")

    # Additional information
    @property
    def unstructured_message(self):
        return self._unstructured_message

    @unstructured_message.setter
    def unstructured_message(self, unstructured_message):
        billing_info_length = len(self.billing_info) if self.billing_info else 0

        if unstructured_message and len(unstructured_message) + billing_info_length > 140:
            raise ValidationError(
                "Unstructured message and billing information cannot contain more than 140 characters")
        self._unstructured_message = unstructured_message

    @property
    def billing_info(self):
        if hasattr(self, "_billing_info"):
            return self._billing_info

        return None

    @billing_info.setter
    def billing_info(self, billing_info):
        unstructured_msg_length = len(self.unstructured_message) if self.unstructured_message else 0

        if billing_info and len(billing_info) + unstructured_msg_length > 140:
            raise ValidationError(
                "Unstructured message and billing information cannot contain more than 140 characters")
        self._billing_info = billing_info

    # Internal
    @property
    def language(self):
        return self._language

    @language.setter
    def language(self, language):
        if language not in ["en", "de", "fr", "it"]:
            raise ValidationError("Language can only be 'en', 'de', 'fr', or 'it'")
        self._language = language

    def recipient(self):
        """
        :return: list containing IBAN and creditor information
        """
        recipient = [self.account]
        recipient.extend(self.creditor.as_paragraph())
        return recipient

    def additional_info(self):
        """
        :return: list containing unstructured message and billing information
        """

        return [self.unstructured_message, self.billing_info]

    def sender(self):
        if self.debtor:
            return self.debtor.as_paragraph()

        return []

    def qr_data(self):
        """Create str used to encoded in QR code."""
        data = []

        def address_as_list(address):
            if address:
                data.append(address.name)
                data.append(address.address_line_1)
                data.append(address.address_line_2)
                data.append(address.pcode)
                data.append(address.town)
                data.append(address.country)
            else:
                data.extend([None] * 7)

        # Header
        data.append(self.qr_type)
        data.append(self.qr_version)
        data.append(self.coding_type)

        # Creditor information
        data.append(self.account)

        # Creditor
        data.append(self.creditor.address_type)
        address_as_list(self.creditor)

        # Ultimate Creditor
        data.append(self.ultimate_creditor.address_type if self.ultimate_creditor else None)
        address_as_list(Address(country=""))

        # Payment information
        data.append(self.amount)
        data.append(self.currency)

        # Ultimate debtor
        address_as_list(self.debtor)

        # Payment reference
        data.append(self.ref_type)
        data.append(self.ref_number)

        # Additional information
        data.append(self.unstructured_message)
        data.append(self.trailer)
        data.append(self.billing_info)

        # Alternative schemes
        # data.append(self.av1_param)
        # data.append(self.av2_param)

        return "\r\n".join([str(d) if d else "" for d in data])

    def qr_code(self, data=None, image_factory=qrcode.image.svg.SvgPathImage, **kwargs):
        """ Generate QR code instance

        :param data:
        :param image_factory:
        :param kwargs: kwargs for QRCode
        :return: QRCode instance
        """

        if not data:
            data = self.qr_data()

        code = QRCode(image_factory=image_factory, **kwargs)
        code.add_data(data)
        return code

    def label(self, txt):
        return txt if self.language == "en" else LABELS[txt][self.language]

    def save(self, file_name, printer=None):
        """ Save bill under the given file name

        :param file_name: filename to save the bill
        :param printer: printer used to create the bill
        :return: None
        """
        if isinstance(printer, Printer):
            self.printer = printer

        if not self.account:
            raise MissingAttributeError("Account (IBAN) is mandatory")
        if not self.creditor:
            raise MissingAttributeError("Creditor is mandatory")

        self.printer.draw(file_name, self)

    @staticmethod
    def _convert_address(address):
        if not address:
            return None
        if isinstance(address, Address):
            return address
        if isinstance(address, dict):
            return Address(**address)

        return ConversionError(f"Address can only be an instance {Address.__name__} or dict. Cannot convert {address}")
