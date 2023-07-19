from dash import html, dcc
import dash_bootstrap_components as dbc
from .. import styles


def _extract_dropdown(arg_dict, arg, as_str=False):
    default = '' if as_str else []
    if arg in arg_dict:
        arglst = arg_dict[arg].split(',')
        if as_str:
            arglst = arglst[0]
    else:
        arglst = default
    return arglst


def spread_plot_page(dropdown_args):
    return dbc.Container([
        dbc.Card([
            dbc.Row([
                dbc.Col([
                    dbc.Label('Base ISIN', className='graph-dropdown-label'),
                    dcc.Dropdown(id='base_isin_spread',
                                 options=_extract_dropdown(dropdown_args, 'base_isin'),
                                 value=_extract_dropdown(dropdown_args, 'base_isin', as_str=True),
                                 multi=False,
                                 searchable=True,
                                 className='graph-dropdown'),
                    html.Br(),
                    dbc.Label('Comparison ISINs', className='graph-dropdown-label'),
                    dcc.Dropdown(id='compare_isins_spread',
                                 options=_extract_dropdown(dropdown_args, 'compare_isins'),
                                 value=_extract_dropdown(dropdown_args, 'compare_isins'),
                                 multi=True,
                                 searchable=True,
                                 className='graph-dropdown')
                ], md=2),
                dbc.Col(
                    dcc.Graph(id='rate_spreads_plot',
                              figure=dict(layout=styles.DAILY_GRAPH_STYLE),
                              style={'height': '92vh'},
                              config={'displayModeBar': False}),
                    md=10
                )
            ], **styles.ROW_STYLE)
        ], className='graph__container')
    ])
