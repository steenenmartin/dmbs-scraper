import dash_bootstrap_components as dbc
from dash import html


def page_not_found(pathname):
    return dbc.Card(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P(f"The pathname {pathname} was not recognised..."),
        ]
    )