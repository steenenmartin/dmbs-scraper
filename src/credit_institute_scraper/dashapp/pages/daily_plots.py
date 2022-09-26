import dash_bootstrap_components as dbc
from dash import dcc, html
from .. import styles


def _extract_dropdown(arg_dict, arg, cast=None):
    arglst = arg_dict[arg].split(',') if arg in arg_dict else []
    if cast:
        arglst = list(map(cast, arglst))
    return arglst


def daily_plot_page(date, dropdown_args):
    return dbc.Container([
        dcc.Store(id='daily_store', data=None),
        dcc.Interval(id='interval-component',  interval=60000, n_intervals=0),
        dbc.Card(
            [
                dbc.Row(
                    [
                        html.H4(f'{date.isoformat()}: Daily change in spot prices', className='header__graph'),
                        dbc.Col(
                            [
                                dbc.Label('Institute', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_institute_daily_plot',
                                             options=_extract_dropdown(dropdown_args, 'institute'),
                                             value=_extract_dropdown(dropdown_args, 'institute'),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Coupon', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_coupon_daily_plot',
                                             options=_extract_dropdown(dropdown_args, 'coupon_rate', float),
                                             value=_extract_dropdown(dropdown_args, 'coupon_rate', float),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Years to maturity', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_ytm_daily_plot',
                                             options=_extract_dropdown(dropdown_args, 'years_to_maturity', int),
                                             value=_extract_dropdown(dropdown_args, 'years_to_maturity', int),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Max interest-only period', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_max_io_daily_plot',
                                             options=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                             value=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label("Isin", className='graph-downdown-label'),
                                dcc.Dropdown(id='select_isin_daily_plot',
                                             options=_extract_dropdown(dropdown_args, 'isin'),
                                             value=_extract_dropdown(dropdown_args, 'isin'),
                                             multi=True,
                                             searchable=True,
                                             className='graph-dropdown')
                            ],
                            md=2
                        ),
                        dbc.Col(
                            dcc.Graph(id='daily_plot',
                                      figure=dict(
                                          layout=styles.DAILY_GRAPH_STYLE
                                      ),
                                      style={'height': '92vh'}),
                            md=10
                        ),
                    ],
                    **styles.ROW_STYLE
                ),
            ], className='graph__container'
        ),
    ],
)
