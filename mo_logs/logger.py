import sys
from threading import current_thread

from mo_dots import to_data, unwraplist, Data, is_data, coalesce, listwrap
from mo_future import utcnow, is_text
from mo_imports import delay_import
from mo_kwargs import override

from mo_logs import constants as _constants, exceptions, strings
from mo_logs.exceptions import Except, LogItem, WARNING, get_stacktrace
from mo_logs.log_usingPrint import StructuredLogger_usingPrint
from mo_logs.strings import CR, indent, parse_template
from mo_logs.utils import (
    raise_from_none,
    add_param,
    machine_metadata,
    BackupLogContext,
    _add_thread,
    _known_loggers,
    ExtrasContext,
    MO_LOGS_EXTRAS,
    STACKTRACE,
)

StructuredLogger_usingMulti = delay_import("mo_logs.log_usingMulti.StructuredLogger_usingMulti")
startup_read_settings = delay_import("mo_logs.startup.read_settings")

all_log_callers = {}
cached_templates = {}
trace = False
main_log = StructuredLogger_usingPrint()
logging_multi = None
profiler = None  # simple pypy-friendly profiler
error_mode = False  # prevent error loops
extra = {}
static_template = True


@override("settings")
def start(
    trace=False,
    cprofile=False,
    constants=None,
    logs=None,
    extra=None,
    app_name=None,
    static_template=True,
    settings=None,
):
    """
    RUN ME FIRST TO SETUP THE THREADED LOGGING
    https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/

    :param trace: SHOW MORE DETAILS IN EVERY LOG LINE (default False)
    :param cprofile: True==ENABLE THE C-PROFILER THAT COMES WITH PYTHON (default False)
                     USE THE LONG FORM TO SET THE FILENAME {"enabled": True, "filename": "cprofile.tab"}
    :param constants: UPDATE MODULE CONSTANTS AT STARTUP (PRIMARILY INTENDED TO CHANGE DEBUG STATE)
    :param logs: LIST OF PARAMETERS FOR LOGGER(S)
    :param extra: ADDITIONAL DATA TO BE INCLUDED IN EVERY LOG LINE
    :param app_name: GIVE THIS APP A NAME, AND RETURN A CONTEXT MANAGER
    :param static_template: IF TRUE, THEN ASSUME TEMPLATE IS STATIC AND CACHE PARSED TEMPLATE
    :param settings: ALL THE ABOVE PARAMETERS
    :return:
    """
    if any("mo_logs" in step["file"] and step["method"] == "start" for step in get_stacktrace(1)):
        raise Except(template="Can not call start() from within start().  Are you still importing?")

    log_context = BackupLogContext(settings)
    log_context.__enter__()
    return log_context


@override("settings")
def _start(
    trace=False,
    cprofile=False,
    constants=None,
    logs=None,
    extra=None,
    app_name=None,
    static_template=True,
    settings=None,
):
    stop()
    globals()["settings"] = settings
    globals()["trace"] = trace
    globals()["static_template"] = static_template

    # ENABLE CPROFILE
    if cprofile is False:
        cprofile = settings.cprofile = Data(enabled=False)
    elif cprofile is True:
        cprofile = settings.cprofile = Data(enabled=True, filename="cprofile.tab")
    if is_data(cprofile) and cprofile.enabled:
        from mo_threads import profiles

        profiles.enable_profilers(settings.cprofile.filename)

    if constants:
        _constants.set(constants)

    logs = coalesce(settings.log, logs)
    if logs:
        globals()["logging_multi"] = StructuredLogger_usingMulti()
        for log in listwrap(logs):
            logging_multi.add_log(new_instance(log))

        old_log, globals()["main_log"] = main_log, _add_thread(logging_multi)
        old_log.stop()
    globals()["extra"] = extra or {}
    if isinstance(app_name, str):
        extra["app_name"] = app_name


def stop():
    """
    DECONSTRUCTS ANY LOGGING, AND RETURNS TO DIRECT-TO-stdout LOGGING
    EXECUTING MULTIPLE TIMES IN A ROW IS SAFE, IT HAS NO NET EFFECT, IT STILL LOGS TO stdout
    :return: NOTHING
    """
    old_log, globals()["main_log"] = main_log, StructuredLogger_usingPrint()
    old_log.stop()
    globals()["trace"] = False
    globals()["cprofile"] = False


@override("settings")
def new_instance(log_type=None, settings=None):
    if settings["class"]:
        from mo_logs.log_usingHandler import StructuredLogger_usingHandler

        return StructuredLogger_usingHandler(settings)
    if isinstance(log_type, type):
        return log_type(settings)
    elif isinstance(log_type, str):
        clazz = _known_loggers.get(log_type.lower())
        if clazz:
            return clazz(settings)
        error("Log type of {config|json} is not recognized", config=settings)
    else:
        if hasattr(log_type, "write"):
            return log_type
        return log_type


def set_logger(logger):
    global main_log
    if logging_multi:
        logging_multi.add_log(logger)
    else:
        old_log, main_log = main_log, _add_thread(logger)
        old_log.stop()


def note(
    template, default_params={}, *, stack_depth=0, static_template=None, **more_params,
):
    """
    :param template: *string* human readable string with placeholders for parameters
    :param default_params: *dict* parameters to fill in template
    :param stack_depth:  *int* how many calls you want popped off the stack to report the *true* caller
    :param static_template: *bool* if True, then the template is static, and optimization can be done
    :param more_params: *any more parameters (which will overwrite default_params)
    :return:
    """
    timestamp = utcnow()
    if not isinstance(template, str):
        error("logger.info was expecting a string template")

    _annotate(
        LogItem(
            severity=exceptions.NOTE,
            template=template,
            params=dict(default_params, **more_params),
            timestamp=timestamp,
        ),
        stack_depth + 1,
        globals()['static_template'] if static_template is None else static_template,
    )


