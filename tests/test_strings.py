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
from mo_logs.strings import expand_template, wordify, round, datetime, parse_template


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
        result = parse_template("this is a test of {name|capitalize(\"some value\", lambda x: {'x': x})}")
        expected = [("this is a test of ", "name|capitalize(\"some value\", lambda x: {'x': x})",)]
        self.assertEqual(result, expected)

    def test_parse5(self):
        result = parse_template("this is a test of {{name|capitalize(\"some value\", lambda x: {'x': x})}}")
        expected = [("this is a test of ", "name|capitalize(\"some value\", lambda x: {'x': x})",)]
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
