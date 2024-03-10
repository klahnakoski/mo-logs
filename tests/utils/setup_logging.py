import json
import logging

from mo_logs import logger

logger.start()


class JsonHandler(logging.Handler):
    def emit(self, record):
        print(json.dumps(record.__dict__))
