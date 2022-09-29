import dash_bootstrap_components as dbc
from dash import dcc, html
from .. import styles
from ...database.postgres_conn import query_db


def _extract_var(dct, var_name, to_options, cast=None):
    out = dct.get(var_name)
    if cast and out is not None:
        out = cast(out)
    if to_options:
        out = [] if out is None else [out]
    return out


def historical_plot_page(dropdown_args):
    return dbc.Container([
        dcc.Store(id='historical_store', data=query_db(sql="select * from ohlc_prices").to_dict('records')),
        dbc.Card(
            [
                dbc.Row(
                    [
                        html.H4(f'Historic prices', className='header__graph'),
                        dbc.Col(
                            [
                                html.H5("Select all"),
                                dbc.Label('Institute', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_institute_historical_plot',
                                             options=_extract_var(dropdown_args, 'institute', str),
                                             value=_extract_var(dropdown_args, 'institute', str),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Coupon', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_coupon_historical_plot',
                                             options=_extract_var(dropdown_args, 'coupon_rate', float),
                                             value=_extract_var(dropdown_args, 'coupon_rate', float),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Years to maturity', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_ytm_historical_plot',
                                             options=_extract_var(dropdown_args, 'years_to_maturity', int),
                                             value=_extract_var(dropdown_args, 'years_to_maturity', int),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Max interest-only period', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_max_io_historical_plot',
                                             options=_extract_var(dropdown_args, 'max_interest_only_period', float),
                                             value=_extract_var(dropdown_args, 'max_interest_only_period', float),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                html.H5("Or select"),
                                dbc.Label("Isin", className='graph-downdown-label'),
                                dcc.Dropdown(id='select_isin_historical_plot',
                                             options=_extract_var(dropdown_args, 'isin', True),
                                             value=_extract_var(dropdown_args, 'isin', False),
                                             searchable=True,
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
