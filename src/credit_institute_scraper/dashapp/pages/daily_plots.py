import dash_bootstrap_components as dbc
from dash import dcc, html
from .. import styles
from ..app_config import app_color


def daily_plot_page():
    return dbc.Container([
        html.H2('Daily change in spot prices'),
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
                                                     options=[],
                                                     **styles.DROPDOWN_STYLE)
                                    ]
                                ),
                                html.Br(),
                                dbc.Label('Coupon'),
                                dbc.Card(
                                    [
                                        dcc.Dropdown(id='select_coupon_daily_plot',
                                                     options=[],
                                                     **styles.DROPDOWN_STYLE)
                                    ]
                                ),
                                html.Br(),
                                dbc.Label('Years to maturity'),
                                dbc.Card(
                                    [
                                        dcc.Dropdown(id='select_ytm_daily_plot',
                                                     options=[],
                                                     **styles.DROPDOWN_STYLE)
                                    ]
                                ),
                                html.Br(),
                                dbc.Label('Max interest only period'),
                                dbc.Card(
                                    [
                                        dcc.Dropdown(id='select_max_io_daily_plot',
                                                     options=[],
                                                     **styles.DROPDOWN_STYLE)
                                    ]
                                ),

                            ],
                            **styles.LEFT_COL_STYLE
                        ),
                        dbc.Col(
                            dcc.Graph(id='daily_plot',
                                      figure=dict(
                                          layout=dict(
                                              plot_bgcolor=app_color['graph_bg'],
                                              paper_bgcolor=app_color['graph_bg'],
                                          )
                                      )),
                            **styles.RIGHT_COL_STYLE
                        ),
                    ],
                    **styles.ROW_STYLE
                ),
            ], style={"border": "none"}
        ),
    ]
)
