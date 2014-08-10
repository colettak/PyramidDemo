"""
This module handles all the 

"""

from pyramid.view import view_config
from pyramid.response import Response
from pyramid.renderers import get_renderer
from pyramid.security import remember, forget, authenticated_userid
from pyramid.httpexceptions import HTTPFound, HTTPNotFound, HTTPForbidden
import os
from deform import ValidationFailure
from deform import Form
from deform import widget
from deform import FileData
from deform import Set
from deform.interfaces import FileUploadTempStore 
import colander
import peppercorn
import validators
from pymongo.errors import DuplicateKeyError
from pymongo.objectid import ObjectId
from security import _check_pw, _hash_pw, USERS
from gridfs import GridFS

#temporary hardcoded variables, move these to a better place
looking_fors =(('love', "Love"), ('friends', 'Friends'), ('fun','Fun'))
interests = (('men', 'Men'), ('women', 'Women'))
username_regex = r'^[A-Za-z](?=[A-Za-z0-9_.]{3,31}$)[a-zA-Z0-9_]*\.?[a-zA-Z0-9_]*$'
msg = "Username must be 4 to 32 characters and start with a letter. You may use letters, numbers, underscores, and one dot (.)"
ages = [[x,x] for x in range(1,130)]
tmpstore = FileUploadTempStore()

"""Schemas used to create and validate forms"""
#TODO: move these to a separate module

class SignupSchema(colander.MappingSchema):
	"""
	Signup form schema for creation and validation.
	"""
    username = colander.SchemaNode(colander.String(),
        validator=colander.Regex(usernameregex, msg))
    firstname = colander.SchemaNode(colander.String())
    lastname = colander.SchemaNode(colander.String())
    password = colander.SchemaNode(colander.String(),
                                validator=colander.Length(min=5, max=100),
                                widget=widget.CheckedPasswordWidget(size=20),
                                description='Enter a password')
    email = colander.SchemaNode(colander.String(),
                                validator=colander.Email())
    gender = colander.SchemaNode(colander.String(),
                                 widget=widget.RadioChoiceWidget(values=(('male', 'Male'), ('female', 'Female'),('other', 'Other'))),
                                 title='Choose your gender',
                                 description='Select a gender',
                                 validator=colander.OneOf(('male', 'female', 'other')))
    interestedin = colander.SchemaNode(Set(),
                                 widget=widget.CheckboxChoiceWidget(values=(('men', 'Men'), ('women', 'Women'))))
    lookingfor =colander.SchemaNode(Set(),
                                      widget=widget.CheckboxChoiceWidget(values=looking_fors))
    age = colander.SchemaNode(colander.String(),
                              widget=widget.SelectWidget(values=ages))


class EditSchema(colander.MappingSchema):
	"""
	Profile edit schema for form creation and validation.
	"""
    firstname = colander.SchemaNode(colander.String())
    lastname = colander.SchemaNode(colander.String())
    gender = colander.SchemaNode(colander.String(),
                                 widget=widget.RadioChoiceWidget(values=(('male', 'Male'), ('female', 'Female'),('other', 'Other'))),
                                 title='Choose your gender',
                                 description='Select a gender',
                                 validator=colander.OneOf(('male', 'female', 'other')))
    interestedin = colander.SchemaNode(Set(),
                                       widget=widget.CheckboxChoiceWidget(values=interests))
    lookingfor =colander.SchemaNode(Set(),
                                      widget=widget.CheckboxChoiceWidget(values=looking_fors))

    traits = []
    likes = []
    aboutme = colander.SchemaNode(
                colander.String(),
                validator=colander.Length(max=500),
                widget=widget.TextAreaWidget(rows=10, cols=40),
                description='Enter some text')

class EditPictureSchema(colander.MappingSchema):
	"""
	Picture edit schema
	"""
    image = colander.SchemaNode(
                FileData(),
                widget=widget.FileUploadWidget(tmpstore))

class MessageSchema(colander.MappingSchema):
	"""Messaging schema
	"""
    message = colander.SchemaNode(colander.String(),
                                  widget=widget.TextAreaWidget(rows=10, cols=40))

									  
"""Views"""

@view_config(route_name='root', renderer='templates/userhome.pt')
def root(request):
	"""The home page if you are logged in, this route shows a particular user,
	    or returns not found if that user doesn't exist
	"""
    main = get_renderer('templates/main.pt').implementation()
    logged_in = authenticated_userid(request)
    
    actions= [{'url':'editpicture', 'text':'edit picture'},{'url':'edit','text':'edit profile'}]
	#if not logged in, go to the start page
    if (not logged_in):
        location = request.application_url + '/start'
        return HTTPFound(location = location)

    #if you are logged in, show profile
    userinfo =  request.db.users.find_one({"username": logged_in})
    
    #if the user is not in the database
    if not userinfo:
        raise HTTPNotFound('User not available.')
    
    #see if there's a profile picture set, and if not use the default image
    try:
        pic_url = "/profilepic/" + str(userinfo['pic_id'])
    except KeyError, e:
        pic_url = "/static/defaultpic.jpg"
    userinfo.update({'main':main, 'logged_in':logged_in, 'actions':actions, 'pic_url':pic_url})
    return userinfo



