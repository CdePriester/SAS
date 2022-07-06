import os
from lxml import etree
from lxml.etree import ElementTree

from sas.kadmos_interface.cpacs import PortableCpacs

class SellarCPACS:
    """Basic governing class to handle CPACS for the sellar problem.

    All disciplines can import this class, and easily work with the variables from the cpacs.
    """
    # Old
    lookup_xpath = {'x0': '/dataSchema/variables/x0',
                    'x1': '/dataSchema/variables/x1',
                    'z1': '/dataSchema/variables/z1',
                    'z2': '/dataSchema/variables/z2',
                    'y1': '/dataSchema/analyses/y1',
                    'y2': '/dataSchema/analyses/y2',
                    'g1': '/dataSchema/analyses/g1',
                    'g2': '/dataSchema/analyses/g2',
                    'f': '/dataSchema/analyses/f',
                    'a': '/dataSchema/settings/a',
                    'b': '/dataSchema/settings/b',
                    'c': '/dataSchema/settings/c'
                    }
    """
    # New
    lookup_xpath = {'x0': '/dataSchema/variables/x0',
                    'x1': '/dataSchema/variables/x1',
                    'z1': '/dataSchema/variables/z1',
                    'z2': '/dataSchema/variables/z2',
                    'y1': '/dataSchema/analyses/y1',
                    'y2': '/dataSchema/analyses/y2',
                    'g1': '/dataSchema/analyses/g1',
                    'g2': '/dataSchema/analyses/g2',
                    'f': '/dataSchema/analyses/f',
                    'a': '/dataSchema/settings/a',
                    'b': '/dataSchema/settings/b',
                    'c': '/dataSchema/settings/c'
                    }"""

    def __init__(self, path='ToolInput', filename='cpacs_in.xml'):
        """Open and read cpacs from certain folder and file."""
        current_dir = os.getcwd()

        cpacs_in = os.path.join(current_dir, path, filename)

        self.cpacs = PortableCpacs(cpacs_in=cpacs_in)

    def save_cpacs(self, path='ToolOutput', filename='cpacs_out.xml'):
        """Save changes to specified location"""
        current_dir = os.getcwd()
        cpacs_out = os.path.join(current_dir, path, filename)

        self.cpacs.save(cpacs_out=cpacs_out)

    def get_value(self, var):
        """Retrieve value for parameter from cpacs file"""
        xpath = self._get_xpath(var)
        val = self.cpacs.get_value(xpath)

        return val

    def update_value(self, var, updated_value):
        """Update value for parameter from cpacs file"""
        xpath = self._get_xpath(var)

        self.cpacs.update_value(xpath, updated_value)

    def _get_xpath(self, var):
        """Get xpath beloning to sellar cpacs file"""
        assert var in self.lookup_xpath, f'Cannot find xpath for variable {var}'

        return self.lookup_xpath[var]


if __name__ == "__main__":
    cpacs = SellarCPACS()

    print(cpacs.get_value('x1'))