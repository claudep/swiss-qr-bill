import unittest

from qrbill.address import Address


class AddressInitializationTest(unittest.TestCase):

    def test_empty_address(self):
        address = Address()
        self.assertEqual(repr(address), "<Address (name:, address:, ,  , CH)>")
        self.assertEqual(str(address), ", , ,  , CH")

    def test_full_address(self):
        name, street, pcode, town = "Hans Muster", "Musterstrasse 1", 1000, "Musterhausen"
        country = "CH"
        address = Address(name=name, address_line_1=street, pcode=pcode, town=town, country=country)

        self.assertEqual(str(address), f"{name}, {street}, , {pcode} {town}, {country}")


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

        self.assertEqual(str(self.address), f"{name}, {street}, , {pcode} {town}, {country}")

    def test_max_length(self):
        attrs = {"name": 70, "address_line_1": 70, "address_line_2": 70, "pcode": 16, "town": 35}

        for attr, max_length in attrs.items():
            with self.assertRaises(ValueError):
                self.address.__setattr__(attr, "a" * (max_length + 1))


class AddressFunctionTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.name, cls.street, cls.building_no, cls.pcode, = "Hans Muster", "Musterstrasse", 1, "1000"
        cls.town, cls.country = "Musterhausen", "CH"
        cls.address = Address(name=cls.name, address_line_1=cls.street, address_line_2=cls.building_no, pcode=cls.pcode,
                              town=cls.town, country=cls.country)

    def test_data_list(self):
        data_list = self.address.data_list()

        self.assertListEqual(data_list, ["S", self.name, self.street, str(self.building_no), self.pcode, self.town,
                                         self.country])

    def test_as_paragraph(self):
        paragraph = self.address.as_paragraph()

        self.assertListEqual(paragraph, [self.name, f"{self.street} {self.building_no}",
                                         f"{self.country}-{self.pcode} {self.town}"])
