import dash_bootstrap_components as dbc
from dash import dcc, html
from ...database.postgres_conn import query_db
from .. import styles


def daily_plot_page(date):
    return dbc.Container([
        dcc.Store(id='daily_store', data=query_db(sql="select * from prices where date(timestamp) = :date",
                                                  params={'date': date}).to_dict("records")),
        dbc.Card(
            [
                dbc.Row(
                    [
                        html.H4(f'{date.isoformat()}: Daily change in spot prices', className='header__graph'),
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
                            width={"size": 2}
                        ),
                        dbc.Col(
                            dcc.Graph(id='daily_plot',
                                      figure=dict(
                                          layout=styles.GRAPH_STYLE
                                      ),
                                      style={'height': '95vh'}),
                            width={"size": 10}
                        ),
                    ],
                    **styles.ROW_STYLE
                ),
            ], className='graph__container'
        ),
    ],
)
