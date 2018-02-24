.. image:: https://travis-ci.org/claudep/swiss-qr-bill.svg?branch=master
    :target: https://travis-ci.org/claudep/swiss-qr-bill

Python library to generate Swiss QR-bills
=========================================

From January 2019, all Swiss payment slips will have to be formatted as
QR-bills.
Specifications can be found on https://www.paymentstandards.ch/

This library is aimed to produce properly-formatted QR-bills as SVG files
from command line input.

Command line usage example
==========================

Minimal:
$ qrbill --account "CH4431999123000889012" --creditor-name "John Doe" --creditor-postalcode 2501 --creditor-city "Biel"

More complete:
$ qrbill --account "CH58 0079 1123 0008 8901 2" --creditor-name "Robert Schneider AG" --creditor-street "Rue du Lac 1268" --creditor-postalcode "2501" --creditor-city "Biel" --extra-infos "Bill No. 3139 for garden work and disposal of cuttings." --debtor-name "Pia Rutschmann" --debtor-street "Marktgasse 28" --debtor-postalcode "9400" --debtor-city "Rorschach" --due-date "2019-10-31"

For usage:
$ qrbill -h

If no `--output` SVG file path is specified, the SVG file will be named after
the account and the current date/time and written in the current directory.

Running tests
=============

You can run tests either by executing:

$ python tests/test_qrbill.py

or

$ python setup.py test
