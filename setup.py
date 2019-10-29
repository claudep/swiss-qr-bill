#!/usr/bin/env python

from setuptools import setup

from pathlib import Path

readme = Path(__file__).parent / 'README.rst'
with readme.open() as f:
    long_description = f.read()

setup(
    name='qrbill',
    version='0.3',
    description='A library to generate Swiss QR-bill payment slips',
    long_description=long_description,
    license='GPLv3',
    author='Claude Paroz',
    author_email='claude@2xlibre.net',
    packages=['qrbill'],
    scripts=['scripts/qrbill'],
    install_requires=['iso3166', 'validators', 'qrcode', 'svgwrite'],
    test_suite='tests',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
    ],
)
