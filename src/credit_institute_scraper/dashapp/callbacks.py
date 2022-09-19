from credit_institute_scraper.dashapp.app import dash_app as app
from .pages import page_not_found, home, plots
from dash import Output, Input
from ..database.sqlite_conn import query_db
import plotly.graph_objects as go
import datetime as dt


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return home.home_page()
    elif pathname == "/Plots":
        return plots.plot_page()
    # If the user tries to reach a different page, return a 404 message
    return page_not_found.page_not_found(pathname)


@app.callback(Output("daily_plot", "figure"), [Input("select_institute_daily_plot", "value"),
                                               Input("select_coupon_daily_plot", "value"),
                                               Input("select_ytm_daily_plot", "value"),
                                               Input("select_max_io_daily_plot", "value")])
def update_daily_plot(institute, coupon_rate, years_to_maturity, max_interest_only_period):
    date = dt.date(2022, 9, 16)
    sql = f"select * from prices where date(timestamp) = :date"

    filters = []
    if institute is not None:
        sql += " and institute = :institute"
    else:
        filters.append('institute')
    if coupon_rate is not None:
        sql += " and coupon_rate = :coupon_rate"
    else:
        filters.append('coupon_rate')
    if years_to_maturity is not None:
        sql += " and years_to_maturity = :years_to_maturity"
    else:
        filters.append('years_to_maturity')

    if max_interest_only_period is not None:
        sql += " and max_interest_only_period = :max_interest_only_period"
    else:
        filters.append('max_interest_only_period')
    df = query_db(sql, params=locals())

    scatters = []
    groups = df.groupby(filters) if filters else [('', df)]
    for g, tmp_df in groups:
        g = g if isinstance(g, (list, tuple)) else [g]
        scatters.append(go.Scatter(x=tmp_df['timestamp'],
                                   y=tmp_df['spot_price'],
                                   line=dict(width=3),
                                   name='<br>'.join(f'{f}: {v}' for f, v in zip(filters, g)),
                                   line_shape='hv',
                                   showlegend=True
                                   ))
    fig = go.Figure(scatters)
    fig.update_layout(title=f'Daily spot prices',
                      xaxis_title='Timestamp',
                      yaxis_title='Spot price',
                      )
    return fig
