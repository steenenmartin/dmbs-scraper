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
                dbc.NavLink("Daily changes", href="/daily", active="exact"),
                dbc.NavLink("Historical changes", href="/historical", active="exact")
            ],
            vertical=True,
            pills=True,
        ),
        dbc.Button("Hide", outline=True, id="btn_sidebar", className='sidebar-btn')
    ],
    id='sidebar',
    style=styles.SIDEBAR_STYLE
)

content = html.Div(id="page-content", style=styles.CONTENT_STYLE)
layout = html.Div(
    [
        dcc.Store(id='side_click'),
        dcc.Location(id="url", refresh=False),
        sidebar,
        content
     ]
)
