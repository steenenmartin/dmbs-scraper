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


@app.callback(Output("daily_plot", "figure"), [Input("select_institute_daily_plot", "value")])
def update_daily_plot(institute):
    date = dt.date(2022, 9, 16)
    years_to_maturity = 30
    max_interest_only_period = 0
    df = query_db(f"""
select * from prices 
where date(timestamp) = :date 
and institute = :institute
and years_to_maturity = :years_to_maturity
and max_interest_only_period = :max_interest_only_period""", params=locals())

    scatters = []
    for cr in sorted(df['coupon_rate'].unique()):
        tmp_df = df[df['coupon_rate'] == cr]
        scatters.append(go.Scatter(x=tmp_df['timestamp'], y=tmp_df['spot_price'], line=dict(width=3), name=cr))
    fig = go.Figure(scatters)
    fig.update_layout(title=f'Years to maturity: {years_to_maturity}, max interest only period: {max_interest_only_period}, institute: {institute}, date={date.isoformat()}',
                      xaxis_title='Timestamp',
                      yaxis_title='Spot price')
    return fig