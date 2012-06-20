import unittest

from base.utils import use_mongo
from base.gob import SimpleEnv, Gob
from gb import create_jobs


class TestPrep(unittest.TestCase):
    def setUp(self):
        self.gob = Gob(SimpleEnv())
        use_mongo('fl_fixture')
        create_jobs(self.gob)
        SimpleEnv.THE_FS = {}

    def test_mloc_users(self):
        self.gob.run_job('mloc_uids')
        uids = SimpleEnv.THE_FS['mloc_uids.03']
        self.assertEqual(len(uids),1)
        self.assertEqual(uids[0]['name'], 'Chris')
        self.assertEqual(uids[0]['folc'], 9)

    def test_edge_d(self):
        self.gob.run_job('mloc_uids')
        self.gob.run_job('edge_d')
        edge03 = SimpleEnv.THE_FS['edge_d.03']
        self.assertEqual(len(edge03),1)
        rels = edge03[0]['rels']
        self.assertEqual( [d['_id'] for d in rels], [1,6,9,2] )