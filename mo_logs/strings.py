# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import json as _json
import math
import re
import string
from datetime import date, datetime as builtin_datetime, timedelta
from typing import Tuple

from mo_dots import (
    Data,
    coalesce,
    is_data,
    is_list,
    to_data,
    is_sequence,
    is_many,
)
from mo_future import (
    get_function_name,
    is_text,
    round as _round,
    transpose,
    xrange,
    zip_longest,
    binary_type,
)
from mo_imports import delay_import

from mo_logs.convert import (
    datetime2string,
    datetime2unix,
    milli2datetime,
    unix2datetime,
    value2json,
)

logger = delay_import("mo_logs.logger")
json_encoder = delay_import("mo_json.encoder.json_encoder")
Except = delay_import("mo_logs.exceptions.Except")
Duration = delay_import("mo_times.durations.Duration")


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
    if isinstance(value, (date, builtin_datetime)):
        pass
    elif value.__class__.__name__ == "Date":
        value = unix2datetime(value.unix)
    elif value < 10000000000:
        value = unix2datetime(value)
    else:
        value = milli2datetime(value)

    output = datetime2string(value, "%Y-%m-%d %H:%M:%S.%f")
    if output.endswith(".000000"):
        return output[:-7]
    elif output.endswith("000"):
        return output[:-3]
    else:
        return output


@formatter
def unicode(value):
    """
    Convert to a unicode string
    :param value: any value
    :return: unicode
    """
    if value == None:
        return ""
    return str(value)


@formatter
def unix(value):
    """
    Convert a date, or datetime to unix timestamp
    :param value:
    :return:
    """
    if isinstance(value, (date, builtin_datetime)):
        pass
    elif value < 10000000000:
        value = unix2datetime(value)
    else:
        value = milli2datetime(value)

    return str(datetime2unix(value))


value2url_param = None


@formatter
def url(value):
    """
    convert FROM dict OR string TO URL PARAMETERS
    """
    global value2url_param
    if not value2url_param:
        from mo_files.url import value2url_param
    return value2url_param(value)


@formatter
def html(value):
    """
    convert FROM unicode TO HTML OF THE SAME
    """
    import cgi

    return cgi.escape(value)


@formatter
def upper(value):
    """
    convert to uppercase
    :param value:
    :return:
    """
    return value.upper()


@formatter
def capitalize(value: str):
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
    return CR + toString(value).lstrip(CR)


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
        str(value)


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

    value = toString(value)
    try:
        content = value.rstrip()
        suffix = value[len(content) :]
        lines = content.splitlines()
        return prefix + (CR + prefix).join(lines) + suffix
    except Exception as e:
        raise Exception(f"Problem with indent of value ({e.message})\n{toString(value)}")


@formatter
def outdent(value):
    """
    remove common whitespace prefix from lines
    :param value:
    :return:
    """
    try:
        num = 100
        lines = toString(value).splitlines()
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
    if value == None:
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
    """
    REMOVE WHITESPACE (INCLUDING CONTROL CHARACTERS)
    """
    if not value or (ord(value[0]) > 32 and ord(value[-1]) > 32):
        return value

    s = 0
    e = len(value)
    while s < e:
        if ord(value[s]) > 32:
            break
        s += 1
    else:
        return ""

    for i in reversed(range(s, e)):
        if ord(value[i]) > 32:
            return value[s : i + 1]

    return ""


@formatter
def trim(value):
    """
    Alias for `strip`
    :param value:
    :return:
    """
    return strip(value)


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
    value = toString(value)
    if prefix == None:
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
def right(value, len):
    """
    Return the `len` last characters of a string
    :param value:
    :param len:
    :return:
    """
    if len <= 0:
        return ""
    return value[-len:]


@formatter
def right_align(value, length):
    """
    :param value: string to right align
    :param length: the number of characters to output (spaces added to left)
    :return:
    """
    if length <= 0:
        return ""

    value = str(value)

    if len(value) < length:
        return (" " * (length - len(value))) + value
    else:
        return value[-length:]


@formatter
def left_align(value, length):
    if length <= 0:
        return ""

    value = str(value)

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
    try:
        if float(value) == _round(float(value), 0):
            output = "{:,}".format(int(value))
        else:
            output = "{:,}".format(float(value))
    except Exception:
        output = str(value)

    return output


