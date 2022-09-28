import dash_bootstrap_components as dbc
from dash import html


def home_page():
    return dbc.Container(
        [
            html.H3("Welcome to bond stats"),
            html.P("This table shows the cumulative change for all bonds during latest business day"),
            html.Div(id='data_table_div'),
        ]
    )
