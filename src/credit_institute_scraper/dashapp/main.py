from credit_institute_scraper.dashapp.app import dash_app
from credit_institute_scraper.dashapp import styles, callbacks
import dash_bootstrap_components as dbc
from dash import html, dcc

sidebar = html.Div(
    [
        html.H3("Cool beans", className="app__header"),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/", active="exact"),
                dbc.NavLink("Plots", href="/Plots", active="exact")
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=styles.SIDEBAR_STYLE
)

content = html.Div(id="page-content", style=styles.CONTENT_STYLE)
dash_app.layout = html.Div([dcc.Location(id="url"), sidebar, content])


if __name__ == '__main__':
    dash_app.run_server(port=8888)
