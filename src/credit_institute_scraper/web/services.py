from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from colour import Color
import pytz


DB_PATH = Path(__file__).resolve().parents[3] / 'database.db'


GRAPH_STYLE = dict(
    plot_bgcolor="#f2f2f2",
    paper_bgcolor="#FFFFFF",
    font={"color": "#000000"},
    margin={"l": 20, "r": 20, "b": 30, "t": 40},
)

SPOT_GROUPERS = ['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period', 'isin']


def query_df(sql: str, params: Any = None) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(sql, conn, params=params)


def get_master_data(start_utc: Any | None = None, end_utc: Any | None = None) -> pd.DataFrame:
    sql = """
        select distinct institute, isin, years_to_maturity, max_interest_only_period, coupon_rate
        from prices
    """
    params: list[Any] = []
    if start_utc is not None and end_utc is not None:
        sql += " where timestamp between ? and ?"
        params.extend([start_utc, end_utc])
    return query_df(sql, params=params if params else None)


def options_for(df: pd.DataFrame, col: str) -> list[str]:
    vals = sorted([x for x in df[col].dropna().unique().tolist()])
    if pd.api.types.is_numeric_dtype(df[col]):
        return [str(v) for v in vals]
    return vals


def filter_data(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    out = df.copy()
    for key, value in filters.items():
        if value in (None, "", []):
            continue

        if isinstance(value, (list, tuple, set)):
            casted = [_cast_like(out, key, v) for v in value if v not in (None, "")]
            if casted:
                out = out[out[key].isin(casted)]
        else:
            out = out[out[key] == _cast_like(out, key, value)]
    return out


def constrained_options(master_df: pd.DataFrame, filters: dict[str, Any]) -> dict[str, list[str]]:
    response: dict[str, list[str]] = {}
    for key in filters.keys():
        other_filters = {k: v for k, v in filters.items() if k != key}
        valid_subset = filter_data(master_df, other_filters)
        response[key] = options_for(valid_subset, key)
    return response


def _cast_like(df: pd.DataFrame, key: str, value: str) -> Any:
    if pd.api.types.is_numeric_dtype(df[key]):
        return pd.to_numeric(value)
    return value


def _group_name(group_values: tuple[Any, ...]) -> str:
    return '<br>'.join(f'{k.replace("_", " ").title()}: {v}' for k, v in zip(SPOT_GROUPERS, group_values))


def build_spot_price_series(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    data = df.copy()
    data['timestamp'] = pd.to_datetime(data['timestamp'], utc=True).dt.tz_convert('Europe/Copenhagen')

    groups = sorted(data.groupby(SPOT_GROUPERS), key=lambda x: x[1]['spot_price'].mean(), reverse=True)
    series: list[dict[str, Any]] = []
    for grp, tmp_df in groups:
        tmp_df = tmp_df.sort_values('timestamp')
        series.append(
            {
                'name': _group_name(grp),
                'x': tmp_df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S%z').tolist(),
                'y': tmp_df['spot_price'].astype(float).tolist(),
            }
        )
    return series


def make_spot_prices_figure(df: pd.DataFrame, start_utc: Any, end_utc: Any) -> go.Figure:
    tz_cph = pytz.timezone('Europe/Copenhagen')
    start_cet = pd.to_datetime(start_utc, utc=True).tz_convert(tz_cph)
    end_cet = pd.to_datetime(end_utc, utc=True).tz_convert(tz_cph)

    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            title='No matching spot price data',
            xaxis=dict(
                range=[start_cet, end_cet],
                tick0=start_cet,
                dtick=3600000,
                showgrid=True,
                gridwidth=1,
                gridcolor='#676565',
                griddash='solid',
                showline=True,
                zeroline=False,
                minor=dict(dtick=900000, showgrid=True, gridwidth=1, gridcolor='#676565', griddash='dot'),
            ),
            yaxis=dict(showline=True, zeroline=False, showgrid=True, gridcolor='#676565'),
            **GRAPH_STYLE,
        )
        return fig

    data = df.copy()
    data['timestamp'] = pd.to_datetime(data['timestamp'], utc=True).dt.tz_convert('Europe/Copenhagen')
    groups = sorted(data.groupby(SPOT_GROUPERS), key=lambda x: x[1]['spot_price'].mean(), reverse=True)
    colors = Color("darkblue").range_to(Color("#34a1fa"), len(groups))

    traces = []
    for (grp, tmp_df), color in zip(groups, colors):
        tmp_df = tmp_df.sort_values('timestamp')
        traces.append(
            go.Scattergl(
                x=tmp_df['timestamp'],
                y=tmp_df['spot_price'],
                mode='lines',
                line=dict(width=3, shape='hv', color=color.get_hex()),
                name=_group_name(grp),
                hovertemplate='Time: %{x}<br>Price: %{y:.2f}',
                showlegend=False,
            )
        )

    fig = go.Figure(traces)
    fig.update_layout(
        title='Fixed loan spot prices',
        xaxis_title='Time (CEST/CET)',
        xaxis=dict(
            range=[start_cet, end_cet],
            tick0=start_cet,
            dtick=3600000,
            showgrid=True,
            gridwidth=1,
            gridcolor='#676565',
            griddash='solid',
            showline=True,
            zeroline=False,
            minor=dict(dtick=900000, showgrid=True, gridwidth=1, gridcolor='#676565', griddash='dot'),
        ),
        yaxis=dict(showline=True, zeroline=False, showgrid=True, gridcolor='#676565'),
        **GRAPH_STYLE,
    )
    return fig


def get_filtered_prices(master_data: pd.DataFrame, filters: dict[str, Any], start_utc: Any, end_utc: Any, since: str | None = None) -> pd.DataFrame:
    filtered_master = filter_data(master_data, filters)
    if filtered_master.empty:
        return pd.DataFrame(columns=['timestamp', 'institute', 'isin', 'years_to_maturity', 'max_interest_only_period', 'coupon_rate', 'spot_price'])

    isins = filtered_master['isin'].unique().tolist()
    placeholders = ', '.join(['?'] * len(isins))
    sql = f"select * from prices where isin in ({placeholders}) and timestamp between ? and ?"
    params: list[Any] = list(isins) + [start_utc, end_utc]
    if since:
        sql += " and timestamp > ?"
        params.append(since)

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql(sql, conn, params=params)


def latest_timestamp(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    ts = pd.to_datetime(df['timestamp'], utc=True).max()
    return ts.strftime('%Y-%m-%dT%H:%M:%SZ')


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
    fig.update_layout(title=f'OHLC prices ({isin})', xaxis_title='Date', yaxis=dict(showline=True, zeroline=False, showgrid=True, gridcolor='#676565'), xaxis=dict(showline=True, zeroline=False, showgrid=True, gridcolor='#676565'), **GRAPH_STYLE)
    fig.update_xaxes(rangeslider_visible=False)
    return fig


def make_spot_rates_figure() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title='Flex loan rates',
        annotations=[dict(text='Spot-rate dataset is not present in local SQLite database.', x=0.5, y=0.5, showarrow=False)],
        xaxis=dict(showline=True, zeroline=False, showgrid=True, gridcolor='#676565'),
        yaxis=dict(showline=True, zeroline=False, showgrid=True, gridcolor='#676565'),
        **GRAPH_STYLE,
    )
    return fig
