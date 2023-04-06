from . import styles
import dash_bootstrap_components as dbc
from dash import html, dcc


sidebar = html.Div(
    [
        html.I(className="app__header",
               style={'background-image': 'url(/assets/favicon.ico)',
                      'padding-top': '100%',
                      'background-size': '100%'}),
        html.H3("Bond stats", className='app__header'),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/", active="exact"),
                dbc.NavLink("Spot prices", href="/prices", active="exact"),
                dbc.NavLink("OHLC prices", href="/ohlc", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
        html.Hr(),
        html.Div(id='uptime_status', style={'margin-top': '2rem'}),
    ],
    id='sidebar',
    style=styles.SIDEBAR_STYLE,
    className='sidebar'
)

stores = [
    dcc.Location(id="url", refresh=False),
    html.Div(id='page-title-output'),
    html.Div(id='dummy1', style={'display': 'none'}),
    html.Div(id='dummy2', style={'display': 'none'}),
    html.Div(id='date_range_div', style={'display': 'none'}),
    dcc.Store(id='spot_prices_store', data=None),
    dcc.Store(id='master_data', data=None),
    dcc.Store(id='side_click'),
    dcc.Interval(id='interval-component', interval=60000, n_intervals=0),
    dcc.Loading(type="default", children=html.Div(id="loading-spinner-output1"), className='spinner'),
]

content = html.Div(id="page-content", style=styles.CONTENT_STYLE)
layout = html.Div(
    [
        *stores,
        dbc.Button(outline=True, id="btn_sidebar", className='sidebar-btn'),
        sidebar,
        content
     ]
)
