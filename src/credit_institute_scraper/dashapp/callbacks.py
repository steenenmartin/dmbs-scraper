from .dash_app import dash_app as app
from .pages import page_not_found, home, daily_plots, historical_plots
from . import styles
from ..utils.object_helper import listify
from ..utils.date_helper import get_active_date
from dash import Output, Input, State
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
import logging
from colour import Color
from ..utils.server_helper import is_heroku_server
if is_heroku_server():
    from ..database.postgres_conn import query_db
else:
    from ..database.sqlite_conn import query_db

date = get_active_date()


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return home.home_page()
    elif pathname == "/daily":
        return daily_plots.daily_plot_page(date=date)
    elif pathname == "/historical":
        return historical_plots.historical_plot_page()

    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(pathname)


@app.callback(Output("daily_plot", "figure"),
              [Input("select_institute_daily_plot", "value"),
               Input("select_coupon_daily_plot", "value"),
               Input("select_ytm_daily_plot", "value"),
               Input("select_max_io_daily_plot", "value"),
               Input("select_isin_daily_plot", "value"),
               Input('interval-component', 'n_intervals'),
               Input("daily_store", "data")])
def update_daily_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, _, df):
    groupers, filters = [], []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period), ('isin', isin)]
    for k, v in args:
        if v:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")
        if not v or len(v) > 1:
            groupers.append(k)

    df = pd.DataFrame(df)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    full_idx = pd.date_range(dt.datetime.combine(date, dt.time(7)), dt.datetime.combine(date, dt.time(15)), freq='5T')
    if filters:
        df = df.query(' and '.join(filters))

    lines = []
    groups = sorted(df.groupby(groupers), key=lambda x: x[1]['spot_price'].mean(), reverse=True) if groupers else [('', df)]
    colors = Color("Blue").range_to(Color("green"), len(groups))
    for grp, c in zip(groups, colors):
        g, tmp_df = grp
        g = listify(g)

        tmp_df = tmp_df.set_index('timestamp').reindex(full_idx, fill_value=float('nan'))
        tmp_df.index = [x.strftime('%H:%M') for x in tmp_df.index]
        lgnd = '<br>'.join(f'{f.capitalize().replace("_", " ")}: {v}' for f, v in zip(groupers, g))
        hover = 'Time: %{x}<br>Price: %{y:.2f}<br>Isin: %{text}'
        lines.append(go.Scatter(
            x=tmp_df.index,
            y=tmp_df['spot_price'],
            line=dict(width=2, shape='hv'),
            name=lgnd,
            hovertemplate=hover,
            text=tmp_df['isin'],
            showlegend=True,
            marker={'color': c.get_hex()},
        ))
    fig = go.Figure(lines)
    fig.update_layout(**styles.DAILY_GRAPH_STYLE)
    logging.info(f'Updated daily plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')
    return fig


@app.callback([Output('select_institute_daily_plot', 'options'),
               Output('select_coupon_daily_plot', 'options'),
               Output('select_ytm_daily_plot', 'options'),
               Output('select_max_io_daily_plot', 'options'),
               Output('select_isin_daily_plot', 'options')],
              Input('daily_store', 'data')
              )
def update_dropdowns_daily_plot(df):
    df = pd.DataFrame(df)
    inst = [{'label': opt, 'value': opt} for opt in sorted(df['institute'].unique())]
    coup = [{'label': opt, 'value': opt} for opt in sorted(df['coupon_rate'].unique())]
    ytm = [{'label': opt, 'value': opt} for opt in sorted(df['years_to_maturity'].unique())]
    maxio = [{'label': opt, 'value': opt} for opt in sorted(df['max_interest_only_period'].unique())]
    isin = [{'label': opt, 'value': opt} for opt in sorted(df['isin'].unique())]
    logging.info('Updated dropdown labels for daily plot')
    return inst, coup, ytm, maxio, isin


@app.callback(Output('daily_store', 'data'), Input('interval-component', 'n_intervals'))
def periodic_data_update_daily_plot(n):
    logging.info(f'Updated data at interval {n}')
    df = query_db(sql="select * from prices where date(timestamp) = :date",
                  params={'date': date}).to_dict("records")
    return df


@app.callback([Output('select_institute_historical_plot', 'options'),
               Output('select_coupon_historical_plot', 'options'),
               Output('select_ytm_historical_plot', 'options'),
               Output('select_max_io_historical_plot', 'options'),
               Output('select_isin_historical_plot', 'options'),
               Output("historical_plot", "figure")],
              [Input("select_institute_historical_plot", "value"),
               Input("select_coupon_historical_plot", "value"),
               Input("select_ytm_historical_plot", "value"),
               Input("select_max_io_historical_plot", "value"),
               Input("select_isin_historical_plot", "value")])
def update_historical_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin):
    groupers, filters = [], []
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period), ('isin', isin)]
    for k, v in args:
        if v:
            v_str = f'"{v}"' if isinstance(v, str) else v
            filters.append(f"{k} == {v_str}")
        if not v or len(v) > 1:
            groupers.append(k)

    df = pd.DataFrame(
        query_db(sql="select * from ohlc_prices").to_dict("records")
    )

    inst = [{'label': opt, 'value': opt} for opt in sorted(df['institute'].unique())]
    coup = [{'label': opt, 'value': opt} for opt in sorted(df['coupon_rate'].unique())]
    ytm = [{'label': opt, 'value': opt} for opt in sorted(df['years_to_maturity'].unique())]
    maxio = [{'label': opt, 'value': opt} for opt in sorted(df['max_interest_only_period'].unique())]
    isin = [{'label': opt, 'value': opt} for opt in sorted(df['isin'].unique())]

    if filters:
        df = df.query(' and '.join(filters))
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    open_df = df.loc[df['price_type'] == "Open"]
    close_df = df.loc[df['price_type'] == "Close"]
    low_df = df.loc[df['price_type'] == "Low"]
    high_df = df.loc[df['price_type'] == "High"]

    # for grp, c in zip(groups, colors):
    #     g, tmp_df = grp
    #     g = listify(g)
    #
    #     tmp_df = tmp_df.set_index('timestamp')
    #     tmp_df.index = [x.strftime('%d/%m') for x in tmp_df.index]
    #     lgnd = '<br>'.join(f'{f.capitalize().replace("_", " ")}: {v}' for f, v in zip(groupers, g))
    #     hover = 'Date: %{x}<br>Price: %{y:.2f}'
    #     lines.append(go.Scatter(
    #         x=tmp_df.index,
    #         y=tmp_df['spot_price'],
    #         line=dict(width=2),
    #         name=lgnd,
    #         hovertemplate=hover,
    #         showlegend=True,
    #         marker={'color': c.get_hex()},
    #     ))

    fig = go.Figure(data=go.Ohlc(
            x=open_df['timestamp'].dt.date,
            open=open_df['spot_price'],
            high=high_df['spot_price'],
            low=low_df['spot_price'],
            close=close_df['spot_price']
        )
    )

    fig.update_layout(**styles.HISTORICAL_GRAPH_STYLE)
    logging.info(f'Updated historical plot figure with args {", ".join(f"{k}={v}" for k, v in args)}')

    return inst, coup, ytm, maxio, isin, fig
