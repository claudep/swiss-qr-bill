.. -*- mode: rst -*-

ChangeLog
=========

1.1.0 (2023-12-16)
------------------
- Add Arial font name in addition to Helvetica for better font fallback on some
  systems.
- Drop support for Python < 3.8, and add testing for Python 3.11 and 3.12.

1.0.0 (2022-09-21)
------------------
- BREAKING: Removed the ``due-date`` command line argument and the ``due_date``
  QRBill init kwarg, as this field is no longer in the most recent specs (#84).
- Handle line breaks in additional information, so it is showing in the printed
  version, but stripped from the QR data (#86).
- Improved performance by deactivating debug mode in svgwrite (#82).

0.8.1 (2022-05-10)
------------------
- Fixed a regression where the currency was not visible in the payment part
  (#81).

0.8.0 (2022-04-13)
------------------
- Replaced ``##`` with ``//`` as separator in additional informations (#75).
- Print scissors symbol on horizontal separation line when not in full page.
  WARNING: the resulting bill is 1 millimiter higher to be able to show the
  entire symbol (#65).
- Renamed ``--extra-infos`` command line parameter to ``--additional-information``
  and renamed ``extra_infos`` and ``ref_number`` ``QRBill.__init__`` arguments
  to ``additional_information`` and ``reference_number``, respectively.
  The old arguments are still accepted but raise a deprecation warning (#68).

0.7.1 (2022-03-07)
------------------
- Fixed bad position of amount rect on receipt part (#74).
- Increased title font size and section spacing on payment part.

0.7.0 (2021-12-18)
------------------
- License changed from GPL to MIT (#72).
- Prevented separation line filled on some browsers.
- Scissors symbol is now an SVG path (#46).

0.6.1 (2021-05-01)
------------------
- Added ``--version`` command-line option.
- QR-code size is now more in line with the specs, including the embedded Swiss
  cross (#58, #59).
- Widen space at the right of the QR-code (#57).
- A new ``--font-factor`` command-line option allows to scale the font if the
  actual size does not fit your needs (#55).

0.6.0 (2021-02-11)
------------------
- Added the possibility to include newline sequences in name, street, line1, or
  line2 part of addresses to improve printed line wrapping of long lines.
- Moved QR-code and amount section to better comply with the style guide (#52).
- Dropped support for EOL Python 3.5 and confirmed support for Python 3.9.

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
