from pyramid.config import Configurator
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from datinggame.resources import Root
from datinggame.security import groupfinder
from pyramid.events import subscriber
from pyramid.events import NewRequest
from gridfs import GridFS
import pymongo
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.exceptions import NotFound
from pyramid.view import AppendSlashNotFoundViewFactory
from datinggame.views import notfound_view

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    authentication_policy = AuthTktAuthenticationPolicy('lrrrftht', callback=groupfinder)
    authorization_policy = ACLAuthorizationPolicy()

    config = Configurator(authentication_policy=authentication_policy, authorization_policy=authorization_policy, settings=settings, root_factory='datinggame.models.RootFactory')
	
	#set up the database and have it append to each request
    db_uri = settings['db_uri']
    conn = pymongo.Connection(db_uri)
    config.registry.settings['db_conn'] = conn
    config.add_subscriber(add_mongo_db, NewRequest)
	
    config.add_static_view('static', 'datinggame:static', cache_max_age=3600)
	#add the routes here -- they will be specified with a decorator in the views file
    config.add_route('root', '')
    config.add_route('logout', '/logout')
    config.add_route('login', '/login')
    config.add_route('start', '/start')
    config.add_route('signup', '/signup')
    config.add_route('edit','/edit')
    config.add_route('editpicture','/editpicture')
    config.add_route('profilepic','/profilepic/{pic_id}')
    config.add_route('messagethread', '/messages/{username}')
    config.add_route('favicon', "/favicon.ico")
    config.add_route('user', '/{username}')
    
    config.scan()
    return config.make_wsgi_app()

def add_mongo_db(event):
	"""Function for appending the db to each request
	"""
    settings = event.request.registry.settings
    db = settings['db_conn'][settings['db_name']]
	#create set the mongo db and the gridfs instance for file storage
    event.request.db = db
    event.request.fs = GridFS(db)
