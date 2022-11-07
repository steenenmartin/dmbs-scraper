import pandas as pd
from datetime import datetime as dt
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from ...database.postgres_conn import query_db
from ..dash_app import dash_app as app


def query_func(args):
    if not args:
        return

    if "table" not in args or args["table"] not in ("spot_prices", "offer_prices", "ohlc_prices"):
        return

    master_data = query_db(sql="select * from master_data")
    prices = query_db(sql=f"select * from {args['table']}",)

    df = pd.merge(prices, master_data, on="isin")

    return df


@app.callback(
    Output("export_data", "data"),
    Input("export_store", "data"),
)
def func(df):
    return dcc.send_data_frame(pd.DataFrame(df).to_csv, f"BondstatsExport_{dt.utcnow().strftime('%Y%m%d%H%M')}.csv", index=False)


def export_page(args):
    return dbc.Container(
        [
            html.H3("Export data"),
            dcc.Download(id="export_data"),
            dcc.Store(id='export_store', data=query_func(args).to_dict('records')),
            dbc.Card(
                [
                    dcc.Markdown(
                        """ 
                            **Guide**        
                            Ez        
                        """, style={'margin-left': '2rem', 'margin-top': '1rem'}
                    )
                ], style={'width': '50%'}
            )
        ]
    )
