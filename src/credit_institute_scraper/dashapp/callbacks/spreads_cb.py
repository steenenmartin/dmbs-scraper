from dash import Input, Output, State
from dash.exceptions import PreventUpdate
from .utils import update_dropdowns, update_search_bar_template
from ..dash_app import dash_app as app
from .. import styles
from ...database.postgres_conn import query_db
from colour import Color
import pandas as pd
import plotly.graph_objects as go


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
)
def update_spreads_plot(base_isin, compare_isins):
    if not base_isin or not compare_isins:
        raise PreventUpdate

    isin_str = "', '".join([base_isin, *compare_isins])
    data = query_db(sql=f"select * from closing_prices where isin in ('{isin_str}')")
    df = pd.DataFrame(data)

    lines = []
    colors = Color("darkblue").range_to(Color("#34a1fa"), len(compare_isins))
    base = df[df['isin'] == base_isin].set_index('timestamp').sort_index()
    for gd, c in zip(df[df['isin'].isin(compare_isins)].groupby('isin'), colors):
        group, dat = gd
        dat = dat.set_index('timestamp').sort_index()
        lines.append(
            go.Scatter(
                x=dat.index,
                y=dat['spot_price'] - base['spot_price'],
                line=dict(width=3, shape='hv'),
                name=group,
                hovertemplate='Date: %{x}<br>Spread: %{y:.2f}',
                showlegend=False,
                marker={'color': c.get_hex()},
                connectgaps=True
            )
        )
    fig = go.Figure(lines)
    fig.update_layout(**styles.__graph_style(x_axis_title="Date", show_historic=False))

    return fig


@app.callback(
    Output('dummy3', 'value'),
    Input('base_isin_spread', 'value'),
    Input('compare_isins_spread', 'value'),
    State('url', 'search'))
def update_search_bar_spot_prices(base_isin, compare_isins, search):
    return update_search_bar_template(search=search, base_isin=base_isin, compare_isins=compare_isins)