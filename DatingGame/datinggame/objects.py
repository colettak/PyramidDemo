"""
Basic objects to be mapped from the database

"""

class User(object):
  
    def __init__(self, username, firstname, lastname, traits=[], likes=[]):
        self.username = username
        self.firstname = firstname
        self.lastname = lastname
        self.traits = traits
        self.likes = likes

    def returndict(self):
        return dict(
            username = self.username,
            firstname = self.firstname,
            lastname = self.lastname,
            traits = self.traits,
            likes = self.likes
        )
        

def get_action_urls(action):
    map = {}
    pass