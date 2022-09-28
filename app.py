from src.credit_institute_scraper.dashapp.dash_app import dash_app as app
from src.credit_institute_scraper.dashapp import layout, callbacks


app.layout = layout.layout
server = app.server
