import dash_bootstrap_components as dbc
from dash import dcc


def plot_page():
    return dbc.Container(
        [
            dcc.Markdown("## Tmp plotting page"),
        ]
    )