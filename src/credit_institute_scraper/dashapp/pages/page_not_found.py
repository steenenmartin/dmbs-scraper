import dash_bootstrap_components as dbc
from dash import html


def page_not_found(href: str):
    return dbc.Container(
        [
            html.H2("404: Not found", className="text-danger"),
            html.Hr(),
            html.H5(f'The url "{href}" was not recognised...'),
        ]
    )
