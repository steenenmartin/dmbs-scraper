from dash import Input, Output, State
from dash.exceptions import PreventUpdate
from .utils import update_dropdowns, update_search_bar_template
from ..dash_app import dash_app as app
import pandas as pd
import plotly.express as px


@app.callback([
    Output('base_isin_spread', 'options'),
    Output('compare_isins_spread', 'options'),
], Input('master_data', 'data'))
def update_dropdowns_spreads_plot(master_data):
    ud = update_dropdowns(master_data=master_data, log_text='Updated dropdown labels for spot prices plot')
    return ud[-1], ud[-1]


@app.callback(
    Output('rate_spreads_plot', 'figure'),
    Input('base_isin_spread', 'value'),
    Input('compare_isins_spread', 'value'),
    State('spot_prices_store', 'data')
)
def update_spreads_plot(base_isin, compare_isins, data):
    if not base_isin or not compare_isins:
        raise PreventUpdate
    df = pd.DataFrame(data)
    df = df[df['isin'].isin([base_isin, *compare_isins])]

    fig = px.scatter(
        df,
        x='timestamp',
        y='spot_price',
    )
    return fig


@app.callback(
    Output('dummy3', 'value'),
    Input('base_isin_spread', 'value'),
    Input('compare_isins_spread', 'value'),
    State('url', 'search'))
def update_search_bar_spot_prices(base_isin, compare_isins, search):
    return update_search_bar_template(search=search, base_isin=base_isin, compare_isins=compare_isins)