import dash_bootstrap_components as dbc
from dash import dcc


def home_page():
    return dbc.Container(
        [
            dcc.Markdown("## Tmp landing page"),
        ]
    )