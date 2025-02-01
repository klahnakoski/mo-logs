# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from mo_logs import constants as _constants, exceptions, strings
from mo_logs import logger
from mo_logs.exceptions import *
from mo_logs.log_usingPrint import StructuredLogger_usingPrint
from mo_logs.strings import CR, indent, parse_template
from mo_logs.utils import *


logger.warn = logger.warning
logger.info = logger.note
logger.alert = logger.alarm
Log = logger
LoggingContext = logger.start
