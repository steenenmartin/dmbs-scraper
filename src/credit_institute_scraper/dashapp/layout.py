from . import styles
import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_daq as daq

import pandas as pd
from datetime import datetime, timedelta

from ..database import postgres_conn
from ..enums.credit_insitute import CreditInstitute


def load_status_table(institute: CreditInstitute):
    now = datetime.utcnow()
    today = now.date()

    master_data = postgres_conn.query_db(f"select * from master_data where institute = '{institute.name}'")
    isins = "', '".join(set(master_data['isin']))
    spot_prices = postgres_conn.query_db(f"select * from spot_prices where date(timestamp) = '{today}' and isin in ('{isins}')")
    spot_prices['timestamp'] = pd.to_datetime(spot_prices['timestamp'])

    def status_color(timestamp):
        if timestamp is None:
            return "red"
        if 15 < now.hour or now.hour < 7:
            return "grey"
        elif now - timedelta(minutes=5) > timestamp:
            return "red"
        else:
            return "green"

    latest_institute_data_timestamp = None if spot_prices.empty else spot_prices['timestamp'].iloc[-1]
    return status_color(latest_institute_data_timestamp)


sidebar = html.Div(
    [

        html.I(className="app__header",
               style={'background-image': 'url(/assets/favicon.ico)',
                      'height': '16rem',
                      'background-size': '100%'}),
        html.H3("Bond stats", className='app__header'),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink("Home", href="/", active="exact"),
                dbc.NavLink("Daily changes", href="/daily", active="exact"),
                dbc.NavLink("Historical changes", href="/historical", active="exact"),
                dbc.NavLink("About", href="/about", active="exact")
            ],
            vertical=True,
            pills=True,
        ),
        html.Hr(),
        html.H5("Status", style={'color': "white"}, className='app__header'),
        html.Br(),
        daq.Indicator(
            label=CreditInstitute.RealKreditDanmark.name,
            color=load_status_table(CreditInstitute.RealKreditDanmark),
            style={"color": "white"},
        ),
        html.Br(),
        daq.Indicator(
            label=CreditInstitute.Jyske.name,
            color=load_status_table(CreditInstitute.Jyske),
            style={"color": "white"},
        ),
    ],
    id='sidebar',
    style=styles.SIDEBAR_STYLE,
    className='sidebar'
)


content = html.Div(id="page-content", style=styles.CONTENT_STYLE)
layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id='page-title-output'),
        html.Div(id='dummy1', style={'display': 'none'}),
        html.Div(id='dummy2', style={'display': 'none'}),
        dcc.Store(id='daily_store', data=None),
        dcc.Store(id='master_data', data=None),
        dcc.Interval(id='interval-component', interval=60000, n_intervals=0),
        html.Div(id='date_range_div', style={'display': 'none'}),
        dcc.Loading(type="default", children=html.Div(id="loading-spinner-output1"), className='spinner'),
        dcc.Store(id='side_click'),
        dbc.Button("Hide", outline=True, id="btn_sidebar", className='sidebar-btn'),
        sidebar,
        content
     ]
)
