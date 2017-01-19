from . import handlers
from asyncbb.web import Application
from tokenservices.handlers import GenerateTimestamp

urls = [
    (r"^/v1/timestamp/?$", GenerateTimestamp),
    (r"^/v1/user/?$", handlers.UserCreationHandler),
    (r"^/v1/user/(?P<username>[^/]+)/?$", handlers.UserHandler),
    (r"^/v1/search/user/?$", handlers.SearchUserHandler)
]

def main():
    app = Application(urls)
    app.start()
