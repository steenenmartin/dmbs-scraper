import dash_bootstrap_components as dbc
from dash import html


def home_page():

    return dbc.Container(
        [
            html.H3("Welcome to bond stats"),
            html.P("The landing page is under development - Come back for updates soon!")
        ]
    )