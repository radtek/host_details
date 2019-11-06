#!/usr/bin/env python
"""
Used to regenerate the HostDetails fixtures to check the details of hosts specifically for unit testing
"""
import yaml

from host_details.hostdetails import HostDetails
from tests.hostnamemap import HOSTNAMEMAP
from host_details.compat import pkg_resources


def main():
    for host in HOSTNAMEMAP:
        print("processing host: {}".format(host))
        hdetails = HostDetails(host)
        hdetails.all_details()
        path = pkg_resources.resouce_filename("tests", "fixtures/hostdetails/{}.yaml".format(host))
        with open(path, "w") as hostfile:
            yaml.dump(hdetails.details, hostfile)


if __name__ == "__main__":
    main()
