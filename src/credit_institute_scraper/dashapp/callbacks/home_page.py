import pandas as pd
from dash import Output, Input, dash_table
from ..dash_app import dash_app as app
from .utils import data_bars_diverging, table_type


@app.callback(Output('data_table_div', 'children'),
              Input('daily_store', 'data'))
def load_home_page_table(df):
    col_name_map = {
        'institute': 'Institute',
        'coupon_rate': 'Coupon',
        'years_to_maturity': 'Maturity',
        'max_interest_only_period': 'IO Years',
        'isin': 'ISIN'
    }

    df = pd.DataFrame(df)
    df = df.dropna()\
        .groupby(['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period', 'isin'])['spot_price']\
        .agg(lambda x: x.iat[-1] - x.iat[0])\
        .round(3)\
        .reset_index(name='Δ Price')
    ascending = True if df['Δ Price'].mean() < 0 else False
    df = df.sort_values(by='Δ Price', ascending=ascending)
    return dash_table.DataTable(id='home_page_table',
                                data=df.to_dict('records'),
                                sort_action='native',
                                columns=[{'name': col_name_map.get(i, i), 'id': i, 'type': table_type(df[i])} for i in df.columns],
                                style_data_conditional=(
                                    data_bars_diverging(df, 'Δ Price', zero_mid=True)
                                ),
                                style_cell={
                                    'width': '2rem',
                                    'minWidth': '2rem',
                                    'maxWidth': '2rem',
                                    'overflow': 'hidden',
                                    'textOverflow': 'ellipsis',
                                },
                                page_size=20,
                                filter_action='native',
                                )
