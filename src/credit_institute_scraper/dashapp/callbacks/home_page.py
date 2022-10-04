import pandas as pd
from dash import Output, Input, dash_table, State
from ..dash_app import dash_app as app
from ...database.postgres_conn import query_db
from .utils import data_bars_diverging, table_type


@app.callback(Output('data_table_div', 'children'),
              Input('daily_store', 'data'),
              Input('master_data', 'data'))
def load_home_page_table(spot_prices, master_data):
    col_name_map = {
        'institute': 'Institute',
        'coupon_rate': 'Coupon',
        'years_to_maturity': 'Maturity',
        'max_interest_only_period': 'IO Years',
        'isin': 'ISIN'
    }

    spot_prices = pd.DataFrame(spot_prices).merge(pd.DataFrame(master_data), on='isin')

    spot_prices = spot_prices.dropna()\
        .groupby(['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period', 'isin'])['spot_price']\
        .agg(lambda x: x.iat[-1] - x.iat[0])\
        .round(3)\
        .reset_index(name='Δ Price')
    ascending = True if spot_prices['Δ Price'].mean() < 0 else False
    spot_prices = spot_prices.sort_values(by='Δ Price', ascending=ascending)
    return dash_table.DataTable(id='home_page_table',
                                data=spot_prices.to_dict('records'),
                                sort_action='native',
                                columns=[{'name': col_name_map.get(i, i), 'id': i, 'type': table_type(spot_prices[i])} for i in spot_prices.columns],
                                style_data_conditional=(
                                    data_bars_diverging(spot_prices, 'Δ Price', zero_mid=True)
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


# @app.callback(Output('offer_prices_table_div', 'children'),
#               Input('master_data', 'data'),
#               State('date_range_riv', 'children')
#               )
# def offer_price_table(master_data, date_range):
#     offers = query_db("select * from offer_pricez").merge(pd.DataFrame(master_data), on='isin')
#
#     return dash_table.DataTable(id='offer_prices_table',
#                                 data=offers.to_dict('records'),
#                                 columns=[{'name': i, 'id': i} for i in offers.columns],
#                                 style_cell={
#                                     'width': '2rem',
#                                     'minWidth': '2rem',
#                                     'maxWidth': '2rem',
#                                     'overflow': 'hidden',
#                                     'textOverflow': 'ellipsis',
#                                 },
#                                 page_size=20,
#                                 filter_action='native')