@formatter
def quote(value):
    """
    return JSON-quoted value
    :param value:
    :return:
    """
    if value == None:
        return ""
    output = _json.dumps(str(value))
    return output


@formatter
def hex(value):
    """
    return `value` in hex format
    :param value:
    :return:
    """
    return hex(value)


_SNIP = "...<snip>..."


@formatter
def limit(value, length):
    """
    LIMIT THE STRING value TO GIVEN LENGTH, CHOPPING OUT THE MIDDLE IF REQUIRED
    """
    if value == None:
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


@formatter
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
    value = None


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
        value = to_data(value)
        if is_text(template):
            return _simple_expand(template, (value,))

        return _expand(template, (value,))
    except Exception as e:
        return "FAIL TO EXPAND: " + template


def common_prefix(*args):
    prefix = args[0]
    for a in args[1:]:
        for i in range(min(len(prefix), len(a))):
            if a[i] != prefix[i]:
                prefix = prefix[:i]
                break
    return prefix


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


delchars = "".join(c for c in map(chr, range(256)) if not c.isalnum())


def deformat(value):
    """
    REMOVE NON-ALPHANUMERIC CHARACTERS

    FOR SOME REASON translate CAN NOT BE CALLED:
        ERROR: translate() takes exactly one argument (2 given)
        File "C:\\Python27\\lib\\string.py", line 493, in translate
    """
    output = []
    for c in value:
        if c in delchars:
            continue
        output.append(c)
    return "".join(output)


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
                    val = FORMATTERS[func_name](val)
            val = toString(val)
            result.append(val)
        except Exception as cause:
            from mo_logs import Except

            cause = Except.wrap(cause)
            try:
                if cause.message.find("is not JSON serializable"):
                    # WORK HARDER
                    val = toString(val)
                    result.append(val)
            except Exception as f:
                logger.warning(
                    f"Can not expand {op}|{rest} in template: {template_|json}",
                    template_=template,
                    cause=cause,
                )
            result.append(f"[template expansion error: ({cause.message})]")

    return "".join(result)


def chunk(data, size=0):
    for i in range(0, len(data), size):
        yield data[i:i + size]


def toString(val):
    if val == None:
        return ""
    elif is_data(val) or is_many(val):
        return json_encoder(val, pretty=True)
    elif hasattr(val, "__data__"):
        return json_encoder(val.__data__(), pretty=True)
    elif hasattr(val, "__json__"):
        return val.__json__()
    elif isinstance(val, Duration):
        return f"{round(val.seconds, places=4)} seconds"
    elif isinstance(val, timedelta):
        duration = val.total_seconds()
        return f"{round(duration, 3)} seconds"
    elif is_text(val):
        return val
    elif isinstance(val, binary_type):
        try:
            return val.decode("utf8")
        except Exception as _:
            pass

        try:
            return val.decode("latin1")
        except Exception as e:
            logger.error(f"{type(val)} type can not be converted to unicode", cause=e)
    else:
        try:
            return str(val)
        except Exception as e:
            logger.error(f"{type(val)} type can not be converted to unicode", cause=e)


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


