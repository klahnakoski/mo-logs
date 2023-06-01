import logging

from mo_dots import Data

from mo_logs import machine_metadata

from mo_logs.exceptions import ERROR, FATAL, ALARM, INFO, WARNING


class LoggingHandler(logging.Handler):

    def handle(self, record: logging.LogRecord) -> bool:
        if record.levelno >= self.level:
            self.emit(record)
        return True

    def emit(self, record: logging.LogRecord) -> None:
        item = Data()
        item.machine = machine_metadata()
        item.template = item.template = (
                "{machine.name} (pid {machine.pid}) - {timestamp|datetime} -"
                ' {thread.name} - "{location.file}:{location.line}" -'
                " ({location.method}) - "
                + record.msg
        )
        item.timestamp=record.created
        item.location = {
            "line": record.lineno,
            "file": record.filename,
            "method": record.funcName,
        }
        item.thread = {"name": record.threadName, "id": record.thread}
        item.process = {"name": record.processName, "id": record.process}
        item.severity = level_to_severity[record.levelno]
        item.params = record.args
        item.logger.name = record.name
        item.logger.level = record.levelno


        exc_info: _SysExcInfoType | None
        exc_text: str | None
        stack_info: str | None

        asctime: str
        created: float
        msecs: float
        # Only created when logging.Formatter.format is called. See #6132.
        relativeCreated: float


level_to_severity = {
    logging.CRITICAL: FATAL,
    logging.ERROR: ERROR,
    logging.WARNING: WARNING,
    logging.INFO: ALARM,
    logging.INFO: INFO,
}

