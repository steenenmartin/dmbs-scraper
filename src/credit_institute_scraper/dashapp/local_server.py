from credit_institute_scraper.dashapp.dash_app import dash_app as app
from credit_institute_scraper.dashapp import layout, callbacks
from flask import redirect

app.layout = layout.layout
server = app.server


@server.before_request
def hello():
    return redirect('/')


server.run(port=8080)
