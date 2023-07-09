import logging
from datetime import datetime

import pandas as pd
from colour import Color
from dash import Output, Input, State
from plotly import graph_objects as go
from ..dash_app import dash_app as app
from .utils import update_search_bar_template, update_dropdowns
from ..styles import __graph_style, get_tz_name
from ...database.postgres_conn import query_db
from ...utils.object_helper import listify


@app.callback([Output("spot_prices_plot", "figure"),
               Output("loading-spinner-output2", "children"),
               Output('historic_data_store', 'data')],
              [Input("select_institute_spot_prices_plot", "value"),
               Input("select_coupon_spot_prices_plot", "value"),
               Input("select_ytm_spot_prices_plot", "value"),
               Input("select_max_io_spot_prices_plot", "value"),
               Input("select_isin_spot_prices_plot", "value"),
               Input("show_historic", "on"),
               Input("spot_prices_store", "data"),
               Input("master_data", "data"),
               Input('spot_prices_plot', 'relayoutData')
               ],
              State("date_range_div", "children"),
              State('historic_data_store', 'data')
              )
def update_spot_prices_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, show_historic, spot_prices, master_data, rel, date_range, historic_prices):
    groupers, filters = [], []
    args = [
        ('institute', institute),
        ('coupon_rate', coupon_rate),
        ('years_to_maturity', years_to_maturity),
        ('max_interest_only_period', max_interest_only_period),
        ('isin', isin)
    ]
    for k, v in args:
        if v:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")
        if not v or len(v) > 1:
            groupers.append(k)

    master_data = pd.DataFrame(master_data)
    if filters:
        master_data = master_data.query(' and '.join(filters))

    if historic_prices is not None:
        historic_prices = pd.DataFrame(historic_prices)

    if show_historic:
        if historic_prices is None:
            historic_prices = query_db(sql="select * from closing_prices")
            historic_prices = pd.DataFrame(historic_prices)

        prices = historic_prices
    else:
        prices = pd.DataFrame(spot_prices)

    prices = prices[prices["isin"].isin(master_data["isin"].unique())]
    merged_df = pd.merge(prices, master_data, on="isin")

    if show_historic:
        merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp']).dt.date
        full_idx = pd.date_range(merged_df['timestamp'].min(), merged_df['timestamp'].max())
    else:
        merged_df['timestamp'] = pd.to_datetime(merged_df['timestamp']).dt.tz_localize('UTC')
        full_idx = pd.date_range(date_range[0], date_range[1], freq='5T').tz_convert('Europe/Copenhagen')

    lines = []
    groups = sorted(merged_df.groupby(groupers), key=lambda x: x[1]["spot_price"].mean(), reverse=True) if groupers else [('', merged_df)]
    colors = Color("darkblue").range_to(Color("#34a1fa"), len(groups))
    for grp, c in zip(groups, colors):
        g, tmp_df = grp
        g = listify(g)

        if show_historic:
            tmp_df = tmp_df.set_index('timestamp').reindex(full_idx, fill_value=float('nan'))
        else:
            tmp_df = tmp_df.set_index('timestamp').reindex(full_idx, fill_value=float('nan')).tz_convert('Europe/Copenhagen')

        lgnd = '<br>'.join(f'{f.capitalize().replace("_", " ")}: {v}' for f, v in zip(groupers, g))
        hover = 'Date: %{x}<br>Price: %{y:.2f}' if show_historic else 'Time: %{x}<br>Price: %{y:.2f}'
        lines.append(go.Scatter(
            x=tmp_df.index,
            y=tmp_df["spot_price"],
            line=dict(width=3, shape=None if show_historic else 'hv'),
            name=lgnd,
            hovertemplate=hover,
            showlegend=False,
            marker={'color': c.get_hex()},
            connectgaps=show_historic
        ))
    fig = go.Figure(lines)
    fig.update_layout(**__graph_style(x_axis_title="Date" if show_historic else f"Time ({get_tz_name()})", show_historic=show_historic))

    x_range_specified = rel is not None and "xaxis.range[0]" in rel.keys() and "xaxis.range[1]" in rel.keys()
    if show_historic and x_range_specified:
        xmin, xmax = datetime.fromisoformat(rel['xaxis.range[0]']).date(), datetime.fromisoformat(rel['xaxis.range[1]']).date()

        temp_df = merged_df.loc[merged_df['timestamp'].between(xmin, xmax)]["spot_price"]
        ymin, ymax = temp_df.min(), temp_df.max()
        margin = (ymax - ymin) * 0.05

        fig['layout']['xaxis']['range'] = [xmin, xmax]
        fig['layout']['yaxis']['range'] = [ymin - margin, ymax + margin]

    logging.info(f'Updated spot prices plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')
    return fig, '', historic_prices.to_dict('records') if historic_prices is not None else None


@app.callback(
    Output('dummy1', 'value'),
    Input('select_institute_spot_prices_plot', 'value'),
    Input('select_coupon_spot_prices_plot', 'value'),
    Input("select_ytm_spot_prices_plot", "value"),
    Input("select_max_io_spot_prices_plot", "value"),
    Input("select_isin_spot_prices_plot", "value"),
    Input("show_historic", "on"),
    State('url', 'search'))
def update_search_bar_spot_prices(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, show_historic, search):
    return update_search_bar_template(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, show_historic, search)


@app.callback([
    Output('select_institute_spot_prices_plot', 'options'),
    Output('select_coupon_spot_prices_plot', 'options'),
    Output('select_ytm_spot_prices_plot', 'options'),
    Output('select_max_io_spot_prices_plot', 'options'),
    Output('select_isin_spot_prices_plot', 'options')
], Input('master_data', 'data'))
def update_dropdowns_spot_prices_plot(master_data):
    return update_dropdowns(master_data=master_data, log_text='Updated dropdown labels for spot prices plot')
