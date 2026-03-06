from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from colour import Color

DB_PATH = Path(__file__).resolve().parents[3] / 'database.db'


GRAPH_STYLE = dict(
    plot_bgcolor="#f2f2f2",
    paper_bgcolor="#FFFFFF",
    font={"color": "#000000"},
    xaxis={"showline": True, "zeroline": False, "showgrid": True, "gridcolor": "#676565"},
    yaxis={"showline": True, "zeroline": False, "showgrid": True, "gridcolor": "#676565"},
)


def query_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(sql, conn, params=params)


def get_master_data() -> pd.DataFrame:
    return query_df(
        """
        select distinct institute, isin, years_to_maturity, max_interest_only_period, coupon_rate
        from prices
        """
    )


def options_for(df: pd.DataFrame, col: str) -> list[str]:
    return sorted([x for x in df[col].dropna().unique().tolist()])


def filter_data(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    for key, value in filters.items():
        if value not in (None, ""):
            out = out[out[key] == _cast_like(out, key, value)]
    return out


def _cast_like(df: pd.DataFrame, key: str, value: str) -> Any:
    if pd.api.types.is_numeric_dtype(df[key]):
        return pd.to_numeric(value)
    return value


def make_spot_prices_figure(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title='No matching spot price data', **GRAPH_STYLE)
        return fig

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    groupers = ['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period', 'isin']
    groups = sorted(df.groupby(groupers), key=lambda x: x[1]['spot_price'].mean(), reverse=True)
    colors = Color("darkblue").range_to(Color("#34a1fa"), len(groups))

    traces = []
    for (grp, tmp_df), color in zip(groups, colors):
        tmp_df = tmp_df.sort_values('timestamp')
        name = '<br>'.join(f'{k.replace("_", " ").title()}: {v}' for k, v in zip(groupers, grp))
        traces.append(
            go.Scattergl(
                x=tmp_df['timestamp'],
                y=tmp_df['spot_price'],
                mode='lines',
                line=dict(width=3, shape='hv', color=color.get_hex()),
                name=name,
                hovertemplate='Time: %{x}<br>Price: %{y:.2f}',
                showlegend=False,
            )
        )

    fig = go.Figure(traces)
    fig.update_layout(title='Fixed loan spot prices', xaxis_title='Time (Europe/Copenhagen)', **GRAPH_STYLE)
    return fig


def make_ohlc_figure(isin: str | None) -> go.Figure:
    if not isin:
        fig = go.Figure()
        fig.update_layout(title='Select ISIN to view OHLC chart', **GRAPH_STYLE)
        return fig

    df = query_df('select * from ohlc_prices where isin = :isin', {'isin': isin})
    if df.empty:
        fig = go.Figure()
        fig.update_layout(title=f'No OHLC data for {isin}', **GRAPH_STYLE)
        return fig

    pivot = (
        df.pivot_table(index='timestamp', columns='price_type', values='spot_price', aggfunc='last')
        .reset_index()
        .sort_values('timestamp')
    )
    pivot['timestamp'] = pd.to_datetime(pivot['timestamp'])

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=pivot['timestamp'].dt.date,
                open=pivot['Open'],
                high=pivot['High'],
                low=pivot['Low'],
                close=pivot['Close'],
                showlegend=False,
            ),
            go.Scatter(
                x=pivot['timestamp'].dt.date,
                y=pivot['Close'],
                line=dict(color='darkred', width=0.5),
                showlegend=False,
                hoverinfo='none',
            ),
        ]
    )
    fig.update_layout(title=f'OHLC prices ({isin})', xaxis_title='Date', **GRAPH_STYLE)
    fig.update_xaxes(rangeslider_visible=False)
    return fig


def make_spot_rates_figure() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title='Flex loan rates',
        annotations=[dict(text='Spot-rate dataset is not present in local SQLite database.', x=0.5, y=0.5, showarrow=False)],
        **GRAPH_STYLE,
    )
    return fig
