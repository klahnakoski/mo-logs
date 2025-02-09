# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import json as _json
import math
import os
import re
import string
from datetime import date, datetime as builtin_datetime, timedelta
from typing import Tuple

from mo_dots import Data, coalesce, is_data, is_list, to_data, is_sequence, is_many, is_null, is_missing
from mo_future import get_function_name, is_text, round as _round, transpose, xrange, zip_longest, binary_type
from mo_imports import delay_import

builtin_hex = hex
_str, str = str, None

logger = delay_import("mo_logs.logger")
json_encoder = delay_import("mo_json.encoder.json_encoder")
Except = delay_import("mo_logs.exceptions.Except")
Duration = delay_import("mo_times.durations.Duration")
value2url_param = delay_import("mo_files.url.value2url_param")
Date = delay_import("mo_times.dates.Date")


FORMATTERS = {}
CR = "\n"


def formatter(func):
    """
    register formatters
    """
    FORMATTERS[get_function_name(func)] = func
    return func


@formatter
def datetime(value):
    """
    Convert from unix timestamp to GMT string
    :param value:  unix timestamp
    :return: string with GMT time
    """
    output = Date(value).format("%Y-%m-%d %H:%M:%S.%f")
    if output.endswith(".000000"):
        return output[:-7]
    elif output.endswith("000"):
        return output[:-3]
    else:
        return output


@formatter
def str(value):
    """
    Convert to a unicode string
    :param value: any value
    :return: unicode
    """
    if is_null(value):
        return ""
    return _str(value)


@formatter
def unicode(value):
    return str(value)


@formatter
def unix(value):
    """
    Convert a date, or datetime to unix timestamp
    :param value:
    :return:
    """
    try:
        return _str(int(Date(value)))
    except Exception:
        return _str(value)


@formatter
def url(value):
    """
    convert FROM dict OR string TO URL PARAMETERS
    """
    return value2url_param(value)


@formatter
def html(value):
    """
    convert FROM unicode TO HTML OF THE SAME
    """
    import html

    return html.escape(value)


@formatter
def upper(value):
    """
    convert to uppercase
    :param value:
    :return:
    """
    return value.upper()


@formatter
def capitalize(value: _str):
    """
    convert first character of word to uppercase
    :param value:
    :return:
    """
    return value.capitalize()


@formatter
def lower(value):
    """
    convert to lowercase
    :param value:
    :return:
    """
    return value.lower()


@formatter
def newline(value):
    """
    ADD NEWLINE, IF SOMETHING
    """
    return CR + to_string(value).lstrip(CR)


@formatter
def replace(value, find, replace):
    """
    :param value: focal value
    :param find: string to find
    :param replace: string to replace with
    :return:
    """
    return value.replace(find, replace)


@formatter
def json(value, pretty=True):
    """
    convert value to JSON
    :param value:
    :param pretty:
    :return:
    """
    return json_encoder(value, pretty=pretty)


@formatter
def tab(value):
    """
    convert single value to tab-delimited form, including a header
    :param value:
    :return:
    """
    if is_data(value):
        h, d = transpose(*to_data(value).leaves())
        return "\t".join(map(value2json, h)) + CR + "\t".join(map(value2json, d))
    else:
        _str(value)


@formatter
def indent(value, prefix="\t", indent=None):
    """
    indent given string, using prefix * indent as prefix for each line
    :param value:
    :param prefix:
    :param indent:
    :return:
    """
    if indent != None:
        prefix = prefix * indent

    value = to_string(value)
    try:
        content = value.rstrip()
        suffix = value[len(content) :]
        lines = content.splitlines()
        return prefix + (CR + prefix).join(lines) + suffix
    except Exception as e:
        raise Exception(f"Problem with indent of value ({e.message})\n{to_string(value)}")


@formatter
def outdent(value):
    """
    remove common whitespace prefix from lines
    :param value:
    :return:
    """
    try:
        num = 100
        lines = to_string(value).splitlines()
        for l in lines:
            trim = len(l.lstrip())
            if trim > 0:
                num = min(num, len(l) - len(l.lstrip()))
        return CR.join([l[num:] for l in lines])
    except Exception as e:
        logger.error("can not outdent value", e)


