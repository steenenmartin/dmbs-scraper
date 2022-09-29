import dash_bootstrap_components as dbc
from dash import dcc, html
from .. import styles
from ...database.postgres_conn import query_db


def _extract_dropdown(arg_dict, arg, cast=None):
    arglst = arg_dict[arg].split(',') if arg in arg_dict else []
    if cast:
        arglst = list(map(cast, arglst))
    return arglst


def isin_finder_page(dropdown_args):
    return dbc.Container([
        dcc.Store(id='isin_finder_store', data=query_db(sql="select * from ohlc_prices").to_dict('records')),
        dbc.Card(
            [
                html.Div(
                    dbc.Row(
                        [
                            html.H4('Filter as desired to find your ISIN(s)', className='header__graph'),
                            html.Br(),
                            html.Br(),
                            html.Br(),
                            html.Br(),
                            html.Br(),

                            dbc.Label('Institute', className='graph-downdown-label'),
                            dcc.Dropdown(id='select_institute_isin_finder',
                                         options=_extract_dropdown(dropdown_args, 'institute'),
                                         value=_extract_dropdown(dropdown_args, 'institute'),
                                         multi=False,
                                         searchable=False,
                                         className='graph-dropdown'),
                            html.Br(),
                            dbc.Label('Coupon', className='graph-downdown-label'),
                            dcc.Dropdown(id='select_coupon_isin_finder',
                                         options=_extract_dropdown(dropdown_args, 'coupon_rate', float),
                                         value=_extract_dropdown(dropdown_args, 'coupon_rate', float),
                                         multi=False,
                                         searchable=False,
                                         className='graph-dropdown'),
                            html.Br(),
                            dbc.Label('Years to maturity', className='graph-downdown-label'),
                            dcc.Dropdown(id='select_ytm_isin_finder',
                                         options=_extract_dropdown(dropdown_args, 'years_to_maturity', int),
                                         value=_extract_dropdown(dropdown_args, 'years_to_maturity', int),
                                         multi=False,
                                         searchable=False,
                                         className='graph-dropdown'),
                            html.Br(),
                            dbc.Label('Max interest-only period', className='graph-downdown-label'),
                            dcc.Dropdown(id='select_max_io_isin_finder',
                                         options=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                         value=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                         multi=False,
                                         searchable=False,
                                         className='graph-dropdown'),
                            html.Br(),
                            dbc.Label("Isin(s)", className='graph-downdown-label'),
                            dcc.Textarea(id='isin_finder_isins')
                        ],
                        **styles.ROW_STYLE
                    ),
                    style={'width': '40vh'}
                )
            ],
            className='graph__container',
            style={
                'width': '41vh',
                'height': '50vh'
            }
        ),
    ],
)
