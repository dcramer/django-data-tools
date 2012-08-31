import sys

from django.contrib.auth.models import User
from django.test import TestCase
from datatools.query.range import RangeQuerySetWrapper


class QueryTest(TestCase):
    def setUp(self):
        for n in xrange(3):
            User.objects.create(username=n, email='%s@example.com' % n)

    def test_simple(self):
        # number of iterations +  1 for empty result set
        seen = set()
        with self.assertNumQueries(4):
            last = 0
            for x, n in enumerate(RangeQuerySetWrapper(User.objects.all(), step=1)):
                self.assertTrue(n.id not in seen)
                seen.add(n.id)
                self.assertTrue(n.id > last)
                last = n.id

    def test_stepping(self):
        # number of iterations + 1 for empty result set
        seen = set()
        with self.assertNumQueries(2):
            last = 0
            for x, n in enumerate(RangeQuerySetWrapper(User.objects.all(), step=3)):
                self.assertTrue(n.id not in seen)
                seen.add(n.id)
                self.assertTrue(n.id > last)
                last = n.id

    def test_order_by(self):
        # number of iterations + 1 for empty result set
        seen = set()
        with self.assertNumQueries(2):
            last = None
            for x, n in enumerate(RangeQuerySetWrapper(User.objects.all(), order_by='date_joined')):
                self.assertTrue(n.id not in seen)
                seen.add(n.id)
                if last:
                    self.assertTrue(n.date_joined > last)
                last = n.date_joined

    def test_with_callbacks(self):
        def add_crud(r):
            r.crud = r.id

        # number of iterations + 1 for empty result set
        seen = set()
        with self.assertNumQueries(4):
            for x, n in enumerate(RangeQuerySetWrapper(User.objects.all(), step=1, callbacks=[
                    lambda x: [add_crud(r) for r in x]
                ])):
                self.assertEquals(getattr(n, 'crud', None), n.id)
                self.assertTrue(n.id not in seen)
                seen.add(n.id)

    def test_reverse_no_matches(self):
        self.assertEquals(len(list(RangeQuerySetWrapper(User.objects.filter(id=9000), step=-1))), 0)

    def test_reverse(self):
        # number of iterations +  1 for empty result set
        seen = set()
        with self.assertNumQueries(4):
            last = sys.maxint
            for x, n in enumerate(RangeQuerySetWrapper(User.objects.all(), step=-1)):
                self.assertTrue(n.id not in seen)
                seen.add(n.id)
                self.assertTrue(n.id < last)
                last = n.id

    def test_reverse_stepping(self):
        # number of iterations + 1 for empty result set
        seen = set()
        with self.assertNumQueries(2):
            last = sys.maxint
            for x, n in enumerate(RangeQuerySetWrapper(User.objects.all(), step=-3)):
                self.assertTrue(n.id not in seen)
                seen.add(n.id)
                self.assertTrue(n.id < last)
                last = n.id
