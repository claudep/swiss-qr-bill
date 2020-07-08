.. -*- mode: rst -*-

ChangeLog
=========

Unreleased
----------

- Fix for missing country field in QR code when using CombinedAddress (#31).
- Added support for printing bill to full A4 format, using the ``full_page``
  parameter of ``QRBill.as_svg()`` or the CLI argument ``--full-page``.

0.5 (2020-06-24)
----------------

- ``QRBill.as_svg()`` accepts now file-like objects.
- Added support for combined address format.
- A top separation line is now printed by default. It can be deactivated
  through the ``top_line`` boolean parameter of ``QRBill.__init__()``.
- The error correction level of the QR code conforms now to the spec (M).

0.4 (2020-02-24)
----------------

Changes were not logged until version 0.4. Development stage was still alpha.
