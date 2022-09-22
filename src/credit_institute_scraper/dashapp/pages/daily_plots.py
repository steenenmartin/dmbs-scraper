import dash_bootstrap_components as dbc
from dash import dcc, html
from ...database.sqlite_conn import query_db
from .. import styles


def daily_plot_page(date):
    return dbc.Container([
        # html.H2('Daily change in spot prices'),
        dcc.Store(id='daily_store', data=query_db(sql="select * from prices where date(timestamp) = :date",
                                                  params={'date': date}).to_dict("records")),
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
                                                     multi=True,
                                                     **styles.DROPDOWN_STYLE)
                                    ]
                                ),
                                html.Br(),
                                dbc.Label('Coupon'),
                                dbc.Card(
                                    [
                                        dcc.Dropdown(id='select_coupon_daily_plot',
                                                     options=[],
                                                     multi=True,
                                                     **styles.DROPDOWN_STYLE)
                                    ]
                                ),
                                html.Br(),
                                dbc.Label('Years to maturity'),
                                dbc.Card(
                                    [
                                        dcc.Dropdown(id='select_ytm_daily_plot',
                                                     options=[],
                                                     multi=True,
                                                     **styles.DROPDOWN_STYLE)
                                    ]
                                ),
                                html.Br(),
                                dbc.Label('Max interest only period'),
                                dbc.Card(
                                    [
                                        dcc.Dropdown(id='select_max_io_daily_plot',
                                                     options=[],
                                                     multi=True,
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
                                              plot_bgcolor=styles.app_color['graph_bg'],
                                              paper_bgcolor=styles.app_color['graph_bg'],
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
