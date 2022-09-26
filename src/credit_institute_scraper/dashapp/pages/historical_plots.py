import dash_bootstrap_components as dbc
from dash import dcc, html
from .. import styles
from ...utils.server_helper import is_heroku_server
if is_heroku_server():
    from ...database.postgres_conn import query_db
else:
    from ...database.sqlite_conn import query_db


def historical_plot_page():
    return dbc.Container([
        dcc.Store(id='historical_store', data=query_db(sql="select * from ohlc_prices").to_dict('records')),
        dbc.Card(
            [
                dbc.Row(
                    [
                        html.H4(f'Historic prices', className='header__graph'),
                        dbc.Col(
                            [
                                dbc.Label('Institute', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_institute_historical_plot',
                                             options=[],
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Coupon', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_coupon_historical_plot',
                                             options=[],
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Years to maturity', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_ytm_historical_plot',
                                             options=[],
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Max interest-only period', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_max_io_historical_plot',
                                             options=[],
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label("Isin", className='graph-downdown-label'),
                                dcc.Dropdown(id='select_isin_historical_plot',
                                             options=[],
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown')
                            ],
                            md=2
                        ),
                        dbc.Col(
                            dcc.Graph(id='historical_plot',
                                      figure=dict(layout=styles.HISTORICAL_GRAPH_STYLE),
                                      style={'height': '92vh'},
                                      config={'displayModeBar': False}),
                            md=10
                        ),
                    ],
                    **styles.ROW_STYLE
                ),
            ], className='graph__container'
        ),
    ],
)
