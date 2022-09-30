import logging
import pandas as pd
from dash import Output, Input, State
from plotly import graph_objects as go
from .. import styles
from ..dash_app import dash_app as app
from .utils import update_search_bar_template, update_dropdowns
import urllib.parse

from ...database.postgres_conn import query_db


@app.callback(
    Output('dummy2', 'value'),
    Input('select_institute_historical_plot', 'value'),
    Input('select_coupon_historical_plot', 'value'),
    Input("select_ytm_historical_plot", "value"),
    Input("select_max_io_historical_plot", "value"),
    Input('isin_selector_table', 'active_cell'),
    State('url', 'search'),
    State('isin_selector_table', 'data'))
def update_search_bar_historic(institute, coupon_rate, years_to_maturity, max_interest_only_period, active_cell, search, isin_data):
    try:
        isin = None if not isin_data or active_cell is None else isin_data[active_cell['row']]['isin']
    except Exception as e:
        print(e)
        print(isin_data)
        print(active_cell)
    return update_search_bar_template(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, search)


@app.callback([
    Output('select_institute_historical_plot', 'options'),
    Output('select_coupon_historical_plot', 'options'),
    Output('select_ytm_historical_plot', 'options'),
    Output('select_max_io_historical_plot', 'options'),
], Input('master_data', 'data'))
def update_dropdowns_historical_plot(master_data):
    inst, coup, ytm, max_io, _ = update_dropdowns(master_data=master_data, log_text='Updated dropdown labels for historical plot')
    return inst, coup, ytm, max_io


@app.callback(Output("isin_selector_table", "data"),
              Output("isin_selector_table", "active_cell"),
              Output("isin_selector_table", "tooltip_data"),
              [Input('select_institute_historical_plot', 'value'),
               Input('select_coupon_historical_plot', 'value'),
               Input("select_ytm_historical_plot", "value"),
               Input("select_max_io_historical_plot", "value")],
              State('master_data', 'data'),
              State('url', 'search'),
              State('isin_selector_table', 'active_cell'))
def update_isin_selector_table(institute, coupon_rate, years_to_maturity, max_interest_only_period, master_data, search, active_cell):
    isin = dict(urllib.parse.parse_qsl(search[1:])).get('isin')

    filters = []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period)]
    for k, v in args:
        if v is not None:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")

    master_data = pd.DataFrame(master_data)
    if filters:
        master_data = master_data.query(' and '.join(filters))

    out = master_data[['isin']].to_dict('records')
    if isin not in master_data['isin'].tolist():
        active_cell = None
    else:
        active_cell['row'] = next(i for i, x in enumerate(out) if x['isin'] == isin)

    tooltip_source = master_data.groupby('isin').max()[['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period']]
    tooltip_data = [
        {
            column: {'value': '\n'.join(f'{k.capitalize().replace("_", " ")}: {v}' for k, v in tooltip_source.loc[value].items())}
            for column, value in row.items()
        } for row in out
    ]
    return out, active_cell, tooltip_data


@app.callback(Output("historical_plot", "figure"),
              Input('isin_selector_table', 'active_cell'),
              State('isin_selector_table', 'data'))
def update_historical_plot(active_cell, isin_data):
    if not isin_data or active_cell is None:
        return go.Figure(layout=styles.HISTORICAL_GRAPH_STYLE)

    isin = isin_data[active_cell['row']]['isin']

    df = query_db(sql="select * from ohlc_pricez where isin = :isin", params={"isin": isin})
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    fig = go.Figure(
        data=go.Candlestick(
            x=df['timestamp'].dt.date,
            open=df['open_price'],
            close=df['close_price'],
            high=df['high_price'],
            low=df['low_price'],
        )
    )

    fig.update_layout(**styles.HISTORICAL_GRAPH_STYLE)
    logging.info(f'Updated historical plot figure with isin = {isin}')

    return fig


"""
import plotly.express as px
import pandas as pd
df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv')

fig = px.scatter(df, x='Date', y='AAPL.High', range_x=['2015-12-01', '2016-01-15'],
                 title="Hide Gaps with rangebreaks")
fig.update_xaxes(
    rangebreaks=[
        dict(bounds=["sat", "mon"]), #hide weekends
        dict(values=["2015-12-25", "2016-01-01"])  # hide Christmas and New Year's
    ]
)
fig.show()
"""
