.. image:: https://travis-ci.org/claudep/swiss-qr-bill.svg?branch=master
    :target: https://travis-ci.org/claudep/swiss-qr-bill
.. image:: https://img.shields.io/pypi/v/qrbill.svg
   :target: https://pypi.python.org/pypi/qrbill/

Python library to generate Swiss QR-bills
=========================================

From 2020, Swiss payment slips will progressively be converted to the
QR-bill format.
Specifications can be found on https://www.paymentstandards.ch/

This library is aimed to produce properly-formatted QR-bills as SVG files
either from command line input or by using the ``QRBill`` class.

Installation
============

You can easily install this library with::

    $ pip install qrbill

Command line usage example
==========================

Minimal::

    $ qrbill --account "CH5800791123000889012" --creditor-name "John Doe"
      --creditor-postalcode 2501 --creditor-city "Biel"

More complete::

    $ qrbill --account "CH44 3199 9123 0008 8901 2" --reference-number "210000000003139471430009017"
    --creditor-name "Robert Schneider AG" --creditor-street "Rue du Lac 1268"
    --creditor-postalcode "2501" --creditor-city "Biel"
    --extra-infos "Bill No. 3139 for garden work and disposal of cuttings."
    --debtor-name "Pia Rutschmann" --debtor-street "Marktgasse 28" --debtor-postalcode "9400"
    --debtor-city "Rorschach" --due-date "2019-10-31" --language "de"

For usage::

    $ qrbill -h

If no `--output` SVG file path is specified, the SVG file will be named after
the account and the current date/time and written in the current directory.

Python usage example
====================

::

    >>> from qrbill.bill import QRBill
    >>> my_bill = QRBill(
            account='CH5800791123000889012',
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
            },
            amount='22.45',
        )
    >>> bill.as_svg('/tmp/my_bill.svg')

Outputting as PDF
=================

If you want to produce a PDF version of the resulting bill, we suggest using the
`svglib <https://pypi.org/project/svglib/>` library. It can be used on the
command line with the `svg2pdf` script, or directly from Python::

    >>> import tempfile
    >>> from qrbill.bill import QRBill
    >>> from svglib.svglib import svg2rlg
    >>> from reportlab.graphics import renderPDF

    >>> my_bill = QRBill(
            account='CH5800791123000889012',
            creditor={
                'name': 'Jane', 'pcode': '1000', 'city': 'Lausanne', 'country': 'CH',
            },
            amount='22.45',
        )
    >>> with tempfile.NamedTemporaryFile(mode='w') as temp:
    >>>     my_bill.as_svg(temp)
    >>>     temp.seek(0)
    >>>     drawing = svg2rlg(temp.name)
    >>> renderPDF.drawToFile(drawing, "file.pdf")

Running tests
=============

You can run tests either by executing::

    $ python tests/test_qrbill.py

or::

    $ python setup.py test
