"""
Hostname Details breakdown (all the host information)
"""

import re
import logging
from collections import OrderedDict
import yaml

from host_details.compat import pkg_resources

from host_details.excp import InvalidHostname, InvalidService, InvalidServiceSpec, InvalidServiceBadInstance

from host_details.d42_connector import D42Connector

LOGGER = logging.getLogger(__name__)


class HostDetails(object):
    """
    All the information/services based from Hostname
    """
    def __init__(self, hostname):
        """
        Takes a hostname, and breaks it down into the environment (tuk, daa), if it is production/qa/test, the server function.
        :param hostname: Hostname to get the details from.
        """
        self.details = {
            "platform": None,
            "subplatform": None,
            "shortname": None,
            "security": {
                "role.service_owner": "",
                "role.authorized_operator": [],
                "role.authorized": []
            },
            "owner": "team-unclassified",
            "hostname": None,
            "env": None,
            "datacenter": None,
            "region": None,
            "services": {}
        }

        self.hostname = hostname
        self.details["hostname"] = hostname
        LOGGER.debug("Hostname: %s", hostname)
        self.env_map = {
            1: "prod",
            5: "integ",
            6: "test",
            8: "qa",
            9: "corp"
        }

        self.team_ownership_regexes = {
            "team-dataplane-storage": "^ss$|^vsn$|^cephexit$|^cephcontrol$|^sntest$|^cephui$|^ssvip$|^sn$|^cephosd$|^cephmon$|^bs$|^bs5sp",
            "team-dataplane-compute": "^vshs$|^vcsa$|^vcusage$|^java$|^hn$|^phn$",
            "team-dataplane-networking": "^nsvc$|^sambahn$|^sambasvc$|^nsxmgr$|^nsxsvc$|^nsxctrl$|^nsxold.*|^nsxgw$|^nhn$",
            "team-frontend": "^npmregistry$",
            "team-infosec": "^ossec$|^nessus$|^secscanconsole$",
            "team-infra-corpit":
                "^fisheye$|^confluence$|^jira$|^okta$|^oktaprov$|^servicedesk$|^polycom$|^ups$|^fs$|^password$|^informatica$|^mitel$|^engrmetrics$|^usrmgmt.*|"
                "^printdca$",
            "team-infra-networking":
                "^kentik$|^ise$|^sr$|^er$|^dltr$|^vr$|^f5lb$|^apm$|^kprobe$|^as$|^cs$|^ar$|^nms$|^acs$|^ds$|^cisco$|^fw$|^wlc$|^dlcr$|^dlbr$",
            "team-infra-systems":
                "^zabbix.*|^hmc$|^hpsim$|^hpsum$|^threeparsr$|^ntop$|^radius$|^ssmc$|^pdu$|^obs.*|^fc$|c[0-9]*oa|^rstricklin.*$|^oob.*|^c[0-9]*b[0-9]*|"
                "^skyvreports$|^infrapypi$",
            "team-middle-tier-core": "^charon|^cm$|^gb$|^qi$|^cmvip$|^nsvip$|^vmhmvip$",
            "team-middle-tier-web-backend": "^guac$|^ftp$|^webnfs$|^mux.*|^memcache$|^wfe$|^trun$|^smartclient$|^cron$|^elastic(data|tribe|master)wfe$",
            "team-reliability": "^netgauge.*$",
            "team-tools-kubernetes": "^knode.*$|^kube.*|^etcd$|^kmaster$|^calico.*|^control$",
            "team-tools-mysql": "^mysql$|^vimadb$|^bmetricsdb$",
            "team-tools-observability":
                "^mon$|^elastic(data|tribe|master)(?!wfe)$|^esvip$|^brokervip$|^influx.*$|^metric$|^bmetrics$|^bi$|^nlogsearch$|^nlog.*|^logger$|^gangliavip$|"
                "^ingestervip$|^mq$",
            "team-tools-runtime":
                "^awx$|^backups$|^cmdb.*$|^dhcp$|^dockerreg$|^foreman$|^gerrit$|^grits$|^hostinfo$|^jenkins.*$|^ldap.*$|^legacyrepo$|.*jump.*|^log$|^nas$|"
                "^skytapca.*|^nsmanage$|.*puppet.*|^oss$|^packages$|^repo$|^aptrepo$|^legacyrepo$|^smtp$|^tftp$|^zfsbackup$|^archive$|^ans$|^ns$|^ntp$|^lb.*|"
                "^sdouglas.*$|^loga$|^stagingwp.*|^corpw.*|^vault$|^consulvault$",
            "team-tools-virtualinfrastructure": "^sshost$|^mn$|^nsxhost$|^nsxctrlhost$|^nsxsvchost$|^vsnhn$|^esxi$|^dbesxi$|^eris$|^ris$|^dmyers.*$",
        }

        self.team_owner_overrides = {
            "hostname": OrderedDict([("jenkins.mgt.test.skytap.com", "team-tools-build")]),
            "shortname": OrderedDict((key, "team-tools-virtualinfrastructure") for key in ["tuk8vcsa1", "tuk5vcsa1", "tuk1vcsa1", "sea9vcsa1"]),
            "function": OrderedDict([
                ("zabbixmysql", "team-infra-systems"),
                ("mysql", "team-tools-mysql")
            ])
        }

        # tools team override
        self.tas_override = [
            "team-tools-runtime",
            "team-tools-kubernetes",
            "team-tools-build",
            "team-tools-mysql",
            "team-tools-observability",
            "team-tools-virtualinfrastructure"
        ]

        # Mapping for the which service see method for details on variables
        self.service_discovery = {
            "logger": {"instance": "2", "resource": True, "management": True, "override": {"corp": None}},
            "cmdb": {"override": {"qa": "cmdb.prod.skytap.com", "prod": "cmdb.prod.skytap.com"}},
            "ntp": {"instance": ["1", "2"], "shared": True},
            "zabbix": {"override": {"qa": "zabbix.qa.skytap.com", "prod": "zabbix.prod.skytap.com", "corp": "zabbix.prod.skytap.com"}},
            "zabbixproxy": {"instance": "", "shared": True},
            "zabbixjobs": {"instance": "1", "shared": True},
            "foreman": {"override": {"qa": "foreman.qa.skytap.com", "prod": "foreman.prod.skytap.com"}},
            "nsmanage": {"override": {"qa": "tuk8nsmanage1.qa.skytap.com", "prod": "tuk1nsmanage2.prod.skytap.com", "corp": "sea9nsmanage1.corp.skytap.com"}},
            "opspuppetca": {
                "override": {"qa": "tuk8opspuppetca3.qa.skytap.com", "prod": "tuk1opspuppetca1.prod.skytap.com", "corp": "tuk8opspuppetca3.qa.skytap.com"}
            },
            "ldap": {"instance": ["1", "2"], "shared": True},
            "mnvcsa": {
                "override": {"qa": "tuk8vcsa1.qa.skytap.com", "prod": "tuk1vcsa1.prod.skytap.com", "corp": "sea9vcsa1.corp.skytap.com",
                             "integ": "tuk5vcsa1.mgt.integ.skytap.com"}
            },
            "vaultvip": {"instance": "1", "shared":True, "override": {"vault": True}}
        }

        component_regexes = [
            # Stack
            re.compile(r"^(?P<datacenterregion>(?P<datacenter>[a-z]{3})(?P<env>\d)(?P<region>[r|m|x]\d))(?P<function>[a-z|0-9]+[a-z])(?P<instance>\d+)"),
            # Stack regionless
            re.compile(r"^(?P<datacenter>[a-z]{3})(?P<env>\d)(?P<function>[a-z|0-9]+[a-z])(?P<instance>\d+)"),
            # Infra
            re.compile(r"^(?P<datacenterfunction>(?P<datacenter>[a-z]{3}\d)(?P<function>[0-9|a-z|-]+[a-z]))(?P<instance>\d+)"),
            # Dev
            re.compile(r"^(?P<datacenter>[a-z]{3}\d)(?P<function>[a-z|0-9|-]+[a-z])(?P<instance>\d+)"),
            # Dev no location
            re.compile(r"^(?P<function>[a-z|0-9|-]+[a-z])(?P<instance>\d+)")
        ]

        host_component = hostname.split(".")

        # This just makes sure there are at least 4 items from a host name split which should be the minimum for any internal skytap hostname
        if len(host_component) < 4:
            raise InvalidHostname()

        self.details["shortname"] = host_component[0]
        if host_component[-3] in ['prod', 'qa', 'test', 'corp', 'ilo', 'integ']:
            self.details["platform"] = host_component[-3]

        if host_component[-4] in ['mgt', 'test', 'dev']:
            self.details["subplatform"] = host_component[-4]

        for regex in component_regexes:
            result = regex.search(host_component[0])
            if result:
                self.details.update(result.groupdict())
                break

        if "function" not in self.details:
            self.details["function"] = host_component[0]

    def all_details(self):
        """
        Populates details with everything we are generating
        """
        self.which_owner()
        self.which_security()
        self.zabbix_details()

        for service, value in self.service_discovery.items():
            self.details["services"][service] = self.which_service(service, **value)

    def hostsplit_service(self):
        """
        Fills out details specific for hostsplit additional detail fields for hostname
        """
        self.which_owner()
        self.which_security()

        for service, value in self.service_discovery.items():
            self.details["services"][service] = self.which_service(service, **value)

    def which_owner(self):
        """
        Determine host Group ownership
        :return:
        """
        LOGGER.debug(self.details)
        for override_function, override_map in self.team_owner_overrides.items():
            for override_key, override_team in override_map.items():
                if override_key in self.details[override_function]:  # pylint: disable=unsupported-membership-test
                    self.details["owner"] = override_team
                    break

        # for chassis and blades in d42, use their role to determine ownership
        if re.match('^c[0-9]*b[0-9]*', self.details['function']) is not None:
            d42_connector = D42Connector()
            self.details['d42'] = d42_connector.get_by_hostname(self.hostname)
            if self.details['d42'].get('Role'):
                self.details['function'] = self.details['d42']['Role']
                if self.details['d42']['Role'] in ['hn', 'hostingnode']:
                    self.details['owner'] = 'team-dataplane-compute'
                elif self.details['d42']['Role'] in ['nhn', 'networkhostingnode']:
                    self.details['owner'] = 'team-dataplane-networking'
                elif self.details['d42']['Role'] in ['dbmanagementnode', 'managementnode',
                                                     'nsxmanagementnode', 'rishost',
                                                     'sshost', 'vsnhn', 'mn']:
                    self.details['owner'] = 'team-tools-virtualinfrastructure'
                else:
                    self.details['owner'] = 'team-infra-systems'

        if self.details["owner"] == "team-unclassified":
            for owner, teamregex in self.team_ownership_regexes.items():
                if re.search(teamregex, self.details["function"]):
                    self.details["owner"] = owner
                    break

    def which_security(self):
        """
        Determine which security groups apply to a host
        :return:
        """
        # Tools and services
        if self.details["owner"] in self.tas_override:
            # setup owner and oncall privs
            if self.details["platform"] == "prod":
                self.details["security"]["role.service_owner"] = "%s-prod" % self.details["owner"]
                self.details["security"]["role.authorized_operator"].append("team-toolsandservices-prod")
            else:
                self.details["security"]["role.service_owner"] = self.details["owner"]
                self.details["security"]["role.authorized_operator"].append("team-toolsandservices")

            # by function
            if self.details["function"] in ["linjump", "loga", "log"]:
                if self.details["platform"] == "prod":
                    self.details["security"]["role.authorized"].append('prod')
                # If the host is not in prod, it will inherit engineering acess
                # from below.

            elif self.details["function"] == "repo":
                self.details["security"]["role.authorized"].append('engineering')

            # Engineering should be able to log into our hosts that aren't in prod
            if self.details["platform"] != "prod":
                self.details["security"]["role.authorized"].append('engineering')

        # Infosec
        elif self.details["owner"] == "team-infosec":
            if self.details["platform"] == "prod":
                self.details["security"]["role.service_owner"] = "%s-prod" % self.details["owner"]
            else:
                self.details["security"]["role.service_owner"] = self.details["owner"]

        # Other hosts should get the legacy access policy
        else:
            if self.details["platform"] == "prod":
                self.details["security"]["role.service_owner"] = 'prod'
            else:
                self.details["security"]["role.service_owner"] = 'ops'
                self.details["security"]["role.authorized"].append('engineering')

    def which_service(self, service, instance=None, resource=False, management=False, shared=False, override=None):  # pylint:disable=too-many-arguments,too-many-return-statements
        """
        Identify Which service to use based on hostname information and sets in details
        :param service: Service to be determined
        :param: instance: which instance/s (list or number) are being used like: 2 would result in tuk1m1logger2, or [1,2] for like ntp1/2
        :param: resource: if it is in a resource region like r1
        :param: management: if it is in a management region like m1
        :param: shared: if it is a shared service like ntp/ldap
        :param: override: Just set the specific intg/qa/corp/prod instance for things like cmdb
        :return: the full domain name of the target service
        """
        if service not in self.service_discovery:
            raise InvalidService()
        if resource and management and shared:
            raise InvalidServiceSpec()

        if override:
            if "vault" in override:
                if self.details["datacenter"] == "jng":
                    return "jng4vault1.skytap-dev.net"
                elif self.details["env"] == "5":
                    return "tuk5vaultvip1.qa.skytap.com"
                elif self.details["env"] in ["6", "8"]:
                    return "{}6vaultvip{}.qa.skytap.com".format(self.details["datacenter"], instance)
                elif self.details["env"] == "9" and self.details["datacenter"] == "sea":
                    return "tuk6vaultvip1.qa.skytap.com"
            elif "integ" in override and (self.details["env"] == "5" or self.details["platform"] == "integ"):
                return override["integ"]
            elif "corp" in override and self.details["env"] == "9":
                return override["corp"]
            elif "qa" in override and (self.details["env"] in ["5", "6", "7", "8"] or self.details["platform"] in ["qa", "integ", "test"]):
                return override["qa"]
            elif self.details["env"] == "9" and self.details["datacenter"] == "sea":
                return override["qa"]
            elif "prod" in override and self.details["env"] == "9" and self.details["datacenter"] == "tuk":
                return override["prod"]
            elif "prod" in override and (self.details["env"] == "1" or self.details["platform"] == "prod"):
                return override["prod"]

        service_details = self.details.copy()
        service_details["details"] = self.service_discovery[service]

        if service_details["datacenter"] is not None and "ash" in service_details["datacenter"]:
            service_details["datacenter"] = "wdb"
        if service_details["datacenter"] is not None and "dls" in service_details["datacenter"]:
            service_details["datacenter"] = "dal"

        if shared and service_details["env"] in ["5", "6", "7", "8"]:
            service_details["env"] = "8"
            service_details["subplatform"] = ""
            service_details["region"] = ""
            service_details["platform"] = "qa"
        elif shared and service_details["env"] == "9" and service_details["datacenter"] == "tuk":
            service_details["env"] = "1"
            service_details["platform"] = "prod"
            service_details["region"] = ""
            service_details["subplatform"] = ""
        elif shared:
            service_details["subplatform"] = ""
            service_details["region"] = ""
        elif not shared and service_details["env"] == "8":
            service_details["env"] = "6"
            service_details["platform"] = "test"

        if not shared and service_details["subplatform"] is None:
            service_details["subplatform"] = "mgt"

        if service_details["subplatform"]:
            service_details["subplatform"] = "." + service_details["subplatform"]
        else:
            service_details["subplatform"] = ""

        if management and resource:
            # corp is always the special case here
            if service_details["env"] == "9" and service_details["datacenter"] == "tuk":
                service_details["env"] = "1"
                service_details["region"] = "m1"
                service_details["platform"] = "prod"
            elif service_details["env"] == "9" and service_details["datacenter"] == "sea":
                service_details["datacenter"] = "tuk"
                service_details["env"] = "6"
                service_details["region"] = "m1"
                service_details["platform"] = "qa"

            # Service exists in management and resource region
            if service_details["region"] is None:
                if self.details["datacenter"] == "tuk":
                    service_details["region"] = "m1"
                elif self.details["datacenter"]:
                    service_details["region"] = "r1"
                else:
                    service_details["region"] = ""
            # in case of x1
            if service_details["region"] == "x1":
                service_details["region"] = "r1"

        if service_details["datacenter"] is None:
            service_details["datacenter"] = ""
        if service_details["env"] is None:
            service_details["env"] = ""

        if instance is not None:
            if isinstance(instance, list):
                return ["{datacenter}{env}{region}{service}{service_instance}{subplatform}.{platform}.skytap.com".format(
                    service=service, service_instance=node, **service_details
                ) for node in instance]
            return "{datacenter}{env}{region}{service}{service_instance}{subplatform}.{platform}.skytap.com".format(
                service=service, service_instance=instance, **service_details
            )

        raise InvalidServiceBadInstance()


    def zabbix_details(self):
        """
        Map Zabbix rules/roles/groups from hostname and function.
        """
        if self.details["owner"] == "team-unclassified":
            self.which_owner()

        self.details["zabbix"] = {"groups": []}

        if self.details["datacenter"] and self.details["env"]:
            self.details["zabbix"]["groups"].append(self.details["datacenter"] + self.details['env'])
        elif self.details["datacenter"]:
            self.details["zabbix"]["groups"].append(self.details["datacenter"])

        self.details["zabbix"]["groups"].append(self.details["owner"])

        if "tools" in self.details["owner"]:
            self.details["zabbix"]["groups"].append("team-tools")

        if self.details["function"] == "vsnhn":
            self.details["zabbix"]["groups"].append("team-storage")


    def map_zabbix_rules(self):
        """
        Map zabbix rules to hostname, based on location and role
        :return: sorted set of zabbix location rules
        """
        # Mysql and mysqlvip are special function cases
        function_override = [
            'packages',
            'zabbix',
            'logger'
        ]
        result = set()

        result.add(self.details["datacenter"] + self.details['env'])
        result.add(self.env_map[int(self.details['env'])])

        if "mysql" in self.details["function"] and "vip" in self.details["function"]:
            result.add("mysqlvip")
        elif "mysql" in self.details["function"]:
            result.add("mysql")

        if "subplatform" in self.details and self.details["subplatform"] != "mgt" and any(key == self.details["platform"] for key in ["prod", "qa"]):
            result.add("sharedservices")

        # Hosting Node
        hnsearch = re.compile(".*c.*b")
        if "hn" in self.details["function"] or hnsearch.search(self.details["function"]):
            result.add("hn")

        # Network
        network_function_name = [
            re.compile(x) for x in [".*as$", ".*cs$", ".*lb$", ".*vr$", ".*sr$", "^er$", ".*dltr$", ".*dlbr$", ".*ar$", ".*acs$", ".*ds$", ".*nsx.*"]
        ]
        if any(network.search(self.details["function"]) for network in network_function_name):
            result.add("network")

        if "lb" in self.details['function'] and "network" in result and self.details["platform"] in ["ilo", "corp", "prod"]:
            result.add("f5ltm")

        # Corp IT
        if self.details['platform'] == "corp":
            result.add("corp-it")

        for item in function_override:
            if item in self.details["function"]:
                result.add(item)

        roletemplate = self.getroletemplate()
        if roletemplate:
            result |= set(roletemplate['zabbix']['host_groups'])
        return sorted(result)

    def getroletemplate(self):
        """
        Zabbix role template based on role.yaml file like mysql
        :param role: the server role, like mysql
        :return: role template dictionary
        """

        from host_details import static

        rolefile_path = pkg_resources.resouce_filename(static, "roles/{}.yaml".format(self.details["function"]))
        LOGGER.debug("Opening rolefile: %s", rolefile_path)
        try:
            with open(rolefile_path, "r") as rolefile:
                roletemplate = yaml.load(rolefile)
        except IOError as error:
            if error.errno == 2:
                # File not found
                return None
            raise error

        return roletemplate
