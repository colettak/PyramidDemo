from pyramid.security import Allow
from pyramid.security import Everyone

class RootFactory(object):
    __acl__ = [ (Allow, 'group:managers', 'manage'),
                (Allow, 'group:users', 'view') ]
    def __init__(self, request):
        pass



