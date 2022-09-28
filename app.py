from src.credit_institute_scraper.dashapp.dash_app import dash_app as app
from src.credit_institute_scraper.dashapp import layout, callbacks
import logging


app.layout = layout.layout
server = app.server
logging.getLogger('werkzeug').setLevel(logging.ERROR)


