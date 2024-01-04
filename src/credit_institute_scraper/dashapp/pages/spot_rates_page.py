import dash_bootstrap_components as dbc

from dash import dcc, html
from .. import styles
from ...database.postgres_conn import query_db


def _extract_dropdown(arg_dict, arg, cast=None):
    arglst = arg_dict[arg].split(',') if arg in arg_dict else []
    if cast:
        arglst = list(map(cast, arglst))
    return arglst


def spot_rates_plot_page(dropdown_args):
    return dbc.Container([
        dcc.Loading(type="default", children=html.Div(id="loading-spinner-output-spot-rates"), className='spinner'),
        dcc.Store(id='master_data_float', data=query_db(sql="select * from master_data_float").to_dict('records')),
        dcc.Store(id='spot_rates_store', data=query_db(sql="select * from rates").to_dict('records')),
        dbc.Card(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Br(),
                                dbc.Label('Institute', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_institute_spot_rates_plot',
                                             options=_extract_dropdown(dropdown_args, 'institute'),
                                             value=_extract_dropdown(dropdown_args, 'institute'),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Fixed rate period', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_fixed_rate_period_spot_rates_plot',
                                             options=_extract_dropdown(dropdown_args, 'fixed_rate_period', int),
                                             value=_extract_dropdown(dropdown_args, 'fixed_rate_period', int),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Max interest-only period', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_max_io_spot_rates_plot',
                                             options=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                             value=_extract_dropdown(dropdown_args, 'max_interest_only_period', float),
                                             multi=True,
                                             searchable=False,
                                             className='graph-dropdown')
                            ],
                            md=2
                        ),
                        dbc.Col(
                            dcc.Graph(id='spot_rates_plot',
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
