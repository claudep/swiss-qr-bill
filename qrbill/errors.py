class QRBillError(Exception):
    pass


class MissingAttributeError(QRBillError):
    pass


class ValidationError(QRBillError):
    pass


class ConversionError(QRBillError):
    pass
