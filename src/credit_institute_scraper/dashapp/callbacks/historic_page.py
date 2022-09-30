import logging
import pandas as pd
from dash import Output, Input, State
from plotly import graph_objects as go
from .. import styles
from ..dash_app import dash_app as app
from .utils import update_search_bar_template, update_dropdowns


@app.callback(
    Output('dummy2', 'value'),
    Input('select_institute_historical_plot', 'value'),
    Input('select_coupon_historical_plot', 'value'),
    Input("select_ytm_historical_plot", "value"),
    Input("select_max_io_historical_plot", "value"),
    Input("select_isin_historical_plot", "value"),
    State('url', 'search'))
def update_search_bar_historic(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, search):
    return update_search_bar_template(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, search)


@app.callback([
    Output('select_institute_historical_plot', 'options'),
    Output('select_coupon_historical_plot', 'options'),
    Output('select_ytm_historical_plot', 'options'),
    Output('select_max_io_historical_plot', 'options'),
    Output('select_isin_historical_plot', 'options')
], Input('historical_store', 'data'))
def update_dropdowns_historical_plot(df):
    return update_dropdowns(df=df, log_text='Updated dropdown labels for historical plot')


@app.callback([Output("historical_plot", "figure"),
               Output('select_institute_historical_plot', 'value'),
               Output('select_coupon_historical_plot', 'value'),
               Output("select_ytm_historical_plot", "value"),
               Output("select_max_io_historical_plot", "value"),
               Output("select_isin_historical_plot", "value")],
              [Input('select_institute_historical_plot', 'value'),
               Input('select_coupon_historical_plot', 'value'),
               Input("select_ytm_historical_plot", "value"),
               Input("select_max_io_historical_plot", "value"),
               Input("select_isin_historical_plot", "value"),
               Input("historical_store", "data")])
def update_historical_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, df):
    if isin is not None and any(x is None for x in [institute, coupon_rate, years_to_maturity, max_interest_only_period]) and not all(x is None for x in [institute, coupon_rate, years_to_maturity, max_interest_only_period]):
        isin = None

    filters = []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period), ('isin', isin)]
    for k, v in args:
        if v is not None:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")

    df = pd.DataFrame(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    if filters:
        df = df.query(' and '.join(filters))

    fig_dct = dict()
    if len(df['isin'].unique()) == 1:
        institute = df['institute'].iloc[0]
        coupon_rate = df['coupon_rate'].iloc[0]
        years_to_maturity = df['years_to_maturity'].iloc[0]
        max_interest_only_period = df['max_interest_only_period'].iloc[0]
        isin = df['isin'].iloc[0]

        for g, dat in df[df['price_type'].isin(['Open', 'Close', 'Low', 'High'])].groupby('price_type'):
            fig_dct[str(g).lower()] = dat['spot_price']
            fig_dct['x'] = dat['timestamp'].dt.date

    fig = go.Figure(data=go.Candlestick(**fig_dct))

    fig.update_layout(**styles.HISTORICAL_GRAPH_STYLE)
    logging.info(f'Updated historical plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')

    return fig, institute, coupon_rate, years_to_maturity, max_interest_only_period, isin
