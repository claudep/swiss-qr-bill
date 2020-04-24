import unittest

from qrbill.address import Address
from qrbill.errors import ValidationError


class AddressInitializationTest(unittest.TestCase):

    def test_empty_address(self):
        address = Address()
        self.assertEqual(repr(address), "<Address (name:None, address:None, None, None None, None)>")
        self.assertEqual(str(address), "None, None, None, None None, None")

    def test_full_address(self):
        name, street, pcode, town = "Hans Muster", "Musterstrasse 1", 1000, "Musterhausen"
        country = "CH"
        address = Address(name=name, address_line_1=street, pcode=pcode, town=town, country=country)

        self.assertEqual(str(address), f"{name}, {street}, None, {pcode} {town}, {country}")


class AddressPropertyTest(unittest.TestCase):

    def setUp(self) -> None:
        self.address = Address()

    def test_stepwise_attr(self):
        name, street, pcode, town = "Hans Muster", "Musterstrasse 1", 1000, "Musterhausen"
        country = "CH"

        self.address.name = name
        self.address.address_line_1 = street
        self.address.pcode = pcode
        self.address.town = town
        self.address.country = country

        self.assertEqual(str(self.address), f"{name}, {street}, None, {pcode} {town}, {country}")

    def test_max_length(self):
        attrs = {"name": 70, "address_line_1": 70, "address_line_2": 70, "pcode": 16, "town": 35}

        for attr, max_length in attrs.items():
            with self.assertRaises(ValidationError):
                self.address.__setattr__(attr, "a" * (max_length + 1))


class StructuredAddressTest(unittest.TestCase):

    def setUp(self) -> None:
        self.name, self.street, self.building_no, self.pcode, = "Hans Muster", "Musterstrasse", 1, "1000"
        self.town, self.country = "Musterhausen", "CH"
        self.address = Address(name=self.name, address_line_1=self.street, address_line_2=self.building_no,
                               pcode=self.pcode,
                               town=self.town, country=self.country, is_structured_address=True)

    def test_address_type(self):
        self.assertEqual(self.address.address_type, "S")

    def test_data_list(self):
        data_list = self.address.data_list()

        self.assertListEqual(data_list, ["S", self.name, self.street, str(self.building_no), self.pcode, self.town,
                                         self.country])

    def test_as_paragraph(self):
        paragraph = self.address.as_paragraph()

        self.assertListEqual(paragraph, [self.name, f"{self.street} {self.building_no}",
                                         f"{self.country}-{self.pcode} {self.town}"])

    def test_country(self):
        for country in ["Schweiz", "Suisse", "Svizzera", "Svizra"]:
            self.address.country = country
            self.assertEqual(self.address.country, "CH")

        for country in ["Fürstentum Liechtenstein", "Liechtenstein"]:
            self.address.country = country
            self.assertEqual(self.address.country, "LI")

        self.address.country = "Spain"
        self.assertEqual(self.address.country, "ES")

        # TODO: Other countries only work with english wording?
        with self.assertRaises(ValidationError):
            self.address.country = "Spanien"


class CombinedAddressTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.name, cls.address_line_1, cls.address_line_2, = "Hans Muster", "Musterstrasse 1", "CH-1000 Musterhausen"
        cls.address = Address(name=cls.name, address_line_1=cls.address_line_1, address_line_2=cls.address_line_2,
                              is_structured_address=False)

    def test_address_type(self):
        self.assertEqual(self.address.address_type, "K")

    def test_data_list(self):
        data_list = self.address.data_list()

        self.assertListEqual(data_list, ["K", self.name, self.address_line_1, self.address_line_2, None, None, None])

    def test_as_paragraph(self):
        paragraph = self.address.as_paragraph()

        self.assertListEqual(paragraph, [self.name, self.address_line_1, self.address_line_2])
