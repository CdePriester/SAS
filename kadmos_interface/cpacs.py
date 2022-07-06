from lxml import etree
from lxml.etree import ElementTree


class PortableCpacs:
    """Tiny CPACS class capable of reading and writing to a CPACS file"""
    def __init__(self, cpacs_in: str = None):
        self.parser = etree.XMLParser(remove_blank_text=True)
        if cpacs_in is not None:
            self.root = ElementTree(file=cpacs_in, parser=self.parser).getroot()
        else:
            self.root = None

    def get_values(self, xpaths: list[str]) -> list:
        values = [self.get_value(xpath) for xpath in xpaths]
        return values

    def get_value(self, xpath: str) -> float:
        return float(self.root.xpath(xpath)[0].text)

    def update_value(self, xpath: str, value: float) -> None:
        if self.root is not None:
            el = self.root.xpath(xpath)
        else:
            el = None

        if not el:
            el = self.build_xpath(xpath)

        el[0].text = str(value)

    def build_xpath(self, xpath) -> str:
        """Update (or set) an xpath that does not yet exist in a cpacs document.

        :param xpath: xpath of not-yet existing element
        :type xpath: str
        :return: list of all created elements
        :rtype: list
        """
        components = xpath.split("/")

        if self.root is None:
            element = self.parser.makeelement
            self.root = element(components[1])

        previous_el = self.root

        current_xpath = '/'
        for component in components:
            if component == '':
                continue
            if not self.root.xpath(current_xpath + '/' + component):
                updated_el = etree.SubElement(previous_el, component)
            else:
                updated_el = self.root.xpath(current_xpath + '/' + component)[0]

            previous_el = updated_el
            current_xpath += component + '/'

        return self.root.xpath(xpath)

    def save(self, cpacs_out: str):
        ElementTree(self.root).write(cpacs_out, method='xml', pretty_print=True, encoding='UTF-8')