@formatter
def round(value, decimal=0, digits=None, places=None):
    """
    :param value:  THE VALUE TO ROUND
    :param decimal: NUMBER OF DECIMAL PLACES TO ROUND (NEGATIVE IS LEFT-OF-DECIMAL)
    :param digits: ROUND TO SIGNIFICANT NUMBER OF digits
    :param places: SAME AS digits
    :return:
    """
    value = float(value)
    if value == 0.0:
        return "0"

    digits = coalesce(digits, places)
    if digits != None:
        left_of_decimal = int(math.ceil(math.log10(abs(value))))
        decimal = digits - left_of_decimal

    right_of_decimal = max(decimal, 0)
    format = f"{{:.{right_of_decimal}f}}"
    return format.format(_round(value, decimal))


@formatter
def percent(value, decimal=None, digits=None, places=None):
    """
    display value as a percent (1 = 100%)
    :param value:
    :param decimal:
    :param digits:
    :param places:
    :return:
    """
    if is_null(value):
        return ""

    value = float(value)
    if value == 0.0:
        return "0%"

    digits = coalesce(digits, places)
    if digits != None:
        left_of_decimal = int(math.ceil(math.log10(abs(value)))) + 2
        decimal = digits - left_of_decimal

    decimal = coalesce(decimal, 0)
    right_of_decimal = max(decimal, 0)
    format = f"{{:.{right_of_decimal}%}}"
    return format.format(_round(value, decimal + 2))


@formatter
def find(value, find, start=0):
    """
    Return index of `find` in `value` beginning at `start`
    :param value:
    :param find:
    :param start:
    :return: If NOT found, return the length of `value` string
    """
    l = len(value)
    if is_list(find):
        m = l
        for f in find:
            i = value.find(f, start)
            if i == -1:
                continue
            m = min(m, i)
        return m
    else:
        i = value.find(find, start)
        if i == -1:
            return l
        return i


@formatter
def strip(value):
    return _str(value).strip()


@formatter
def trim(value):
    return _str(value).strip()


@formatter
def between(value, prefix=None, suffix=None, start=0):
    """
    Return first substring between `prefix` and `suffix`
    :param value:
    :param prefix: if None then return the prefix that ends with `suffix`
    :param suffix: if None then return the suffix that begins with `prefix`
    :param start: where to start the search
    :return:
    """
    value = to_string(value)
    if is_null(prefix):
        e = value.find(suffix, start)
        if e == -1:
            return None
        else:
            return value[:e]

    s = value.find(prefix, start)
    if s == -1:
        return None
    s += len(prefix)

    if suffix is None:
        e = len(value)
    else:
        e = value.find(suffix, s)
        if e == -1:
            return None

    s = value.rfind(prefix, start, e) + len(prefix)  # WE KNOW THIS EXISTS, BUT THERE MAY BE A RIGHT-MORE ONE

    return value[s:e]


@formatter
def right(value, length):
    """
    Return the `len` last characters of a string
    :param value:
    :param len:
    :return:
    """
    if length <= 0:
        return ""
    return value[-length:]


@formatter
def right_align(value, length):
    """
    :param value: string to right align
    :param length: the number of characters to output (spaces added to left)
    :return:
    """
    if length <= 0:
        return ""

    value = _str(value)

    if len(value) < length:
        return (" " * (length - len(value))) + value
    else:
        return value[-length:]


@formatter
def left_align(value, length):
    if length <= 0:
        return ""

    value = _str(value)

    if len(value) < length:
        return value + (" " * (length - len(value)))
    else:
        return value[:length]


@formatter
def left(value, len):
    """
    return the `len` left-most characters in value
    :param value:
    :param len:
    :return:
    """
    if len <= 0:
        return ""
    return value[0:len]


@formatter
def comma(value):
    """
    FORMAT WITH THOUSANDS COMMA (,) SEPARATOR
    """
    if is_missing(value):
        return ""
    try:
        if float(value) == _round(float(value), 0):
            output = f"{int(value):,}"
        else:
            output = f"{float(value):,}"
    except Exception:
        output = _str(value)

    return output


@formatter
def quote(value):
    """
    return JSON-quoted value
    :param value:
    :return:
    """
    if is_null(value):
        return ""
    output = _json.dumps(_str(value))
    return output


@formatter
def hex(value):
    """
    return `value` in hex format
    :param value:
    :return:
    """
    if isinstance(value, int):
        return builtin_hex(value).upper()[2:]
    elif isinstance(value, bytes):
        return value.hex().upper()
    return to_string(value).encode("utf8").hex().upper()


_SNIP = "...<snip>..."


