from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, email, name, password):
        self.id = email
        self.email = email
        self.name = name
        self.password = password