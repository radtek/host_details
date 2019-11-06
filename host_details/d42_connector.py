"""
Connector to import things from device42 into hostinfo
"""
import os
from Device42.config import ConfigData
from Device42.dev42.devices import Devices
import requests

from host_details.compat import ConfigParser

ROLE_NORMALIZE = {
    'hostingnode': 'hn',
    'managementnode': 'mn',
    'networkhostingnode': 'nhn',
    'storagenode': 'sn',
}


# pylint: disable=too-few-public-methods
class D42Connector():
    """ Provides object interface to d42 """
    def __init__(self):
        # parse configuration files to get session information.
        #  Valid configurations can exist in the ansible
        #  repo/inventories/d42.ini and ~/.config/d42.ini. Typically site
        #  configuration would be included in the repo, and credentials in your
        #  homedir. Also, all variables can be overriden/set through the
        #  environment
        scriptbasename = 'd42'
        scriptbasename = os.path.basename(scriptbasename)
        scriptbasename = scriptbasename.replace('.py', '')
        # SafeConfigParser allows interpolation, passing in os.environ makes
        #  env variables available
        config = ConfigParser.SafeConfigParser(os.environ)
        config.read(os.path.join(os.path.dirname(__file__),
                                 '{}.ini'.format(scriptbasename)))
        config.read(os.path.join('{}'.format(os.path.expanduser("~")),
                                 '.config', '{}.ini'.format(scriptbasename)))

        # start with empty configuration variables
        self.server, self.user, self.password = [None, None, None]

        # load d42 configuration settings
        self.server = config.get('d42', 'server')
        self.user = config.get('d42', 'user')
        self.password = config.get('d42', 'password')

        # setup interface to dev42
        self.d42_settings = ConfigData(dev42=self.server,
                                       duser=self.user,
                                       dpassword=self.password)

    def get_by_hostname(self, host):
        """ Queries device42 for info about a single host """
        # Things we want to take from d42
        import_custom_fields = ['Role']
        import_values = []

        devices = Devices(self.d42_settings)
        rtrn = {}
        rtrn['err'] = []
        try:
            dev = devices.get_device_byname(host)
            if import_custom_fields:
                for val in dev['custom_fields']:
                    if val.get('key') in import_custom_fields:
                        rtrn[val.get('key')] = val.get('value')
            if import_values:
                for key in import_values:
                    rtrn[key] = dev.get(key)
        except requests.exceptions.RequestException as exception:
            rtrn['err'] = str(exception)

        # Normalize Role values ENG-45130
        if 'Role' in import_custom_fields and ROLE_NORMALIZE.get(rtrn.get('Role')):
            rtrn['Role'] = ROLE_NORMALIZE.get(rtrn.get('Role'))

        return rtrn
