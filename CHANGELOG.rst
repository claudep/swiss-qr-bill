.. -*- mode: rst -*-

ChangeLog
=========

Unreleased
----------
- Added the possibility to include newline sequences in name, street, line1, or
  line2 part of addresses to improve printed line wrapping of long lines.

0.5.3 (2021-01-25)
------------------
- Enforced black as swiss cross background color.
- Allowed output with extension other than .svg (warning instead of error).
- Split long address lines to fit in available space (#48).

0.5.2 (2020-11-17)
------------------

- Final creditor is only for future use, it was removed from command line
  parameters.
- Capitalized Helvetica font name in code (#43).
- The top line was printed a bit lower to be more visible (#42).

0.5.1 (2020-08-19)
------------------

- Fix for missing country field in QR code when using CombinedAddress (#31).
- Added support for printing bill to full A4 format, using the ``full_page``
  parameter of ``QRBill.as_svg()`` or the CLI argument ``--full-page``.
- The vertical separation line between receipt and main part can be omitted
  through the ``--no-payment-line`` CLI argument.
- A new ``--text`` command line parameter allows for a raw text output.
- Support for Alternate procedures lines was added (``--alt-procs`` argument,
  #40).

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