@view_config(route_name='start', renderer='templates/start.pt')
def start(request):
	"""The home page if you are not logged in
	"""
    logged_in = authenticated_userid(request)
    main = get_renderer('templates/unlogged.pt').implementation()
    return {'main':main, 'logged_in':logged_in }


@view_config(route_name='edit', renderer='templates/justforms.pt')
def edit(request):
	"""The edit page for your own profile
	"""
    logged_in = authenticated_userid(request)
    main = get_renderer('templates/main.pt').implementation()
    schema = EditSchema()
    myform = Form(schema, buttons=('submit',))
    currentvals = request.db.users.find_one({"username": logged_in})
    actions = [{"text":"back to profile", "url":"/"}]
    
    if 'submit' in request.POST or 'Submit' in request.POST:
        controls = request.POST.items()
		#validate the form
        try:
            validated = myform.validate(controls)
            validated['interestedin']= tuple(validated['interestedin'])
            validated['lookingfor']= tuple(validated['lookingfor'])
        except ValidationFailure, e:
            return {'main':main, 'form':e.render(), 'logged_in':logged_in, 'actions':actions}
        
		#update the database
        db = request.db
        db.users.update( { 'username' : logged_in } , { "$set" : validated } )
        
        return {'main':main, 'form':myform.render(validated),'logged_in':logged_in, 'actions':actions}

    
    
    return {'main':main, 'form':myform.render(currentvals),'logged_in':logged_in, 'actions':actions}


@view_config(route_name='editpicture', renderer='templates/justforms.pt')
def editpicture(request):
	"""The edit page for your profile picture
	"""
    logged_in = authenticated_userid(request)
    main = get_renderer('templates/main.pt').implementation()
    schema = EditPictureSchema()
    myform = Form(schema, buttons=('save',))
    actions = [{"text":"back to profile", "url":"/"}]
    db = request.db
    fs = GridFS(db)
    userinfo =  request.db.users.find_one({"username": logged_in})
	#see if picture is set
    try:
        pic_url = "/profilepic/" + str(userinfo['pic_id'])
    except KeyError, e:
        pic_url = "/static/defaultpic.jpg"
    
    #validate the form if submitted
    if 'save' in request.POST or 'Save' in request.POST:
        controls = request.POST.items()        
        try:
            validatedstuff = myform.validate(controls)
        except ValidationFailure, e:
            return {'main':main, 'form':e.render(), 'logged_in':logged_in, 'actions':actions}
        

        myimage = validatedstuff['image']['fp']
        imageid = fs.put(myimage, content_type="image/jpeg", filename="profilepic.jpg")
        #add imageid to users db 
        db.users.update( { 'username' : logged_in } , { "$set" : { "pic_id" : imageid } } )
        
        
        pic_url = "/profilepic/" + str(imageid)
        
        
        tmpstore.clear()
        return {'main':main, 'pic_url':pic_url,'form':myform.render(),'logged_in':logged_in, 'actions':actions}
    
    return {'main':main, 'form':myform.render(),'logged_in':logged_in, 'actions':actions}

	
@view_config(route_name='messagethread', renderer='templates/messagethread.pt')
def messagethread(request):
    """Basic page for a conversation thread
	"""
    logged_in = authenticated_userid(request)
    userofpage = request.matchdict["username"]
    main = get_renderer('templates/main.pt').implementation()
    schema = MessageSchema()
    myform = Form(schema, buttons=('send',))
    actions = [{"text":"back to messages", "url":"/messages"}]
    db = request.db
    userinfo =  request.db.users.find_one({"username": logged_in})    
    try:
        messages = userinfo['messages']
    except KeyError, e:
        messages = []
    messages = userinfo['messages'][userofpage]

    if 'send' in request.POST or 'Send' in request.POST:
        controls = request.POST.items()        
        try:
            validatedstuff = myform.validate(controls)
        except ValidationFailure, e:
            return {'main':main, 'form':e.render(), 'logged_in':logged_in, 'actions':actions}
        #MOCK DATA
        messageout = {'user':logged_in, 'message':validatedstuff['message']}
        
        #add message to current thread
        #TODO: escape userofpage data / move all database stuff into own module and abstract it more
        db.users.update( { 'username' : logged_in, } , { "$push" : { "messages."+userofpage : messageout } } )
        db.users.update ({ 'username' : userofpage, } , { "$push" : { "messages."+logged_in : messageout} })

        messages.append(messageout)
        return {'main':main, 'messages':messages,'form':myform.render(),'logged_in':logged_in, 'actions':actions}
    
    
    #if you did a get instead of a post
    return {'main':main, 'messages':messages, 'form':myform.render(),'logged_in':logged_in, 'actions':actions}

	
