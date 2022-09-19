import dash_bootstrap_components as dbc
from dash import dcc
from .. import styles


def plot_page():
    return dbc.Container(
        [
            dbc.Card(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label('Plot 1'),
                                    dbc.Card(
                                        [
                                            dbc.RadioItems(id='select_institute_daily_plot',
                                                           options=[{'label': v, 'value': v} for v in ['Jyske', 'Nordea', 'RealKreditDanmark', 'TotalKredit']],
                                                           value='Jyske',
                                                           **styles.LIST_STYLE
                                                           ),
                                        ]
                                    ),
                                ],
                                **styles.LEFT_COL_STYLE
                            ),
                            dbc.Col(
                                dcc.Graph(id='daily_plot'),
                                **styles.RIGHT_COL_STYLE
                            ),
                        ],
                        **styles.ROW_STYLE
                    ),
                ],
            ),
        ]
    )