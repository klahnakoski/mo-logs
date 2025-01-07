# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_times import Date

from mo_logs import strings
from mo_logs.strings import expand_template, wordify, round, datetime, parse_template, chunk, comma, between


class TestStrings(FuzzyTestCase):
    def setUp(self):
        pass

    def test_right_align(self):
        total = 123.45
        some_list = [10, 11, 14, 80]

        result = expand_template("it is currently {{now|datetime}}", {"now": 1420119241000})
        self.assertEqual(result, "it is currently 2015-01-01 13:34:01")

        result = expand_template("Total: {{total|right_align(20)}}", {"total": total})
        self.assertEqual(result, "Total:               123.45")

        result = expand_template("Summary:\n{{list|json|indent}}", {"list": some_list})
        self.assertEqual(result, "Summary:\n\t[10, 11, 14, 80]")

        result = expand_template("Summary:\n{{list|indent}}", {"list": some_list})
        self.assertEqual(result, "Summary:\n\t[10, 11, 14, 80]")

    def test_no_align(self):
        details = {"person": {"name": "Kyle Lahnakoski", "age": 40}}
        result = expand_template("{{person.name}} is {{person.age}} years old", details)
        self.assertEqual(result, "Kyle Lahnakoski is 40 years old")

    def test_percent(self):
        self.assertEqual(strings.percent(0.123, digits=1), "10%")
        self.assertEqual(strings.percent(0.123, digits=2), "12%")
        self.assertEqual(strings.percent(0.123, digits=3), "12.3%")
        self.assertEqual(strings.percent(0.120, digits=3), "12.0%")

        self.assertEqual(strings.percent(0.0123, digits=1), "1%")
        self.assertEqual(strings.percent(0.0123, digits=2), "1.2%")
        self.assertEqual(strings.percent(0.0123, digits=3), "1.23%")
        self.assertEqual(strings.percent(0.0120, digits=3), "1.20%")

        self.assertEqual(strings.percent(0.5), "50%")
        self.assertEqual(strings.percent(0), "0%")
        self.assertEqual(strings.percent(None), "")

    def test_wordify(self):
        self.assertEqual(wordify("thisIsATest"), ["this", "is", "a", "test"])
        self.assertEqual(wordify("another.test"), ["another", "test"])
        self.assertEqual(wordify("also-a_test999"), ["also", "a", "test999"])
        self.assertEqual(wordify("BIG_WORDS"), ["big", "words"])
        self.assertEqual(wordify("ALSO_A_TEST999"), ["also", "a", "test999"])
        self.assertEqual(wordify("c:123:a"), ["c", "123", "a"])
        self.assertEqual(wordify("__int__"), ["__int__"])
        self.assertEqual(wordify(":"), [":"])
        self.assertEqual(wordify("__ENV__"), ["__env__"])

    def test_round(self):
        self.assertEqual(round(3.14), "3")

    def test_datatime(self):
        time = Date("2022-03-12")
        self.assertEqual(datetime(time), "2022-03-12 00:00:00")

    def test_quote(self):
        def f():
            return 1

        self.assertTrue(strings.quote(f).startswith('"<function TestStrings.test_quote.<locals>.f at'))

    def test_capitalize(self):
        result = expand_template("{{name|capitalize}}", {"name": "lahnakoski"})
        self.assertEqual(result, "Lahnakoski")

    def test_parse1(self):
        result = parse_template("{{name|capitalize}}")
        expected = [("", "name|capitalize")]
        self.assertEqual(result, expected)

    def test_parse2(self):
        result = parse_template("{{name|capitalize}} {{age}}")
        expected = [("", "name|capitalize"), (" ", "age")]
        self.assertEqual(result, expected)

    def test_parse3(self):
        result = parse_template("this is a test of {name}")
        expected = [("this is a test of ", "name")]
        self.assertEqual(result, expected)

    def test_parse4(self):
        result = parse_template("this is a test of {name|capitalize(\"some value\", lambda x: {3: x})}")
        expected = [("this is a test of ", "name|capitalize(\"some value\", lambda x: {3: x})")]
        self.assertEqual(result, expected)

    def test_parse5(self):
        result = parse_template("this is a test of {{name|capitalize(\"some value\", lambda x: {'x': x})}}")
        expected = [("this is a test of ", "name|capitalize(\"some value\", lambda x: {'x': x})")]
        self.assertEqual(result, expected)

    def test_parse6(self):
        result = parse_template('this is a test of {name|capitalize("some () value")}')
        expected = [("this is a test of ", 'name|capitalize("some () value")')]
        self.assertEqual(result, expected)

    def test_parse_extra_curly(self):
        with self.assertRaises(Exception):
            parse_template('this is a test of {name|capitalize{("some () value"}')

    def test_double_braces(self):
        result = parse_template("this is a {{{test}}} of {name|capitalize('some () value')}")
        expected = [
            ("this is a ", "{test}"),
            (" of ", "name|capitalize('some () value')"),
        ]
        self.assertEqual(result, expected)

    def test_code(self):
        result = parse_template('a = "{"\nb="}"\n')
        expected = [('a = "{"\nb="}"\n', "")]
        self.assertEqual(result, expected)

    def test_double_quote(self):
        result = parse_template(' - ""{location.file}:{location.line}"" -')
        expected = [(' - "', "location.file"), (":", "location.line"), ('" -', "")]
        self.assertEqual(result, expected)

    def test_chunk(self):
        def things():
            for i in range(20):
                yield i

        result = list(chunk(things(), 5))
        self.assertEqual(
            result, [(0, [0, 1, 2, 3, 4]), (1, [5, 6, 7, 8, 9]), (2, [10, 11, 12, 13, 14]), (3, [15, 16, 17, 18, 19])]
        )

    def test_chunk2(self):
        def things():
            for i in range(20):
                yield i

        result = list(chunk(things(), 7))
        self.assertEqual(
            result, [(0, [0, 1, 2, 3, 4, 5, 6]), (1, [7, 8, 9, 10, 11, 12, 13]), (2, [14, 15, 16, 17, 18, 19])]
        )

    def test_comma(self):
        self.assertEqual(comma(1000), "1,000")
        self.assertEqual(comma(2000.1), "2,000.1")
        self.assertEqual(comma(3000000.99), "3,000,000.99")

    def test_json_in_template(self):
        result = expand_template("{'example':42}", {"list": [1, 2, 3]})
        self.assertEqual(result, "{'example':42}")

    def test_unicode_formatter(self):
        result = expand_template("{name|unicode}", {"name": {"a": 10}})
        self.assertEqual(result, "{'a': 10}")

        result = expand_template("{name|unicode}", {"name": None})
        self.assertEqual(result, "")

    def test_str_formatter(self):
        result = expand_template("{name|str}", {"name": {"a": 10}})
        self.assertEqual(result, "{'a': 10}")

        result = expand_template("{name|str}", {"name": None})
        self.assertEqual(result, "")

    def test_unix_formatter(self):
        now = Date("2025-01-04 14:21:34.999")

        result = expand_template("{name|unix}", {"name": "a/b/c"})
        self.assertEqual(result, "a/b/c")

        result = expand_template("{value|unix}", {"value": now.format()})
        self.assertEqual(result, str(int(now.unix)))

        result = expand_template("{value|unix}", {"value": now.milli})
        self.assertEqual(result, str(int(now.unix)))

    def test_strip_formatter(self):
        result = expand_template("{name|strip}", {"name": "  a  "})
        self.assertEqual(result, "a")

        result = expand_template("{name|trim}", {"name": "  a  b  "})
        self.assertEqual(result, "a  b")

    def test_right_formatter(self):
        result = expand_template("{value|right(10)}", {"value": "01234567890"})
        self.assertEqual(result, "1234567890")

        result = expand_template("{value|right(10)}", {"value": "012345"})
        self.assertEqual(result, "012345")

        result = expand_template("{value|right(-1)}", {"value": "01234567890"})
        self.assertEqual(result, "")

    def test_left_formatter(self):
        result = expand_template("{value|left(10)}", {"value": "01234567890"})
        self.assertEqual(result, "0123456789")

        result = expand_template("{value|left(10)}", {"value": "012345"})
        self.assertEqual(result, "012345")

        result = expand_template("{value|left(-1)}", {"value": "01234567890"})
        self.assertEqual(result, "")

    def test_right_align_formatter(self):
        result = expand_template("{value|right_align(10)}", {"value": "01234567890"})
        self.assertEqual(result, "1234567890")

        result = expand_template("{value|right_align(10)}", {"value": "012345"})
        self.assertEqual(result, "    012345")

        result = expand_template("{value|right_align(-1)}", {"value": "01234567890"})
        self.assertEqual(result, "")

    def test_left_align_formatter(self):
        result = expand_template("{value|left_align(10)}", {"value": "01234567890"})
        self.assertEqual(result, "0123456789")

        result = expand_template("{value|left_align(10)}", {"value": "012345"})
        self.assertEqual(result, "012345    ")

        result = expand_template("{value|left_align(-1)}", {"value": "01234567890"})
        self.assertEqual(result, "")

    def test_comma_formatter(self):
        result = expand_template("{value|comma}", {"value": 1234567890})
        self.assertEqual(result, "1,234,567,890")

        result = expand_template("{value|comma}", {"value": 123456})
        self.assertEqual(result, "123,456")

        result = expand_template("{value|comma}", {"value": 123})
        self.assertEqual(result, "123")

        result = expand_template("{value|comma}", {"value": None})
        self.assertEqual(result, "")

        result = expand_template("{value|comma}", {"value": "abc"})
        self.assertEqual(result, "abc")

    def test_quote_formatter(self):
        result = expand_template("{value|quote}", {"value": "abc"})
        self.assertEqual(result, '"abc"')

        result = expand_template("{value|quote}", {"value": 123})
        self.assertEqual(result, '"123"')

        result = expand_template("{value|quote}", {"value": None})
        self.assertEqual(result, "")

    def test_hex_formatter(self):
        result = expand_template("{value|hex}", {"value": 123})
        self.assertEqual(result, "7B")

        result = expand_template("{value|hex}", {"value": 0})
        self.assertEqual(result, "0")

        result = expand_template("{value|hex}", {"value": None})
        self.assertEqual(result, "")

        result = expand_template("{value|hex}", {"value": b"hello"})
        self.assertEqual(result, "68656C6C6F")

    def test_edit_distance(self):
        result = strings.edit_distance("abc", "abc")
        self.assertEqual(result, 0)

        result = strings.edit_distance("abc", "abcd")
        self.assertEqual(result, 0.25)

        result = strings.edit_distance("abc", "ab")
        self.assertEqual(result, 0.3333333333333333)

        result = strings.edit_distance("abc", "def")
        self.assertEqual(result, 1)

    # tests to cover def datetime(value):

    def test_datetime(self):
        result = expand_template("{value|datetime}", {"value": 1420119241000})
        self.assertEqual(result, "2015-01-01 13:34:01")

        # New assert to cover the case where output ends with "000"
        result = expand_template("{value|datetime}", {"value": 1420119241})
        self.assertEqual(result, "2015-01-01 13:34:01")

        result = datetime(1420119241.000001)
        self.assertEqual(result, "2015-01-01 13:34:01.000001")

    def test_url(self):
        result = expand_template("{value|url}", {"value": {"value": "hello"}})
        self.assertEqual(result, 'value=hello')

        result = expand_template("{value|url}", {"value": {"value": [1, 2, 3]}})
        self.assertEqual(result, 'value=1,2,3')

        result = expand_template("{value|url}", {"value": {"value": None}})
        self.assertEqual(result, '')

        result = expand_template("{value|url}", {"value": {"value": {"a": 1, "b": 2}}})
        self.assertEqual(result, 'value.a=1&value.b=2')

    def test_between(self):
        self.assertEqual(between("this is a test", "this", "test"), " is a ")
        self.assertEqual(between("this is a test", "is", "test"), " a ")
        self.assertEqual(between("this is a test", "this", "a"), " is ")
        self.assertEqual(between("this is a test", None, "test"), "this is a ")
        self.assertEqual(between("this is a test", "this", None), " is a test")
        self.assertEqual(between("this is a test", " is", None), " a test")
        self.assertEqual(between("this is a test", "not", "test"), None)
        self.assertEqual(between("this is a test", "this", "not"), None)
        self.assertEqual(between("this is a test", "this", "test", 5), None)
        self.assertEqual(between("this is a test", "is", "test", 5), " a ")
        self.assertEqual(between("this is a test", "this", "a", 5), None)
        self.assertEqual(between("this is a test", None, "pie"), None)
