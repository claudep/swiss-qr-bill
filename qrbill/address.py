from iso3166 import countries

from qrbill.errors import ValidationError


class Address:
    def __init__(self, name=None, address_line_1=None, address_line_2=None, pcode=None, town=None, country=None,
                 is_structured_address=True):
        """Store a postal address

        Address is either a
         - structured address (name, address_line_2 building no, country-postal code town)
         - combined address (name, address line 1, address line 2) postal code and town must not be provided

        :param name: Name of the person or company
        :param address_line_1: address_line_2 or address line 1
        :param address_line_2: building no or address line 2
        :param pcode: postal code (without country code prefix)
        :param town: town
        :param country: country
        :param is_structured_address: Indicator if is structured address (default) or combined address
        """
        self.is_structured_address = is_structured_address  # has to be before address lines

        self.name = name
        self.address_line_1 = address_line_1
        self.address_line_2 = address_line_2
        self.pcode = pcode
        self.town = town
        self.country = country

    def __repr__(self):
        return f"<{self.__class__.__name__} " \
               f"(name:{self.name}, address:{self.address_line_1}, {self.address_line_2}, {self.pcode} {self.town}, " \
               f"{self.country})>"

    def __str__(self):
        return f"{self.name}, {self.address_line_1}, {self.address_line_2}, {self.pcode} {self.town}, {self.country}"

    def data_list(self):
        """Return address values as a list, appropriate for qr code generation."""
        data_list = []

        if self.is_structured_address:
            data_list.append("S")  # structured address
        else:
            data_list.append("K")  # combined address element

        data_list.extend([self._name, self.address_line_1, self.address_line_2, self._pcode, self._town, self._country])

        return data_list

    def as_paragraph(self):
        address = [self.name]

        if self.is_structured_address:
            address.append(f"{self.address_line_1} {self.address_line_2}")
            address.append(f"{self.country}-{self.pcode} {self.town}")
        else:
            address.append(self.address_line_1)
            address.append(self.address_line_2)

        return address

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = self.check_length(name, "Address name", min_len=1, max_len=70)

    @property
    def address_type(self):
        if self.is_structured_address:
            return "S"

        return "K"

    @property
    def address_line_1(self):
        return self._address_line_1

    @address_line_1.setter
    def address_line_1(self, street):
        self._address_line_1 = self.check_length(street, "Address line 1", max_len=70)

    @property
    def address_line_2(self):
        return self._address_line_2

    @address_line_2.setter
    def address_line_2(self, address_line_2):
        if isinstance(address_line_2, int):
            address_line_2 = str(address_line_2)

        if self.is_structured_address:
            self._address_line_2 = self.check_length(address_line_2, "Building number", max_len=16)
        else:
            self._address_line_2 = self.check_length(address_line_2, "Address line 2", max_len=70)

    @property
    def pcode(self):
        return self._pcode

    @pcode.setter
    def pcode(self, pcode):
        if isinstance(pcode, int):
            pcode = str(pcode)
        self._pcode = self.check_length(pcode, "Postal code", max_len=16)

    @property
    def town(self):
        return self._town

    @town.setter
    def town(self, town):
        self._town = self.check_length(town, "City", max_len=35)

    @property
    def country(self):
        return self._country

    @country.setter
    def country(self, country):
        if not country:
            self._country = None
        else:
            country = (country or "").strip()
            # allow users to write the country as if used in an address in the local language
            if country.lower() in ["schweiz", "suisse", "svizzera", "svizra"]:
                country = "CH"
            if country.lower() in ["fürstentum liechtenstein"]:
                country = "LI"
            try:
                self._country = countries.get(country).alpha2
            except KeyError:
                raise ValidationError("The country code '%s' is not valid" % country)

    @staticmethod
    def check_length(var, var_name, min_len=-1, max_len=-1):
        if not var:
            return None
        var = var.strip()
        if min_len != -1 and var and len(var) < min_len:
            raise ValidationError(f"{var_name} cannot have less than {min_len} characters")
        if max_len != -1 and var and len(var) > max_len:
            raise ValidationError(f"{var_name} cannot have more than {max_len} characters")
        return var
