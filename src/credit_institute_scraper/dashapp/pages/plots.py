import dash_bootstrap_components as dbc
from dash import dcc, html
from .. import styles


def plot_page():
    return dbc.Container(
        [
            dbc.Card(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label('Institute'),
                                    dbc.Card(
                                        [
                                            dcc.Dropdown(id='select_institute_daily_plot',
                                                         options=[{'label': v, 'value': v} for v in ['Jyske', 'Nordea', 'RealKreditDanmark', 'TotalKredit']])
                                        ]
                                    ),
                                    html.Br(),
                                    dbc.Label('Coupon'),
                                    dbc.Card(
                                        [
                                            dcc.Dropdown(id='select_coupon_daily_plot',
                                                         options=[{'label': v, 'value': v} for v in [-0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]])
                                        ]
                                    ),
                                    html.Br(),
                                    dbc.Label('Years to maturity'),
                                    dbc.Card(
                                        [
                                            dcc.Dropdown(id='select_ytm_daily_plot',
                                                         options=[{'label': v, 'value': v} for v in
                                                                  [0, 10, 15, 20, 30]])
                                        ]
                                    ),
                                    html.Br(),
                                    dbc.Label('Max interest only period'),
                                    dbc.Card(
                                        [
                                            dcc.Dropdown(id='select_max_io_daily_plot',
                                                         options=[{'label': v, 'value': v} for v in
                                                                  [0.0, 10.0, 29.75, 30.0, 40.0, 119.0, 120.0]])
                                        ]
                                    ),

                                ],
                                **styles.LEFT_COL_STYLE
                            ),
                            dbc.Col(
                                dcc.Graph(id='daily_plot'),
                                **styles.RIGHT_COL_STYLE
                            ),
                        ],
                        **styles.ROW_STYLE
                    ),
                ],
            ),
        ]
    )