def apply_diff(text, diff, reverse=False, verify=True):
    """
    SOME EXAMPLES OF diff
    #@@ -1 +1 @@
    #-before china goes live, the content team will have to manually update the settings for the china-ready apps currently in marketplace.
    #+before china goes live (end January developer release, June general audience release) , the content team will have to manually update the settings for the china-ready apps currently in marketplace.
    @@ -0,0 +1,3 @@
    +before china goes live, the content team will have to manually update the settings for the china-ready apps currently in marketplace.
    +
    +kward has the details.
    @@ -1 +1 @@
    -before china goes live (end January developer release, June general audience release), the content team will have to manually update the settings for the china-ready apps currently in marketplace.
    +before china goes live , the content team will have to manually update the settings for the china-ready apps currently in marketplace.
    @@ -3 +3 ,6 @@
    -kward has the details.+kward has the details.
    +
    +Target Release Dates :
    +https://mana.mozilla.org/wiki/display/PM/Firefox+OS+Wave+Launch+Cross+Functional+View
    +
    +Content Team Engagement & Tasks : https://appreview.etherpad.mozilla.org/40
    """

    if not diff:
        return text
    output = text
    hunks = [
        (new_diff[start_hunk], new_diff[start_hunk + 1 : end_hunk])
        for new_diff in [
            [d.lstrip() for d in diff if d.lstrip() and d != "\\ No newline at end of file"] + ["@@"]
        ]  # ANOTHER REPAIR
        for start_hunk, end_hunk in pairwise(i for i, l in enumerate(new_diff) if l.startswith("@@"))
    ]
    for header, hunk_body in reversed(hunks) if reverse else hunks:
        matches = DIFF_PREFIX.match(header.strip())
        if not matches:
            logger.error("Can not handle \n---\n{{diff}}\n---\n", diff=diff)

        removes = tuple(int(i.strip()) for i in matches.group(1).split(","))  # EXPECTING start_line, length TO REMOVE
        remove = Data(start=removes[0], length=1 if len(removes) == 1 else removes[1])  # ASSUME FIRST LINE
        adds = tuple(int(i.strip()) for i in matches.group(2).split(","))  # EXPECTING start_line, length TO ADD
        add = Data(start=adds[0], length=1 if len(adds) == 1 else adds[1])

        if add.length == 0 and add.start == 0:
            add.start = remove.start

        def repair_hunk(hunk_body):
            # THE LAST DELETED LINE MAY MISS A "\n" MEANING THE FIRST
            # ADDED LINE WILL BE APPENDED TO THE LAST DELETED LINE
            # EXAMPLE: -kward has the details.+kward has the details.
            # DETECT THIS PROBLEM FOR THIS HUNK AND FIX THE DIFF
            if reverse:
                last_lines = [o for b, o in zip(reversed(hunk_body), reversed(output)) if b != "+" + o]
                if not last_lines:
                    return hunk_body

                last_line = last_lines[0]
                for problem_index, problem_line in enumerate(hunk_body):
                    if problem_line.startswith("-") and problem_line.endswith("+" + last_line):
                        split_point = len(problem_line) - (len(last_line) + 1)
                        break
                    elif problem_line.startswith("+" + last_line + "-"):
                        split_point = len(last_line) + 1
                        break
                else:
                    return hunk_body
            else:
                if not output:
                    return hunk_body
                last_line = output[-1]
                for problem_index, problem_line in enumerate(hunk_body):
                    if problem_line.startswith("+") and problem_line.endswith("-" + last_line):
                        split_point = len(problem_line) - (len(last_line) + 1)
                        break
                    elif problem_line.startswith("-" + last_line + "+"):
                        split_point = len(last_line) + 1
                        break
                else:
                    return hunk_body

            new_hunk_body = (
                hunk_body[:problem_index]
                + [problem_line[:split_point], problem_line[split_point:]]
                + hunk_body[problem_index + 1 :]
            )
            return new_hunk_body

        hunk_body = repair_hunk(hunk_body)

        if reverse:
            new_output = (
                output[: add.start - 1]
                + [d[1:] for d in hunk_body if d and d[0] == "-"]
                + output[add.start + add.length - 1 :]
            )
        else:
            new_output = (
                output[: add.start - 1]
                + [d[1:] for d in hunk_body if d and d[0] == "+"]
                + output[add.start + remove.length - 1 :]
            )
        output = new_output

    if verify:
        original = apply_diff(output, diff, not reverse, False)
        if set(text) != set(original):  # bugzilla-etl diffs are a jumble

            for t, o in zip_longest(text, original):
                if t in ["reports: https://goo.gl/70o6w6\r"]:
                    break  # KNOWN INCONSISTENCIES
                if t != o:
                    logger.error("logical verification check failed")
                    break

    return output


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


def parse_template(template):
    """
    WITH template = "a {b} c {d} e"
    RETURN LIST OF (str, code) PAIRS [("a ", b), (" c ", d), (" e", "")]
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
            append(prefix+'"', "")
        elif code == "''":
            append(prefix + "'", "")
        elif code.startswith("{{") and code.endswith("}}"):
        # STILL ALLOWING MOUSTACHES TO BE USED AS ESCAPE SEQUENCE
            append(prefix, code[2:-2])
        elif code.startswith("{") and code.endswith("}"):
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
        remainder = residue[body.end():]
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
