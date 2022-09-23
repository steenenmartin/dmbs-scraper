from . import styles
import dash_bootstrap_components as dbc
from dash import html, dcc

sidebar = html.Div(
    [
        html.H3("Bond stats", className="app__header"),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/", active="exact"),
                dbc.NavLink("Daily changes", href="/daily", active="exact")
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=styles.SIDEBAR_STYLE
)

content = html.Div(id="page-content", style=styles.CONTENT_STYLE)
layout = html.Div([dcc.Location(id="url"), sidebar, content])