@view_config(route_name='signup', renderer='templates/justforms.pt')
def signup(request):
	"""Sign up form page
	"""
    schema = SignupSchema()
    myform = Form(schema, buttons=('submit',))
    came_from = request.params.get('came_from', '/')
    main = get_renderer('templates/unlogged.pt').implementation()
    logged_in = authenticated_userid(request)   

    if 'submit' in request.POST or 'Submit' in request.POST:
        controls = request.POST.items()
        params = peppercorn.parse(request.POST.items())
        username = params['username']

        #validate form
        try:
            myform.validate(controls)
        except ValidationFailure, e:
            return {'main':main, 'form':e.render(), 'logged_in':logged_in}
        
        login = username
        firstname = params['firstname']
        lastname = params['lastname']
        password = _hash_pw(params['password']['value'])
        email = params['email']
        gender = params['gender']
        lookingfor = params['lookingfor']
        age = params['age']
        likes=[]
        traits=[]
        
        # print request.params
        new_user = {u'username':username, u'firstname':firstname, u'lastname':lastname, u'password':password,u'email':email, u'gender':gender, u'lookingfor':lookingfor,u'age':age, u'likes':likes, 'traits':traits}
        db = request.db

        for user in db.users.find():
            user
        #add the new user to the database
        try:
            db.users.insert(new_user, safe=True)
        except DuplicateKeyError, e:
            return {'main':main, 'form':"Username already in use. Please select another." + myform.render(new_user), 'logged_in':logged_in}
        
        headers = remember(request, login)
        return HTTPFound(location = came_from,
                             headers = headers)

    return {'main':main, 'form':myform.render(), 'logged_in':logged_in}

@view_config(route_name='user', renderer='templates/userhome.pt',  permission='view')
def user(request):
	"""User page
	"""
    logged_in = authenticated_userid(request)
    userofpage = request.matchdict["username"]
    
    #if you are trying to view your own page, redirect home
    if logged_in == userofpage:
        return HTTPFound(location = "/")
		
	#get user info from the database	
    userinfo =  request.db.users.find_one({"username": userofpage})
	
	#if there's no user, 404
    if not userinfo:
        raise HTTPNotFound('bah')
		
	#get the profile picture
    try:
        pic_url = "/profilepic/" + str(userinfo['pic_id'])
    except KeyError, e:
        pic_url = "/static/defaultpic.jpg"
    
    actions = [{'url':'/messages/'+userofpage,'text':'message'}, {'url':'/badges/'+userofpage,'text':'badges'},{'url':'/invite/'+userofpage,'text':'invite to challenge'}]
    main = get_renderer('templates/main.pt').implementation()
    userinfo.update({'main':main, 'logged_in':logged_in, 'actions':actions, 'pic_url':pic_url})
    return userinfo

@view_config(context='pyramid.httpexceptions.HTTPForbidden', renderer='datinggame:templates/login.pt')
@view_config(route_name='login', renderer='templates/login.pt')
def login(request):
	"""Login page. Go here if they hit the log in button or try and view a page they don't have permission to
	"""
    logged_in = False;
    login_url = request.route_url('login')
    referrer = request.url
    if referrer == login_url:
        referrer = '/' # never use the login form itself as came_from
    came_from = request.params.get('came_from', referrer)
    main = get_renderer('templates/unlogged.pt').implementation()
    message = ''
    login = ''
    password = ''
    if 'form.submitted' in request.params:
        login = request.params['login']
        password = request.params['password']
        
        user = request.db.users.find_one({"username": login}, safe=True)

        if user != None:
            hashed = user['password']
        
            if _check_pw(password, hashed ):
                #if USERS.get(login) == password:
                headers = remember(request, login)
                return HTTPFound(location = came_from,
                                 headers = headers)
                
        message = 'Failed login'

    return dict(
        main = main,
        logged_in = logged_in,
        message = message,
        url = request.application_url + '/login',
        came_from = came_from,
        login = login,
        password = password,
        )

@view_config(route_name='logout')
def logout(request):
    headers = forget(request)
    return HTTPFound(location = request.route_url('root'),
                     headers = headers)
    
@view_config(route_name='profilepic')
def profilepic(request):
    logged_in = authenticated_userid(request)
    pid = request.matchdict["pic_id"]
    picid = ObjectId(pid)
    db = request.db
    fs = GridFS(db)
    profilepic = fs.get(picid)
    return Response(content_type='image/jpeg', app_iter=profilepic)

@view_config(context='pyramid.httpexceptions.HTTPNotFound', renderer='datinggame:templates/notfound.pt')
def notfound_view(request):
    logged_in = authenticated_userid(request)   
    actions = None
    main = get_renderer('templates/main.pt').implementation()
    return {'main':main, 'logged_in':logged_in, 'actions':actions }

@view_config(route_name='favicon')
def favicon(request):
    here = os.path.dirname(__file__)
    icon = open(os.path.join(here, 'static', 'favicon.ico'))
    return Response(content_type='image/x-icon', app_iter=icon)

 


