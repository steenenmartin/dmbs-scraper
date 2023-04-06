import pandas as pd
from dash import Output, Input, dash_table, html
from ..dash_app import dash_app as app
from .utils import data_bars_diverging, table_type


# @app.callback(Output('data_table_div', 'children'),
#               Input('spot_prices_store', 'data'),
#               Input('master_data', 'data'))
# def load_home_page_table(spot_prices, master_data):
#     col_name_map = {
#         'institute': 'Institute',
#         'coupon_rate': 'Coupon',
#         'years_to_maturity': 'Maturity',
#         'max_interest_only_period': 'IO Years',
#         'isin': 'ISIN'
#     }
#
#     spot_prices = pd.DataFrame(spot_prices)
#     active_date = spot_prices['timestamp'].iloc[-1][:10]
#     master_data = pd.DataFrame(master_data)
#     spot_prices = pd.merge(spot_prices, master_data, on="isin")
#
#     spot_prices = spot_prices.dropna() \
#         .groupby(['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period', 'isin']) \
#         .agg(Price=('spot_price', lambda x: x.iat[-1]), p_ch=('spot_price', lambda x: x.iat[-1] - x.iat[0])) \
#         .round(2) \
#         .reset_index() \
#         .rename(columns={'p_ch': 'Δ Price'})
#     spot_prices = spot_prices.sort_values(by='Δ Price', key=lambda x: abs(x), ascending=False)
#     return html.Div(
#         [
#             html.Label(active_date, className='table__header'),
#             dash_table.DataTable(
#                 id='home_page_table',
#                 data=spot_prices.to_dict('records'),
#                 sort_action='native',
#                 columns=[{'name': col_name_map.get(i, i), 'id': i, 'type': table_type(spot_prices[i])} for i in
#                          spot_prices.columns],
#                 style_data_conditional=data_bars_diverging(spot_prices, 'Δ Price', zero_mid=True),
#                 style_cell={
#                     'width': '2rem',
#                     'minWidth': '2rem',
#                     'maxWidth': '2rem',
#                     'overflow': 'hidden',
#                     'textOverflow': 'ellipsis',
#                 },
#                 page_size=20,
#                 filter_action='native',
#                 filter_options={'case': 'insensitive'}
#             )
#         ]
#     )
