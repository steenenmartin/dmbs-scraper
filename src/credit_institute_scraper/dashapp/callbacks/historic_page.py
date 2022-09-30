import logging
import pandas as pd
from dash import Output, Input, State
from plotly import graph_objects as go
from .. import styles
from ..dash_app import dash_app as app
from .utils import update_search_bar_template, update_dropdowns
import urllib.parse


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
], Input('historical_store', 'data'))
def update_dropdowns_historical_plot(df):
    inst, coup, ytm, max_io, _ = update_dropdowns(df=df, log_text='Updated dropdown labels for historical plot')
    return inst, coup, ytm, max_io


@app.callback(Output("isin_selector_table", "data"),
              Output("isin_selector_table", "active_cell"),
              [Input('select_institute_historical_plot', 'value'),
               Input('select_coupon_historical_plot', 'value'),
               Input("select_ytm_historical_plot", "value"),
               Input("select_max_io_historical_plot", "value")],
              State('historical_store', 'data'),
              State('url', 'search'),
              State('isin_selector_table', 'active_cell'))
def update_isin_selector_table(institute, coupon_rate, years_to_maturity, max_interest_only_period, df, search, active_cell):
    isin = dict(urllib.parse.parse_qsl(search[1:])).get('isin')

    filters = []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period)]
    for k, v in args:
        if v is not None:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")

    df = pd.DataFrame(df)
    if filters:
        df = df.query(' and '.join(filters))

    out = df[['isin']].drop_duplicates().to_dict('records')
    if isin not in df['isin'].tolist():
        active_cell = None
    else:
        active_cell['row'] = next(i for i, x in enumerate(out) if x['isin'] == isin)
    return out, active_cell


@app.callback(Output("historical_plot", "figure"),
              Input('isin_selector_table', 'active_cell'),
              State("historical_store", "data"),
              State('isin_selector_table', 'data'))
def update_historical_plot(active_cell, df, isin_data):
    if not isin_data or active_cell is None:
        return go.Figure(layout=styles.HISTORICAL_GRAPH_STYLE)

    isin = isin_data[active_cell['row']]['isin']
    df = pd.DataFrame(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['isin'] == isin]

    fig_dct = dict()
    for g, dat in df[df['price_type'].isin(['Open', 'Close', 'Low', 'High'])].groupby('price_type'):
        fig_dct[str(g).lower()] = dat['spot_price']
        fig_dct['x'] = dat['timestamp'].dt.date

    fig = go.Figure(data=go.Candlestick(**fig_dct))

    fig.update_layout(**styles.HISTORICAL_GRAPH_STYLE)
    logging.info(f'Updated historical plot figure with isin = {isin}')

    return fig
