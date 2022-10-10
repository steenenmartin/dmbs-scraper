from datetime import datetime, timedelta

import pandas as pd
from dash import Output, Input, dash_table, html
from ..dash_app import dash_app as app
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

    spot_prices = pd.DataFrame(spot_prices)
    active_date = spot_prices['timestamp'].iloc[-1][:10]
    master_data = pd.DataFrame(master_data)
    spot_prices = pd.merge(spot_prices, master_data, on="isin")

    spot_prices = spot_prices.dropna() \
        .groupby(['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period', 'isin']) \
        .agg(Price=('spot_price', lambda x: x.iat[-1]), p_ch=('spot_price', lambda x: x.iat[-1] - x.iat[0])) \
        .round(2) \
        .reset_index() \
        .rename(columns={'p_ch': 'Δ Price'})
    ascending = True if spot_prices['Δ Price'].mean() < 0 else False
    spot_prices = spot_prices.sort_values(by='Δ Price', ascending=ascending)
    return html.Div(
        [
            html.Label(active_date, className='table__header'),
            dash_table.DataTable(
                id='home_page_table',
                data=spot_prices.to_dict('records'),
                sort_action='native',
                columns=[{'name': col_name_map.get(i, i), 'id': i, 'type': table_type(spot_prices[i])} for i in
                         spot_prices.columns],
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
        ]
    )


@app.callback(Output('status_table_div', 'children'),
              Input('daily_store', 'data'),
              Input('master_data', 'data'))
def load_status_table(spot_prices, master_data):
    col_name_map = {
        'institute': 'Institute',
        'latest_data': 'Latest data',
        'status': 'Status',
    }
    spot_prices = pd.DataFrame(spot_prices)
    spot_prices['timestamp'] = pd.to_datetime(spot_prices['timestamp'])

    master_data = pd.DataFrame(master_data)
    spot_prices = pd.merge(spot_prices, master_data, on="isin").sort_values('timestamp')
    spot_prices['timestamp'] = pd.to_datetime(spot_prices['timestamp'])

    institutes = set(master_data['institute'].values)

    def status(timestamp):
        now = datetime.utcnow()
        if timestamp is None:
            return "No data today"
        if 15 < now.hour or now.hour < 7:
            return "Exchange closed"
        elif now - timedelta(minutes=5) > timestamp:
            return "Not OK"
        else:
            return "OK"

    latest_data_per_institute = pd.DataFrame()
    for institute in institutes:
        institute_prices = spot_prices[spot_prices['institute'] == institute]
        latest_institute_data_timestamp = None if institute_prices.empty else institute_prices['timestamp'].iloc[-1]

        latest_institute_data_df = pd.DataFrame(columns=["institute", "latest_data", "status"])
        latest_institute_data_df.loc[0] = [
            institute,
            latest_institute_data_timestamp,
            status(latest_institute_data_timestamp)
        ]
        latest_data_per_institute = pd.concat([latest_data_per_institute, latest_institute_data_df])

    latest_data_per_institute['latest_data'] = latest_data_per_institute['latest_data'].dt.tz_localize('UTC').dt.tz_convert('Europe/Copenhagen').dt.strftime('%Y-%m-%d %H:%M:%S')

    return html.Div(
        [
            dash_table.DataTable(
                id='status_page_table',
                data=latest_data_per_institute.to_dict('records'),
                columns=[{'name': col_name_map.get(i, i), 'id': i, 'type': table_type(latest_data_per_institute[i])} for i in latest_data_per_institute.columns],
                page_size=20
            )
        ]
    )
