"""Offline package-security report entrypoint."""
from opsfeast.package_security.report import execute as generate_report

VERSION = '0.3.1'


def execute(*, context, timeout):
    return generate_report(context=context, timeout=timeout)
