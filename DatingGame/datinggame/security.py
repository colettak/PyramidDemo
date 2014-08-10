"""Placeholder module for authentication"""

import bcrypt

USERS = {'manager':'manager',
          'viewer':'viewer'
		  }

GROUPS = {'manager':['group:managers'],
          'viewer':['group:users']
          }

def groupfinder(userid, request):
    if userid in USERS:
        return GROUPS.get(userid, [])

def _hash_pw(pw):
    """ Hash a plaintext using bcrypt """
    return bcrypt.hashpw(pw, bcrypt.gensalt())

def _check_pw(plaintext, hashed):
    """ Check a plaintext password against a bcrypt hash """
    return bcrypt.hashpw(plaintext, hashed) == hashed
