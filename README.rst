.. image:: https://travis-ci.org/claudep/swiss-qr-bill.svg?branch=master
    :target: https://travis-ci.org/claudep/swiss-qr-bill

===============================
Swiss QR payment slip generator
===============================

Purpose
=======
This library generates QR payment slips for Switzerland and Liechtenstein, which follow the `Swiss Payment Standards 2019 (Version 2.1) <https://www.paymentstandards.ch/>`_. The library outputs the payment slips as SVG graphics.

Samples
-------

* `Minimal`_
* `Minimal with amount`_
* `Minimal with amount and debtor`_
* `Minimal with amount, debtor and reference number`_
* `Minimal with amount, debtor, reference number and unstructured message`_

.. _Minimal: ./sample/01_bill_minimal.svg
.. _Minimal with amount: ./sample/02_bill_amount.svg
.. _Minimal with amount and debtor: ./sample/03_bill_amount_debtor.svg
.. _Minimal with amount, debtor and reference number: ./sample/04_bill_amount_debtor_ref.svg
.. _Minimal with amount, debtor, reference number and unstructured message: ./sample/05_bill_amount_debtor_ref_msg.svg

Installation
============

    $ pip install qrbill

Usage example
=============
The library can be used as an instance or via the command line:

Python
------

.. code-block:: python

    from qrbill.bill import QRBill, Address

    bill = QRBill()
    bill.account = "CH9889144356966475815"
    bill.creditor = Address(name="Hans Muster", address_line_1="Musterstrasse 1", pcode=1000, town="Musterhausen")

    bill.save("my_bill.svg")

Command line
------------

Minimal::

    $ qrbill --account "CH4431999123000889012" --creditor-name "John Doe"
      --creditor-postalcode 2501 --creditor-city "Biel"

More complete::

    $ qrbill --account "CH58 0079 1123 0008 8901 2" --creditor-name "Robert Schneider AG"
    --creditor-street "Rue du Lac 1268" --creditor-postalcode "2501" --creditor-city "Biel"
    --extra-infos "Bill No. 3139 for garden work and disposal of cuttings."
    --debtor-name "Pia Rutschmann" --debtor-street "Marktgasse 28" --debtor-postalcode "9400"
    --debtor-city "Rorschach" --due-date "2019-10-31" --language "de"

For usage::

    $ qrbill -h


Running tests
=============

You can run tests either by executing::

    $ python tests/test_qrbill.py

or::

    $ python setup.py test

