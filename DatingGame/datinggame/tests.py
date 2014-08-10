import unittest
from pyramid import testing

class ViewTests(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    def test_my_view(self):
        from datinggame.views import login
        request = testing.DummyRequest()
        info = login(request)
        self.assertEqual(info['project'], 'DatingGame')