@formatter
def limit(value, length):
    """
    LIMIT THE STRING value TO GIVEN LENGTH, CHOPPING OUT THE MIDDLE IF REQUIRED
    """
    if is_null(value):
        return None
    try:
        if len(value) <= length:
            return value
        elif length < len(_SNIP) * 2:
            return value[0:length]
        else:
            lhs = int(round((length - len(_SNIP)) / 2, 0))
            rhs = length - len(_SNIP) - lhs
            return value[:lhs] + _SNIP + value[-rhs:]
    except Exception as e:
        logger.error("Not expected", cause=e)


def split(value, sep=CR):
    # GENERATOR VERSION OF split()
    # SOMETHING TERRIBLE HAPPENS, SOMETIMES, IN PYPY
    s = 0
    len_sep = len(sep)
    n = value.find(sep, s)
    while n > -1:
        yield value[s:n]
        s = n + len_sep
        n = value.find(sep, s)
    yield value[s:]


"""
THE REST OF THIS FILE IS TEMPLATE EXPANSION CODE USED BY mo-logs
"""


def expand_template(template, value):
    """
    :param template: A UNICODE STRING WITH VARIABLE NAMES IN MOUSTACHES `{{.}}`
    :param value: Data HOLDING THE PARAMETER VALUES
    :return: UNICODE STRING WITH VARIABLES EXPANDED
    """
    try:
        return _expand(template, (to_data(value),))
    except Exception as e:
        return "FAIL TO EXPAND: " + template


def common_prefix(*args):
    return os.path.commonprefix(args)


def find_first(value, find_arr, start=0):
    i = len(value)
    for f in find_arr:
        temp = value.find(f, start)
        if temp == -1:
            continue
        i = min(i, temp)
    if i == len(value):
        return -1
    return i


def is_hex(value):
    return all(c in string.hexdigits for c in value)


delchars_pattern = re.compile(r"[^a-zA-Z0-9]")


def deformat(value):
    """
    REMOVE NON-ALPHANUMERIC CHARACTERS
    """
    return delchars_pattern.sub("", value)


def _expand(template, seq):
    """
    seq IS TUPLE OF OBJECTS IN PATH ORDER INTO THE DATA TREE
    """
    if is_text(template):
        return _simple_expand(template, seq)
    elif is_data(template):
        # EXPAND LISTS OF ITEMS USING THIS FORM
        # {"from":from, "template":template, "separator":separator}
        template = to_data(template)
        assert template["from"], "Expecting template to have 'from' attribute"
        assert template.template, "Expecting template to have 'template' attribute"

        data = seq[-1][template["from"]]
        output = []
        for d in data:
            s = seq + (d,)
            output.append(_expand(template.template, s))
        return coalesce(template.separator, "").join(output)
    elif is_list(template):
        return "".join(_expand(t, seq) for t in template)
    else:
        logger.error("can not handle")


def _simple_expand(template, seq: Tuple[Data]):
    """
    seq IS TUPLE OF OBJECTS IN PATH ORDER INTO THE DATA TREE
    seq[-1] IS THE CURRENT CONTEXT
    """
    parsed = parse_template(template)

    result = []
    for text, code in parsed:
        result.append(text)
        if not code:
            continue
        path, *rest = code.split("|")
        var = path.lstrip(".")
        depth = min(len(seq), max(1, len(path) - len(var)))
        try:
            val = seq[-depth]
            if var:
                if is_sequence(val) and float(var) == _round(float(var), 0):
                    val = val[int(var)]
                else:
                    val = val[var]
            for func_name in rest:
                parts = func_name.split("(", 1)
                if len(parts) > 1:
                    val = eval(parts[0] + "(val, " + parts[1])
                else:
                    func = FORMATTERS.get(func_name)
                    if not func:
                        raise Exception(f"Can not find formatter {func_name}")
                    val = func(val)

            val = to_string(val)
            result.append(val)
        except Exception as cause:
            from mo_logs import Except

            cause = Except.wrap(cause)
            try:
                if cause.message.find("is not JSON serializable"):
                    # WORK HARDER
                    val = to_string(val)
                    result.append(val)
            except Exception as f:
                logger.warning(
                    f"Can not expand {op}|{rest} in template: {template_|json}", template_=template, cause=cause,
                )
            result.append(f"[template expansion error: ({cause.message})]")

    return "".join(result)


def chunk(data, size):
    if size < 1:
        logger.error("Can not chunk data into size less than 1", size=size)
    i = 0
    acc = []
    for v in data:
        acc.append(v)
        if len(acc) >= size:
            yield i, acc
            i += 1
            acc = []
    if acc:
        yield i, acc


