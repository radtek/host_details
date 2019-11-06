import logging
import yaml
import mock
from parameterized import parameterized
from .base import BaseTestCase
from tests.hostnamemap import HOSTNAMEMAP
from host_details.hostdetails import HostDetails
from host_details.excp import HostDetailException

import pkg_resources

LOGGER = logging.getLogger(__name__)

from types import SimpleNamespace

class TestConfig(SimpleNamespace):
    server = "localhost"
    user = "user"
    password = "password"

class HostDetailsTests(BaseTestCase):




    @parameterized.expand(HOSTNAMEMAP)
    def test_hostdetails(self, hostname):

        with mock.patch('host_details.hostdetails.load_config_files') as cfg_mock:
            # provide fake config to the D42 client.
            cfg_mock.return_value = TestConfig()
            with mock.patch('host_details.d42_connector.Devices') as d42_devices_mock:
                fixture = self._load_fixture(hostname)

                # setup D42 response based on whats known from the fixture file
                d42_devices_mock.return_value.get_device_byname.return_value = \
                    {
                        "custom_fields": [
                            {
                                "key": "Role",
                                "notes": "",
                                "value": fixture['function']
                            }
                        ]
                    }

                hostdetails = HostDetails(hostname)
                hostdetails.all_details()
                LOGGER.debug("details: %s", hostdetails.details)
                LOGGER.debug("fixture: %s", fixture)
                self.assertEqual(fixture, hostdetails.details)

    def _load_fixture(self, hostname):
        fixes_dir = pkg_resources.resource_filename('tests.fixtures', 'hostdetails')
        with open("{}/{}.yaml".format(fixes_dir, hostname), "r") as fixraw:
            fixture = yaml.load(fixraw)
        return fixture

    def test_autogroup_regex_match_nothing(self):
        server = "nothing.skytap.com"
        with self.assertRaises(HostDetailException):
            _ = HostDetails(server)

    def test_maprules_prod(self):
        self.assertListEqual(['mysql', 'prod', 'sharedservices', 'tuk1'], HostDetails("tuk1mysql1.prod.skytap.com").map_zabbix_rules())

    def test_maprules_integ(self):
        self.assertListEqual(['integ', 'lon5', 'packages'], HostDetails("lon5packages1.integ.skytap.com").map_zabbix_rules())

    def test_maprules_test(self):
        self.assertListEqual(['logger', 'slg6', 'test'], HostDetails("slg6logger1.test.skytap.com").map_zabbix_rules())

    def test_maprules_qa(self):
        self.assertListEqual(['daa8', 'qa', 'sharedservices', 'zabbix'], HostDetails("daa8zabbix1.qa.skytap.com").map_zabbix_rules())

    def test_maprules_corp(self):
        self.assertListEqual(['corp', 'corp-it', 'tuk9'], HostDetails("tuk9foo1.corp.skytap.com").map_zabbix_rules())

    def test_maprules_corp(self):
        self.assertListEqual(['ash1', 'f5ltm', 'network', 'prod'], HostDetails("ash1dlbr1.ilo.skytap.com").map_zabbix_rules())

    def test_getroletemplet(self):
        data = {
            'foreman': {'operatingsystem-name': 'legacy_Ubuntu 12.04 LTS',
                        'architecture-name': 'x86_64', 'partition-table-name': 'zzz_Skytap Ubuntu 12.04',
                        'medium-name': 'zzz_unmanaged_Skytap 12.04 Repository',
                        'parameters': [],
                        'compute-attributes':
                            {'cpus': 4,
                             'memory_mb': 32768,
                             'guest_id': 'ubuntu64Guest'
                             }
                        },
            'skytap': {'highland_env': 'prod', 'highland_nodetype': 'kube_minion', 'role': 'knode'},
            'zabbix': {
                'link_templates': ['Template_Server_Linux_Ubuntu'], 'host_groups': ['Production', 'services.yaml - kubernetes'], 'proxy_name': 0
            }
        }
        self.assertDictEqual(data, HostDetails("tuk1r1knode1.mgt.prod.skytap.com").getroletemplate())

