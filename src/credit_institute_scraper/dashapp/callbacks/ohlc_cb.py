import logging
from datetime import datetime

import pandas as pd
from dash import Output, Input, State, ctx
from plotly import graph_objects as go
from .. import styles
from ..dash_app import dash_app as app
from .utils import update_search_bar_template, update_dropdowns
import urllib.parse

from ..styles import __graph_style
from ...database.postgres_conn import query_db


@app.callback(
    Output('dummy2', 'value'),
    Input('select_institute_ohlc_plot', 'value'),
    Input('select_coupon_ohlc_plot', 'value'),
    Input("select_ytm_ohlc_plot", "value"),
    Input("select_max_io_ohlc_plot", "value"),
    Input('isin_selector_table', 'active_cell'),
    State('url', 'search'),
    State('isin_selector_table', 'data'))
def update_search_bar_ohlc(institute, coupon_rate, years_to_maturity, max_interest_only_period, active_cell, search, isin_data):
    try:
        isin = None if not isin_data or active_cell is None else isin_data[active_cell['row']]['isin']
    except Exception as e:
        print(e)
        print(isin_data)
        print(active_cell)

    args = [
        ('institute', institute),
        ('coupon_rate', coupon_rate),
        ('years_to_maturity', years_to_maturity),
        ('max_interest_only_period', max_interest_only_period),
        ('isin', isin),
        ('show_historic', None)
    ]

    return update_search_bar_template(args, search)


@app.callback([
    Output('select_institute_ohlc_plot', 'options'),
    Output('select_coupon_ohlc_plot', 'options'),
    Output('select_ytm_ohlc_plot', 'options'),
    Output('select_max_io_ohlc_plot', 'options'),
], Input('master_data_ohlc', 'data'))
def update_dropdowns_ohlc_plot(master_data):
    inst, coup, ytm, max_io, _ = update_dropdowns(master_data=master_data, log_text='Updated dropdown labels for ohlc plot')
    return inst, coup, ytm, max_io


@app.callback(Output("isin_selector_table", "data"),
              Output("isin_selector_table", "active_cell"),
              Output("isin_selector_table", "tooltip_data"),
              [Input('select_institute_ohlc_plot', 'value'),
               Input('select_coupon_ohlc_plot', 'value'),
               Input("select_ytm_ohlc_plot", "value"),
               Input("select_max_io_ohlc_plot", "value")],
              State('master_data_ohlc', 'data'),
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


@app.callback(Output("ohlc_plot", "figure"),
              Output("ohlc_data_store", "data"),
              Output("loading-spinner-output3", "children"),
              Input('isin_selector_table', 'active_cell'),
              Input('ohlc_plot', 'relayoutData'),
              State('isin_selector_table', 'data'),
              State('ohlc_data_store', 'data'))
def update_ohlc_plot(active_cell, rel, isin_data, df):
    if not isin_data or active_cell is None:
        return go.Figure(layout=styles.HISTORICAL_GRAPH_STYLE), None, ''

    isin = isin_data[active_cell['row']]['isin']
    if ctx.triggered_id == 'isin_selector_table' or not df:
        df = query_db(sql="select * from ohlc_prices where isin = :isin", params={"isin": isin})
    else:
        df = pd.DataFrame(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df.sort_values(by="timestamp", inplace=True)

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df['timestamp'].dt.date,
                open=df['open_price'],
                close=df['close_price'],
                high=df['high_price'],
                low=df['low_price'],
                showlegend=False,
                hoverlabel=dict(namelength=0),
            ),
            go.Scatter(
                x=df['timestamp'].dt.date,
                y=df['close_price'],
                line=dict(color='darkred', width=0.5),
                showlegend=False,
                hoverinfo='none'
            )
        ]
    )

    fig.update_layout(**__graph_style(x_axis_title="Date", show_historic=True))
    fig.update_xaxes(rangeslider_visible=False)

    x_range_specified = rel is not None and "xaxis.range[0]" in rel.keys() and "xaxis.range[1]" in rel.keys()
    if x_range_specified:
        xmin, xmax = datetime.fromisoformat(rel['xaxis.range[0]'].split(" ")[0]), datetime.fromisoformat(rel['xaxis.range[1]'].split(" ")[0])

        temp_df = df.loc[df['timestamp'].between(xmin, xmax)]
        ymin = temp_df["low_price"].min()
        ymax = temp_df["high_price"].max()
        margin = (ymax - ymin) * 0.05

        fig['layout']['xaxis']['range'] = [xmin, xmax]
        fig['layout']['yaxis']['range'] = [ymin - margin, ymax + margin]

    y_range_specified = rel is not None and "yaxis.range[0]" in rel.keys() and "yaxis.range[1]" in rel.keys()
    if y_range_specified:
        fig['layout']['yaxis']['range'] = [rel['yaxis.range[0]'], rel['yaxis.range[1]']]

    logging.info(f'Updated ohlc plot figure with isin = {isin}')

    return fig, df.to_dict('records'), ''