def to_string(val):
    if is_null(val):
        return ""
    elif is_data(val) or is_many(val):
        return json_encoder(val, pretty=True)
    elif val.__class__.__name__ == "Date":
        return _str(val)
    elif hasattr(val, "__data__"):
        return json_encoder(val.__data__(), pretty=True)
    elif hasattr(val, "__json__"):
        return val.__json__()
    elif val.__class__.__name__ == "Duration":
        return f"{round(val.seconds, places=4)} seconds"
    elif isinstance(val, timedelta):
        duration = val.total_seconds()
        return f"{round(duration, places=4)} seconds"
    elif is_text(val):
        return val
    elif isinstance(val, binary_type):
        try:
            return val.decode("utf8")
        except Exception:
            pass

        return val.decode("latin1")
    else:
        try:
            return _str(val)
        except Exception:
            return f"{type(val)} type can not be converted to str"


toString = to_string


def edit_distance(s1, s2):
    """
    FROM http://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance# Python
    LICENCE http://creativecommons.org/licenses/by-sa/3.0/
    """
    if len(s1) < len(s2):
        return edit_distance(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return 1.0

    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = (
                previous_row[j + 1] + 1
            )  # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1  # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1] / len(s1)


DIFF_PREFIX = re.compile(r"@@ -(\d+(?:\s*,\d+)?) \+(\d+(?:\s*,\d+)?) @@")
WORDS = re.compile(r"[A-Z][0-9a-z]+|[A-Z][0-9A-Z]+(?=$|[^a-z])|[a-z][0-9a-z]+|[0-9][0-9]+|[0-9A-Za-z]")


def wordify(value):
    result = [w.lower() for w in WORDS.findall(value) if strip(w)]
    if len(result) <= 1:
        return [value.lower()]
    return result


def pairwise(values):
    """
    WITH values = [a, b, c, d, ...]
    RETURN [(a, b), (b, c), (c, d), ...]
    """
    i = iter(values)
    a = next(i)

    for b in i:
        yield (a, b)
        a = b


code_pattern = re.compile(r"[^][)(}{\"']*")
bodies = {
    "(": code_pattern,
    "[": code_pattern,
    "{": code_pattern,
    '"': re.compile(r'(\\"|[^"])*'),
    "'": re.compile(r"(\\'|[^'])*"),
}
closers = {
    ")": "(",
    "}": "{",
    "]": "[",
    '"': '"',
    "'": "'",
}
any_opener = re.compile(r'[\[{("\']')
code_opener = re.compile(r'[{"\']')
json_signature = re.compile(r"[\"']\s*:")


def parse_template(template):
    """
    WITH template = "a {b} c {d} e"
    RETURN LIST OF (_str, code) PAIRS [("a ", b), (" c ", d), (" e", "")]
    """

    result = []

    def append(prefix, code):
        if result:
            if not code or not prefix:
                prev_prefix, prev_code = result[-1]
                if not prev_code:
                    result[-1] = (prev_prefix + prefix, code)
                    return
        result.append((prefix, code))

    while True:
        opener = code_opener.search(template)
        if not opener:
            if template:
                append(template, "")
            return result
        i = opener.start()
        prefix, residue = template[:i], template[i:]
        code, template = parse_code(residue)
        if code == '""':
            append(prefix + '"', "")
        elif code == "''":
            append(prefix + "'", "")
        elif code.startswith("{{") and code.endswith("}}"):
            # STILL ALLOWING MOUSTACHES TO BE USED AS ESCAPE SEQUENCE
            append(prefix, code[2:-2])
        elif code.startswith("{") and code.endswith("}") and not json_signature.search(code):
            # STILL ALLOWING MOUSTACHES TO BE USED AS ESCAPE SEQUENCE
            append(prefix, code[1:-1])
        else:
            append(prefix + code, "")


def parse_code(code):
    """
    EXPECTING any_opener.match(code) TO BE TRUE
    """
    first, residue = code[0], code[1:]
    result = [first]
    while True:
        body = bodies[first].match(residue)
        remainder = residue[body.end() :]
        if not remainder:
            result.append(first)
            return "".join(result), residue
        residue = remainder
        result.append(body.group(0))
        try:
            next_char = residue[0]
        except Exception as cause:
            print(cause)
        if closers.get(next_char) == first:
            result.append(next_char)
            return "".join(result), residue[1:]
        elif next_char in bodies:
            more, residue = parse_code(residue)
            result.append(more)
        else:
            logger.error(f"expecting {closers.get(next_char)}")
