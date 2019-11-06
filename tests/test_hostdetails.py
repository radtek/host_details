import logging
import yaml
from parameterized import parameterized
from host_details.tests import BaseTestCase
from tests.hostnamemap import HOSTNAMEMAP
from host_details.hostdetails import HostDetails
from werkzeug.exceptions import BadRequest

LOGGER = logging.getLogger(__name__)

class HostDetailsTests(BaseTestCase):

    @parameterized.expand(HOSTNAMEMAP)
    def test_hostdetails(self, hostname):
        with open("fixtures/hostdetails/{}.yaml".format(hostname), "r") as fixraw:
            fixture = yaml.load(fixraw)
        hostdetails = HostDetails(hostname)
        hostdetails.all_details()
        LOGGER.debug("details: %s", hostdetails.details)
        LOGGER.debug("fixture: %s", fixture)
        self.assertEqual(fixture, hostdetails.details)

    def test_autogroup_regex_match_nothing(self):
        server = "nothing.skytap.com"
        with self.assertRaises(BadRequest):
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

