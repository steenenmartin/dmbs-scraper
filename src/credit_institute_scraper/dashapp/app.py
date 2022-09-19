import dash
import dash_bootstrap_components as dbc

dash_app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
dash_app.title = 'Credit Institute Scraper'