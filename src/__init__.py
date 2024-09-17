from flask import Flask, Request
from dynaconf import FlaskDynaconf
from flasgger import Swagger
from flask_cors import CORS
from sentry_sdk import init

class ProxiedRequest(Request):
    def __init__(self, environ, populate_request=True, shallow=False):
        super(Request, self).__init__(environ, populate_request, shallow)
        # Support SSL termination. Mutate the host_url within Flask to use https://
        # if the SSL was terminated.
        x_forwarded_proto = self.headers.get('X-Forwarded-Proto')
        if  x_forwarded_proto == 'https':
            self.url = self.url.replace('http://', 'https://')
            self.host_url = self.host_url.replace('http://', 'https://')
            self.base_url = self.base_url.replace('http://', 'https://')
            self.url_root = self.url_root.replace('http://', 'https://')

init(
    dsn="https://add731144a98d9aa29313ca7b51b2e05@o4504096348438528.ingest.us.sentry.io/4507157353594880",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)
app = Flask(__name__, template_folder="../templates")
CORS(app, supports_credentials=True)

flask_conf = FlaskDynaconf(
    app,
    settings_files=["settings.yaml", ".secrets.yaml"],
)
app.request_class = ProxiedRequest
swagger = Swagger(app)

from src import routes
from src.settings import *
