import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from .. import styles
from ...database.postgres_conn import query_db


def _extract_var(dct, var_name, to_options=False, cast=None):
    out = dct.get(var_name)
    if cast and out is not None:
        out = cast(out)
    if to_options:
        out = [] if out is None else [out]
    return out


def _data_table_arg(dropdown_args):
    out = {}
    if 'isin' in dropdown_args:
        out['data'] = [{'isin': dropdown_args['isin']}]
        out['active_cell'] = {'row': 0, 'column': 0, 'column_id': 'isin'}
    return out


def historical_plot_page(dropdown_args):
    return dbc.Container([
        dcc.Loading(type="default", children=html.Div(id="loading-spinner-output3"), className='spinner'),
        dcc.Store(id='master_data_historic', data=query_db(sql="select * from master_data").to_dict('records')),
        dcc.Store(id='historic_data_store'),
        dbc.Card(
            [
                dbc.Row(
                    [
                        html.H4(f'Historical prices', className='header__graph'),
                        dbc.Col(
                            [
                                html.H6("Filter ISIN list"),
                                dbc.Label('Institute', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_institute_historical_plot',
                                             options=_extract_var(dropdown_args, 'institute', True),
                                             value=_extract_var(dropdown_args, 'institute', False),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Coupon', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_coupon_historical_plot',
                                             options=_extract_var(dropdown_args, 'coupon_rate', True, float),
                                             value=_extract_var(dropdown_args, 'coupon_rate', False, float),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Years to maturity', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_ytm_historical_plot',
                                             options=_extract_var(dropdown_args, 'years_to_maturity', True, int),
                                             value=_extract_var(dropdown_args, 'years_to_maturity', False, int),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                dbc.Label('Max interest-only period', className='graph-downdown-label'),
                                dcc.Dropdown(id='select_max_io_historical_plot',
                                             options=_extract_var(dropdown_args, 'max_interest_only_period', True,
                                                                  float),
                                             value=_extract_var(dropdown_args, 'max_interest_only_period', False,
                                                                float),
                                             multi=False,
                                             searchable=False,
                                             className='graph-dropdown'),
                                html.Br(),
                                html.H6("Select ISIN to plot"),
                                dash_table.DataTable(
                                    id='isin_selector_table',
                                    columns=[{'id': 'isin', 'name': 'ISIN'}],
                                    page_size=6,
                                    tooltip_delay=200,
                                    tooltip_duration=None,
                                    style_cell={'overflow': 'hidden', 'textOverflow': 'ellipsis', 'maxWidth': 0},
                                    css=[{'selector': '.dash-table-tooltip',
                                          'rule': 'background-color: #E8E8C8; '
                                                  'font-family: monospace; '
                                                  'color: #00000;'
                                                  'white-space: pre-line;'}],
                                    **_data_table_arg(dropdown_args)
                                )
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
