import dash_bootstrap_components as dbc
import dash_daq as daq

from dash import dcc, html
from .. import styles


def _extract_dropdown(arg_dict, arg, cast=None):
    arglst = arg_dict[arg].split(',') if arg in arg_dict else []
    if cast:
        arglst = list(map(cast, arglst))
    return arglst


def spot_prices_plot_page(dropdown_args):
    return dbc.Container([
        dbc.Card(
            [
                dcc.Store(id='historic_data_store'),
                dcc.Loading(type="default", children=html.Div(id="loading-spinner-output2"), className='spinner'),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                daq.BooleanSwitch(
                                    label="Show historic prices",
                                    on=_extract_dropdown(dropdown_args, 'show_historic') == ['True'],
                                    color='green',
                                    id="show_historic"
                                ),
                                html.Br(),
                                dbc.Label('Institute', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_institute_spot_prices_plot',
                                             options=_extract_dropdown(dropdown_args, 'institute'),
                                             value=_extract_dropdown(dropdown_args, 'institute'),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Coupon', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_coupon_spot_prices_plot',
                                             options=_extract_dropdown(dropdown_args, 'coupon_rate', float),
                                             value=_extract_dropdown(dropdown_args, 'coupon_rate', float),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Years to maturity', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_ytm_spot_prices_plot',
                                             options=_extract_dropdown(dropdown_args, 'years_to_maturity', int),
                                             value=_extract_dropdown(dropdown_args, 'years_to_maturity', int),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Max interest-only period', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_max_io_spot_prices_plot',
                                             options=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                             value=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label("Isin", className='graph-downdown-label'),
                                dcc.Dropdown(id='select_isin_spot_prices_plot',
                                             options=_extract_dropdown(dropdown_args, 'isin'),
                                             value=_extract_dropdown(dropdown_args, 'isin'),
                                             multi=True,
                                             searchable=True,
                                             className='graph-dropdown')
                            ],
                            md=2
                        ),
                        dbc.Col(
                            dcc.Graph(id='spot_prices_plot',
                                      figure=dict(layout=styles.DAILY_GRAPH_STYLE),
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
