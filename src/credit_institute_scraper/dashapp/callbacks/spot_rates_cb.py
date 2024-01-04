import logging
from datetime import datetime

import pandas as pd
from colour import Color
from dash import Output, Input, State
from plotly import graph_objects as go

from . import update_search_bar_template
from ..dash_app import dash_app as app
from ..styles import __graph_style
from ...database.postgres_conn import query_db
from ...utils.object_helper import listify


@app.callback([Output("spot_rates_plot", "figure"),
               Output("loading-spinner-output-spot-rates", "children")],
              [Input("select_institute_spot_rates_plot", "value"),
               Input("select_fixed_rate_period_spot_rates_plot", "value"),
               Input("select_max_io_spot_rates_plot", "value"),
               Input('spot_rates_plot', 'relayoutData')])
def update_spot_rates_plot(institute, fixed_rate_period, max_interest_only_period, rel):
    groupers, filters = [], []
    args = [
        ('institute', institute),
        ('fixed_rate_period', fixed_rate_period),
        ('max_interest_only_period', max_interest_only_period),
    ]
    for k, v in args:
        if v:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")
        if not v or len(v) > 1:
            groupers.append(k)

    spot_rates = query_db(sql="select * from rates")
    if filters:
        spot_rates = spot_rates.query(' and '.join(filters))

    spot_rates['timestamp'] = pd.to_datetime(spot_rates['timestamp']).dt.date
    if spot_rates.shape[0] != 0:
        full_idx = pd.date_range(spot_rates['timestamp'].min(), spot_rates['timestamp'].max())

    lines = []
    groups = sorted(spot_rates.groupby(groupers), key=lambda x: x[1]["spot_rate"].mean(), reverse=True) if groupers else [('', spot_rates)]
    colors = Color("darkblue").range_to(Color("#34a1fa"), len(groups))
    for grp, c in zip(groups, colors):
        g, tmp_df = grp
        g = listify(g)

        tmp_df = tmp_df.set_index('timestamp').reindex(full_idx, fill_value=float('nan'))

        lgnd = '<br>'.join(f'{f.capitalize().replace("_", " ")}: {v}' for f, v in zip(groupers, g))
        hover = 'Date: %{x}<br>Rate: %{y:.2f}'
        lines.append(go.Scatter(
            x=tmp_df.index,
            y=tmp_df["spot_rate"],
            line=dict(width=3),
            name=lgnd,
            hovertemplate=hover,
            showlegend=False,
            marker={'color': c.get_hex()},
            connectgaps=True
        ))
    fig = go.Figure(lines)
    fig.update_layout(**__graph_style(x_axis_title="Date", show_historic=True))

    x_range_specified = rel is not None and "xaxis.range[0]" in rel.keys() and "xaxis.range[1]" in rel.keys()
    if x_range_specified:
        xmin, xmax = datetime.fromisoformat(rel['xaxis.range[0]'].split(" ")[0]).date(), datetime.fromisoformat(rel['xaxis.range[1]'].split(" ")[0]).date()

        temp_df = spot_rates.loc[spot_rates['timestamp'].between(xmin, xmax)]["spot_rate"]
        ymin, ymax = temp_df.min(), temp_df.max()
        margin = (ymax - ymin) * 0.05

        fig['layout']['xaxis']['range'] = [xmin, xmax]
        fig['layout']['yaxis']['range'] = [ymin - margin, ymax + margin]

    y_range_specified = rel is not None and "yaxis.range[0]" in rel.keys() and "yaxis.range[1]" in rel.keys()
    if y_range_specified:
        fig['layout']['yaxis']['range'] = [rel['yaxis.range[0]'], rel['yaxis.range[1]']]

    logging.info(f'Updated spot rates plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')
    return fig, ''


@app.callback(
    Output('dummy3', 'value'),
    Input('select_institute_spot_rates_plot', 'value'),
    Input("select_fixed_rate_period_spot_rates_plot", "value"),
    Input("select_max_io_spot_rates_plot", "value"),
    State('url', 'search'))
def update_search_bar_spot_rates(institute, fixed_rate_period, max_interest_only_period, search):
    args = [
        ('institute', institute),
        ('fixed_rate_period', fixed_rate_period),
        ('max_interest_only_period', max_interest_only_period)
    ]

    return update_search_bar_template(args, search)


@app.callback([
    Output('select_institute_spot_rates_plot', 'options'),
    Output('select_fixed_rate_period_spot_rates_plot', 'options'),
    Output('select_max_io_spot_rates_plot', 'options'),
], Input('master_data_float', 'data'))
def update_dropdowns_spot_rates_plot(master_data):
    master_data = pd.DataFrame(master_data)
    inst = [{'label': opt, 'value': opt} for opt in sorted(master_data['institute'].unique())]
    fixed_rate_period = [{'label': opt, 'value': opt} for opt in sorted(master_data['fixed_rate_period'].unique())]
    maxio = [{'label': opt, 'value': opt} for opt in sorted(master_data['max_interest_only_period'].unique())]
    logging.info('Updated dropdown labels for spot rates plot')
    return inst, fixed_rate_period, maxio
