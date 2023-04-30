# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import base64
from decimal import Decimal

from mo_dots import to_data
from mo_future import number_types, is_text
from mo_json import datetime2unix, value2json
from mo_kwargs import override

from mo_logs import logger, strings
from mo_logs.exceptions import ALARM, ERROR, NOTE, WARNING
from mo_logs.log_usingNothing import StructuredLogger

LOG_STRING_LENGTH = 2000


class StructuredLogger_usingMozLog(StructuredLogger):
    """
    WRITE TO MozLog STANDARD FORMAT
    https://wiki.mozilla.org/Firefox/Services/Logging
    """

    @override
    def __init__(self, stream, app_name):
        """
        :param stream: MozLog IS A JSON FORMAT, WHICH IS BYTES
        :param app_name: MozLog WOULD LIKE TO KNOW WHAT APP IS MAKING THESE LOGS
        """
        self.stream = stream
        self.app_name = app_name
        if not app_name:
            logger.error("mozlog expects an `app_name` in the config")
        if not logger.trace:
            logger.error("mozlog expects trace=True so it gets the information it requires")

    def write(self, template, params):
        output = {
            "Timestamp": (Decimal(datetime2unix(params.timestamp)) * Decimal(1e9)).to_integral_exact(),  # NANOSECONDS
            "Type": params.template,
            "Logger": params.machine.name,
            "Hostname": self.app_name,
            "EnvVersion": "2.0",
            "Severity": severity_map.get(params.severity, 3),  # https://en.wikipedia.org/wiki/Syslog#Severity_levels
            "Pid": params.machine.pid,
            "Fields": {k: strings.limit(_json_to_string(v), LOG_STRING_LENGTH) for k, v in to_data(params).leaves()},
        }
        self.stream.write(value2json(output).encode("utf8"))
        self.stream.write(b"\n")


def _json_to_string(value) -> str:
    """
    :param value: SOME STRUCTURE
    :return: str
    """
    if isinstance(value, number_types):
        return str(value)
    elif is_text(value):
        return value
    elif isinstance(value, bytes):
        return base64.b64encode(value).decode("latin1")
    else:
        return value2json(value)


# https://en.wikipedia.org/wiki/Syslog#Severity_levels
severity_map = {
    ERROR: 3,  # Error
    WARNING: 4,  # Warning
    ALARM: 5,  # Notice
    NOTE: 6,  # Informational
}


def datatime2decimal(value):
    return
