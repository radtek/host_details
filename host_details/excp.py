"""Copyright Placeholder"""

class HostDetailException(Exception):
    "Generic Exception"
    msg = ""

    def __str__(self):
        return self.msg

class InvalidService(HostDetailException):
    "Generic Exception"
    msg = "Invalid Service"

class InvalidServiceSpec(HostDetailException):
    "Generic Exception"
    msg = "Invalid Service specification"

class InvalidServiceBadInstance(HostDetailException):
    "Generic Exception"
    msg = "Invalid Service, instance unspecified"

class InvalidHostname(HostDetailException):
    "Generic Exception"
    msg = "Invalid Hostname"