def alarm(
    template, default_params={}, *, stack_depth=0, static_template=None, **more_params,
):
    """
    :param template: *string* human readable string with placeholders for parameters
    :param default_params: *dict* parameters to fill in template
    :param stack_depth:  *int* how many calls you want popped off the stack to report the *true* caller
    :param more_params: more parameters (which will overwrite default_params)
    :return:
    """
    timestamp = utcnow()
    template = ("*" * 80) + CR + indent(template, prefix="** ").strip() + CR + ("*" * 80)
    _annotate(
        LogItem(
            severity=exceptions.ALARM,
            template=template,
            params=dict(default_params, **more_params),
            timestamp=timestamp,
        ),
        stack_depth + 1,
        globals()["static_template"] if static_template is None else static_template,
    )


def warning(
    template: str,  # human readable string with placeholders for parameters
    default_params={},  # parameters to fill in template
    cause=None,  # for chaining
    *,
    stack_depth=0,  # how many calls you want popped off the stack to report the *true* caller
    log_severity=WARNING,  # set the logging severity
    exc_info=None,  # used by python logging as the cause
    static_template=None,
    **more_params,  # any more parameters (which will overwrite default_params)
):
    if exc_info is True:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        exc_info = Except.wrap(exc_value)
    if not is_text(template):
        error("logger.warning was expecting a string template")
    if "values" in more_params.keys():
        error("Can not handle a logging parameter by name `values`")

    if isinstance(default_params, BaseException):
        cause = default_params
        default_params = {}

    params = to_data(dict(default_params, **more_params))
    cause = unwraplist([Except.wrap(c, stack_depth=2) for c in listwrap(cause or exc_info)])
    trace = exceptions.get_stacktrace(stack_depth + 1)

    e = Except(severity=log_severity, template=template, params=params, cause=cause, trace=trace,)
    _annotate(
        e, stack_depth + 1, globals()["static_template"] if static_template is None else static_template,
    )


def error(
    template,  # human readable template
    default_params={},  # parameters for template
    *,
    cause=None,  # pausible cause
    stack_depth=0,
    exc_info=None,  # used by python logging as the cause
    **more_params,
):
    """
    raise an exception with a trace for the cause too

    :param template: *string* human readable string with placeholders for parameters
    :param default_params: *dict* parameters to fill in template
    :param cause: *Exception* for chaining
    :param stack_depth:  *int* how many calls you want popped off the stack to report the *true* caller
    :param exc_info: *Exception* alternate to cause (used by other logging libs)
    :param more_params: *any more parameters (which will overwrite default_params)
    :return:
    """
    if not is_text(template):
        # sys.stderr.write(str("logger.error was expecting a string template"))
        error("logger.error was expecting a string template")
    if "values" in more_params.keys():
        error("Can not handle a logging parameter by name `values`")
    if exc_info is True:
        exc_info = Except.wrap(sys.exc_info()[1])

    if isinstance(default_params, BaseException):
        cause = default_params
        default_params = {}

    params = to_data(dict(default_params, **more_params))
    cause = unwraplist([Except.wrap(c, stack_depth=2) for c in listwrap(cause or exc_info)])
    trace = exceptions.get_stacktrace(stack_depth + 1)

    e = Except(severity=exceptions.ERROR, template=template, params=params, cause=cause, trace=trace,)
    raise_from_none(e)


def _annotate(item, stack_depth, static_template):
    """
    :param item:  A LogItem THE TYPE OF MESSAGE
    :param stack_depth: FOR TRACKING WHAT LINE THIS CAME FROM
    :return:
    """
    given_template = item.template
    given_template = strings.limit(given_template, 10_000)
    if static_template:
        param_template = cached_templates.get(given_template)
        if param_template is None:
            param_template = cached_templates[given_template] = add_param(parse_template(given_template))
    else:
        param_template = add_param(parse_template(given_template))

    if isinstance(item, Except):
        param_template = "{severity}: " + param_template + STACKTRACE
        temp = item.__data__()
        temp.trace_text = item.trace_text
        temp.cause_text = item.cause_text
        item = temp
    else:
        item = item.__data__()

    if not param_template.startswith(CR) and CR in param_template:
        param_template = CR + param_template

    thread = current_thread()
    thread_extra = getattr(thread, MO_LOGS_EXTRAS, [{}])[-1]
    if trace:
        item.machine = machine_metadata()
        log_format = item.template = (
            "{machine.name} (pid {machine.pid}) - {timestamp|datetime} -"
            ' {thread.name} - ""{location.file}:{location.line}"" -'
            " ({location.method}) - "
            + param_template
        )
        f = sys._getframe(stack_depth + 1)
        item.location = {
            "line": f.f_lineno,
            "file": f.f_code.co_filename,
            "method": f.f_code.co_name,
        }
        if static_template:
            last_caller_loc = (f.f_code.co_filename, f.f_lineno)
            prev_template = all_log_callers.get(last_caller_loc)
            if prev_template != given_template:
                if prev_template:
                    raise Except(
                        template="Expecting logger call to be static: was {a|quote} now {b|quote}",
                        params={"a": prev_template, "b": given_template},
                        trace=get_stacktrace(stack_depth + 1),
                    )
                all_log_callers[last_caller_loc] = given_template
        item.thread = {"name": thread.name, "id": thread.ident}
    else:
        log_format = param_template
        # log_format = item.template = "{timestamp|datetime} - " + template

    item.params = {**thread_extra, **extra, **item.params}
    main_log.write(log_format, item)


def extras(**kwargs):
    return ExtrasContext(kwargs)
