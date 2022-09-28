from credit_institute_scraper.dashapp.dash_app import dash_app as app
from credit_institute_scraper.dashapp import layout, callbacks
from flask_caching import Cache

app.layout = layout.layout
server = app.server
cache = Cache(app.server, config={'CACHE_TYPE': 'simple'})
cache.clear()
server.run(port=8080)
