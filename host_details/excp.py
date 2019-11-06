"""Copyright Placeholder"""

class HostDetailException(Exception):
    msg = ""

    def __str__(self):
        return self.msg

class InvalidService(HostDetailException):
    msg = "Invalid Service"

class InvalidServiceSpec(HostDetailException):
    msg = "Invalid Service specification"

class InvalidServiceBadInstance(HostDetailException):
    msg = "Invalid Service, instance unspecified"

class InvalidHostname(HostDetailException):
    msg = "Invalid Hostname"
