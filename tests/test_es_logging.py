# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.O
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import unicode_literals

from unittest import skipIf

from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Till
from mo_times import Date

from mo_dots import Data
from mo_logs import Log
from tests.config import IS_TRAVIS

TEST_CONFIG = Data(
    host="http://localhost",
    index="test-es-logging",
    type="log"
)
GET_RECENT_LOG = {
    "query": {
        "nested": {
            "path": "~N~",
            "query": {"term": {"~N~.template.~s~": "this is a {{type}} test"}}
        }
    },
    "from": 0,
    "size": 1,
    "sort": [{"~N~.timestamp.~n~": "desc"}],
    "stored_fields": ["_source"]
}


@skipIf(IS_TRAVIS, "ES logging not tested on travis")
class TestESLogging(FuzzyTestCase):

    cluster = None

    @classmethod
    def setUpClass(cls):
        from pyLibrary.env.elasticsearch import Cluster
        cls.cluster = Cluster(TEST_CONFIG)

    def setUp(self):
        Log.start({"trace": True})

    def test_note(self):
        self._before_test()
        Log.note("this is a {{type}} test", type="basic")
        es = self._after_test()

        # VERIFY LOG
        result = es.search(GET_RECENT_LOG).hits.hits[0]._source
        expected = {"~N~": [{
            "context": {"~s~": "NOTE"},
            "template": {"~s~": "this is a {{type}} test"},
            "params": {"type": {"~s~": "basic"}, "~e~": 1}
        }]}
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
        result = es.search(GET_RECENT_LOG).hits.hits[0]._source
        expected = {"~N~": [{
            "context": {"~s~": "WARNING"},
            "template": {"~s~": "this is a {{type}} test"},
            "params": {"type": {"~s~": "basic"}, "~e~": 1}
        }]}
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
        result = es.search(GET_RECENT_LOG).hits.hits[0]._source
        expected = {"~N~": [{
            "context": {"~s~": "ALARM"},
            "template": {"~s~": "this is a {{type}} test"},
            "params": {"type": {"~s~": "basic"}, "~e~": 1}
        }]}
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
        self.temp = Log.main_log
        from mo_logs.log_usingElasticSearch import StructuredLogger_usingElasticSearch
        self.es_logger = Log.main_log = self.es_logger = StructuredLogger_usingElasticSearch(TEST_CONFIG)

    def _after_test(self):
        Log.main_log = self.temp
        cluster = self.es_logger.es.cluster

        # WAIT FOR SOMETHING TO SHOW UP IN THE LOG
        found = False
        while not found:
            for q in self.es_logger.es.known_queues.values():
                result = q.slow_queue.search({
                    "from": 0,
                    "size": 1,
                    "stored_fields": ["_source"]
                })
                if result.hits.total:
                    found = True
                    break
                q.slow_queue.refresh()
            else:
                Till(seconds=1).wait()

        self.es_logger.stop()
        cluster.get_metadata(after=Date.now())
        index = cluster.get_index(TEST_CONFIG)
        return index

    def _delete_testindex(self):
        # DELETE OLD INDEX
        try:
            i = self.cluster.get_best_matching_index(TEST_CONFIG.index)
            if i:
                self.cluster.delete_index(i.index)
        except Exception as e:
            pass
        self.cluster.get_metadata(after=Date.now())


class NullOp(object):
    pass

NULL = NullOp()

