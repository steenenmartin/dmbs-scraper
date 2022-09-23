import dash
import dash_bootstrap_components as dbc

dash_app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
dash_app.title = 'Bond stats'
