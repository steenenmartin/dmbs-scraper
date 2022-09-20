import dash_bootstrap_components as dbc
from dash import dcc, html
from .. import styles


def plot_page():
    return dbc.Container(id='daily_plot_container', children=
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
                                                         options=[])
                                        ]
                                    ),
                                    html.Br(),
                                    dbc.Label('Coupon'),
                                    dbc.Card(
                                        [
                                            dcc.Dropdown(id='select_coupon_daily_plot',
                                                         options=[])
                                        ]
                                    ),
                                    html.Br(),
                                    dbc.Label('Years to maturity'),
                                    dbc.Card(
                                        [
                                            dcc.Dropdown(id='select_ytm_daily_plot',
                                                         options=[])
                                        ]
                                    ),
                                    html.Br(),
                                    dbc.Label('Max interest only period'),
                                    dbc.Card(
                                        [
                                            dcc.Dropdown(id='select_max_io_daily_plot',
                                                         options=[])
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
