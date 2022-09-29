import dash_bootstrap_components as dbc
from dash import html


def home_page():
    return dbc.Container(
        [
            html.H3("Welcome to bond stats"),
            html.Div(
                [
                    html.P("This table shows the cumulative change for all bonds during latest business day"),
                    html.Div(children=[html.Small("To filter numerical columns, prepend with either "),
                                       html.Code('=', className='code-container'),
                                       html.Small(', '),
                                       html.Code('>', className='code-container'),
                                       html.Small(' or '),
                                       html.Code('<', className='code-container'),
                                       html.Small(" e.g. you could filter the Coupon column by writing "),
                                       html.Code('>0.5', className='code-container')]),
                    html.Div(id='data_table_div', style={'margin-top': '1rem'})
                ], style={'width': '55rem'}),
        ]
    )
