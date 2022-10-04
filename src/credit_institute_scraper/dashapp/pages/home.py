import dash_bootstrap_components as dbc
from dash import html


def home_page(date_range):
    return dbc.Container(
        [
            html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H3(f"{date_range[-1][:10]}: Cumulative daily changes", className='header__card'),
                                    html.Div(children=[html.Small("To filter numerical columns, prepend with either "),
                                                       html.Code('=', className='code-container'),
                                                       html.Small(', '),
                                                       html.Code('>', className='code-container'),
                                                       html.Small(' or '),
                                                       html.Code('<', className='code-container'),
                                                       html.Small(
                                                           " - e.g. you could filter the Coupon column by writing "),
                                                       html.Code('>0.5', className='code-container')]),
                                    html.Div(id='data_table_div', style={'margin-top': '1rem'})
                                ]
                            ),
                            dbc.Col(
                                [
                                    # html.H3("Offer prices", className='header__card'),
                                    html.Div(id='offer_prices_table_div'),
                                ]
                            )
                        ]
                    )
                ], style={'max-width': '110rem'}),
        ]
    )
