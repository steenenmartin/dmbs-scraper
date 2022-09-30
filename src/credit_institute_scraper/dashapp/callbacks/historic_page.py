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
              Output("isin_selector_table", "tooltip_data"),
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

    tooltip_source = df.groupby('isin').max()[['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period']]
    tooltip_data = [
        {
            column: {'value': ', '.join(f'{k}: {v}' for k, v in tooltip_source.loc[value].items()), 'type': 'markdown'}
            for column, value in row.items()
        } for row in out
    ]
    return out, active_cell, tooltip_data


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

    # The 5 ISINs below from Nordea have maturity of both 15Y and 20Y, giving duplicates in the database. We simply
    # apply a filter here to get the observations where maturity is highest, as candlestick plots bugs with duplicates
    if isin in ['DK0002056134', 'DK0002054436', 'DK0002053545', 'DK0002051176', 'DK0002050285']:
        df = df[df['years_to_maturity'] == df['years_to_maturity'].max()]

    fig_dct = dict()
    for g, dat in df[df['price_type'].isin(['Open', 'Close', 'Low', 'High'])].groupby('price_type'):
        fig_dct[str(g).lower()] = dat['spot_price']
        fig_dct['x'] = dat['timestamp'].dt.date

    fig = go.Figure(data=go.Candlestick(**fig_dct))

    fig.update_layout(**styles.HISTORICAL_GRAPH_STYLE)
    logging.info(f'Updated historical plot figure with isin = {isin}')

    return fig
