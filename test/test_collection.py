# Copyright 2009 10gen, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test the collection module."""
import unittest

import qcheck
from test_connection import get_connection
from pymongo.objectid import ObjectId
from pymongo.collection import Collection
from pymongo.errors import InvalidName
from pymongo.database import ASCENDING, DESCENDING
from pymongo.son import SON

class TestCollection(unittest.TestCase):
    def setUp(self):
        self.db = get_connection().test

    def test_collection(self):
        self.assertRaises(TypeError, Collection, self.db, 5)

        def make_col(base, name):
            return base[name]

        self.assertRaises(InvalidName, make_col, self.db, "")
        self.assertRaises(InvalidName, make_col, self.db, "te$t")
        self.assertRaises(InvalidName, make_col, self.db, ".test")
        self.assertRaises(InvalidName, make_col, self.db, "test.")
        self.assertRaises(InvalidName, make_col, self.db, "tes..t")
        self.assertRaises(InvalidName, make_col, self.db.test, "")
        self.assertRaises(InvalidName, make_col, self.db.test, "te$t")
        self.assertRaises(InvalidName, make_col, self.db.test, ".test")
        self.assertRaises(InvalidName, make_col, self.db.test, "test.")
        self.assertRaises(InvalidName, make_col, self.db.test, "tes..t")

        self.assertTrue(isinstance(self.db.test, Collection))
        self.assertEqual(self.db.test, self.db["test"])
        self.assertEqual(self.db.test, Collection(self.db, "test"))
        self.assertEqual(self.db.test.mike, self.db["test.mike"])
        self.assertEqual(self.db.test["mike"], self.db["test.mike"])

    def test_create_index(self):
        db = self.db

        self.assertRaises(TypeError, db.test.create_index, 5)
        self.assertRaises(TypeError, db.test.create_index, "hello")
        self.assertRaises(ValueError, db.test.create_index, [])
        self.assertRaises(TypeError, db.test.create_index, [], ASCENDING)
        self.assertRaises(TypeError, db.test.create_index, [("hello", DESCENDING)], DESCENDING)
        self.assertRaises(TypeError, db.test.create_index, "hello", "world")

        db.test.drop_indexes()
        self.assertFalse(db.system.indexes.find_one({"ns": u"test.test"}))

        db.test.create_index("hello", ASCENDING)
        db.test.create_index([("hello", DESCENDING), ("world", ASCENDING)])

        count = 0
        for _ in db.system.indexes.find({"ns": u"test.test"}):
            count += 1
        self.assertEqual(count, 2)

        db.test.drop_indexes()
        self.assertFalse(db.system.indexes.find_one({"ns": u"test.test"}))
        db.test.create_index("hello", ASCENDING)
        self.assertEqual(db.system.indexes.find_one({"ns": u"test.test"}),
                         SON([(u"name", u"hello_1"),
                              (u"ns", u"test.test"),
                              (u"key", SON([(u"hello", 1)]))]))

        db.test.drop_indexes()
        self.assertFalse(db.system.indexes.find_one({"ns": u"test.test"}))
        db.test.create_index([("hello", DESCENDING), ("world", ASCENDING)])
        self.assertEqual(db.system.indexes.find_one({"ns": u"test.test"}),
                         SON([(u"name", u"hello_-1_world_1"),
                              (u"ns", u"test.test"),
                              (u"key", SON([(u"hello", -1),
                                            (u"world", 1)]))]))

    def test_drop_index(self):
        db = self.db
        db.test.drop_indexes()
        db.test.create_index("hello", ASCENDING)
        name = db.test.create_index("goodbye", DESCENDING)

        self.assertEqual(db.system.indexes.find({"ns": u"test.test"}).count(), 2)
        self.assertEqual(name, "goodbye_-1")
        db.test.drop_index(name)
        self.assertEqual(db.system.indexes.find({"ns": u"test.test"}).count(), 1)
        self.assertEqual(db.system.indexes.find_one({"ns": u"test.test"}),
                         SON([(u"name", u"hello_1"),
                              (u"ns", u"test.test"),
                              (u"key", SON([(u"hello", 1)]))]))

    def test_index_info(self):
        db = self.db
        db.test.drop_indexes()
        self.assertEqual(db.test.index_information(), {})

        db.test.create_index("hello", ASCENDING)
        self.assertEqual(db.test.index_information(),
                         {"hello_1": [("hello", ASCENDING)]})

        db.test.create_index([("hello", DESCENDING), ("world", ASCENDING)])
        self.assertEqual(db.test.index_information(),
                         {"hello_1": [("hello", ASCENDING)],
                          "hello_-1_world_1": [("hello", DESCENDING),
                                               ("world", ASCENDING)]})

    def test_options(self):
        db = self.db
        db.drop_collection("test")
        db.test.save({})
        self.assertEqual(db.test.options(), {})
        self.assertEqual(db.test.doesnotexist.options(), {})

        db.drop_collection("test")
        options = {"capped": True}
        db.create_collection("test", options)
        self.assertEqual(db.test.options(), options)
        db.drop_collection("test")

    def test_insert_find_one(self):
        db = self.db
        db.test.remove({})
        self.assertEqual(db.test.find().count(), 0)
        doc = {"hello": u"world"}
        db.test.insert(doc)
        self.assertEqual(db.test.find().count(), 1)
        self.assertEqual(doc, db.test.find_one())

        def remove_insert_find_one(dict):
            db.test.remove({})
            db.test.insert(dict)
            return db.test.find_one() == dict

        qcheck.check_unittest(self, remove_insert_find_one, qcheck.gen_mongo_dict(3))

    def test_id_can_be_anything(self):
        db = self.db

        db.test.remove({})
        auto_id = {"hello": "world"}
        db.test.insert(auto_id)
        self.assertTrue(isinstance(auto_id["_id"], ObjectId))

        numeric = {"_id": 240, "hello": "world"}
        db.test.insert(numeric)
        self.assertEqual(numeric["_id"], 240)

        object = {"_id": numeric, "hello": "world"}
        db.test.insert(object)
        self.assertEqual(object["_id"], numeric)

        for x in db.test.find():
            self.assertEqual(x["hello"], u"world")
            self.assertTrue("_id" in x)

    def test_iteration(self):
        db = self.db

        def iterate():
            [a for a in db.test]

        self.assertRaises(TypeError, iterate)

    def test_insert_multiple(self):
        db = self.db
        db.drop_collection("test")
        doc1 = {"hello": u"world"}
        doc2 = {"hello": u"mike"}
        self.assertEqual(db.test.find().count(), 0)
        db.test.insert([doc1, doc2])
        self.assertEqual(db.test.find().count(), 2)
        self.assertEqual(doc1, db.test.find_one({"hello": u"world"}))
        self.assertEqual(doc2, db.test.find_one({"hello": u"mike"}))

if __name__ == "__main__":
    unittest.main()