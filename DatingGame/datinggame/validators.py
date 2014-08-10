'''
Created on Sep 13, 2011
Module for validating form inputs

@author: kcoletta
'''
import colander



@colander.deferred
def username_validator(node, kw):
    regex = r'^[A-Za-z](?=[A-Za-z0-9_.]{3,31}$)[a-zA-Z0-9_]*\.?[a-zA-Z0-9_]*$'
    msg = "Username must be 4 to 32 characters and start with a letter. You may use letters, numbers, underscores, and one dot (.)"

    db = kw.get('db')
    username = kw.get('username')
    assert db
    regex_validator = colander.Regex(regex, msg=msg)
    regex_validator(node, username)
    if db.users.find_one({"username":username}):
        raise colander.Invalid(node, "Username %s is in use" % username)
    