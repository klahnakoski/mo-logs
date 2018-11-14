# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import unicode_literals

from jx_base.expressions import NULL
from mo_dots import Data
from mo_logs import Log, machine_metadata
from mo_logs.log_usingElasticSearch import StructuredLogger_usingElasticSearch
from mo_testing.fuzzytestcase import FuzzyTestCase
from pyLibrary.env.elasticsearch import Cluster

TEST_CONFIG = Data(
    host="http://localhost",
    index="test-es-logging",
    type="log"
)


class TestESLogging(FuzzyTestCase):

    cluster = Cluster(TEST_CONFIG)

    def setUp(self):
        Log.start({"trace": True})

    def test_note(self):
        self._before_test()
        Log.note("this is a {{type}} test", type="basic")
        es = self._after_test()

        # VERIFY LOG
        result = es.search({
            "query": {"term": {"template.~s~": "this is a {{type}} test"}},
            "from": 0,
            "size": 1,
            "sort": [{"timestamp.~n~": "desc"}],
            "stored_fields": ["_source"]
        }).hits.hits[0]._source
        expected = {
            "context": {"~s~": "NOTE"},
            "template": {"~s~": "this is a {{type}} test"},
            "params": {"type": {"~s~": "basic"}, "~e~": 1}
        }
        self.assertEqual(result, expected)

        self.assertIsNotNone(result.machine.name)
        self.assertIsNotNone(result.location)
        self.assertIsNotNone(result.thread)
        self.assertIsNotNone(result.timestamp['~n~'])

        self.assertEqual(result.timestamp['~s~'], NULL)
        self._delete_testindex()

    def test_warning(self):
        self._before_test()
        Log.warning("this is a {{type}} test", type="basic")
        es = self._after_test()

        # VERIFY LOG
        result = es.search({
            "query": {"term": {"template.~s~": "this is a {{type}} test"}},
            "from": 0,
            "size": 1,
            "sort": [{"timestamp.~n~": "desc"}],
            "stored_fields": ["_source"]
        }).hits.hits[0]._source
        expected = {
            "context": {"~s~": "WARNING"},
            "template": {"~s~": "this is a {{type}} test"},
            "params": {"type": {"~s~": "basic"}, "~e~": 1}
        }
        self.assertEqual(result, expected)

        self.assertIsNotNone(result.machine.name)
        self.assertIsNotNone(result.location)
        self.assertIsNotNone(result.thread)
        self.assertIsNotNone(result.timestamp['~n~'])

        self.assertEqual(result.timestamp['~s~'], NULL)
        self._delete_testindex()

    def test_alarm(self):
        self._before_test()
        Log.alarm("this is a {{type}} test", type="basic")
        es = self._after_test()

        # VERIFY LOG
        result = es.search({
            "query": {"term": {"template.~s~": "this is a {{type}} test"}},
            "from": 0,
            "size": 1,
            "sort": [{"timestamp.~n~": "desc"}],
            "stored_fields": ["_source"]
        }).hits.hits[0]._source
        expected = {
            "context": {"~s~": "ALARM"},
            "template": {"~s~": "this is a {{type}} test"},
            "params": {"type": {"~s~": "basic"}, "~e~": 1}
        }
        self.assertEqual(result, expected)

        self.assertIsNotNone(result.machine.name)
        self.assertIsNotNone(result.location)
        self.assertIsNotNone(result.thread)
        self.assertIsNotNone(result.timestamp['~n~'])

        self.assertEqual(result.timestamp['~s~'], NULL)
        self._delete_testindex()

    def _before_test(self):
        self._delete_testindex()

        # CREATE INDEX, AND LOG
        self.es_logger = Log.main_log = self.es_logger = StructuredLogger_usingElasticSearch(TEST_CONFIG)
        self.temp = Log.main_log

    def _after_test(self):
        Log.main_log = self.temp
        self.es_logger.stop()
        self.cluster.get_metadata(force=True)
        return self.cluster.get_index(TEST_CONFIG)

    def _delete_testindex(self):
        # DELETE OLD INDEX
        try:
            i = self.cluster.get_best_matching_index(TEST_CONFIG.index)
            if i:
                self.cluster.delete_index(i.index)
        except Exception as e:
            pass
        self.cluster.get_metadata(force=True)
