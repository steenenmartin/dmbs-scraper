import logging
import urllib.parse
import re
import dash_bootstrap_components as dbc
import pandas as pd
from dash_daq.Indicator import Indicator

from ...enums.status import Status


def update_search_bar_template(institute, coupon_rate, years_to_maturity, max_interest_only_period, isin, show_historic, search):
    args = [('institute', institute), ('coupon_rate', coupon_rate), ('years_to_maturity', years_to_maturity),
            ('max_interest_only_period', max_interest_only_period), ('isin', isin), ('show_historic', show_historic)]

    q = dict(urllib.parse.parse_qsl(search[1:]))  # [1:] to remove the leading `?`
    for k, v in args:
        if v or v == 0:
            q[k] = ','.join(map(str, v)) if isinstance(v, (list, tuple)) else str(v)
        else:
            q.pop(k, None)
    query_string = urllib.parse.urlencode(q)
    return '?' + query_string if query_string else ''


def update_dropdowns(master_data, log_text):
    master_data = pd.DataFrame(master_data)
    inst = [{'label': opt, 'value': opt} for opt in sorted(master_data['institute'].unique())]
    coup = [{'label': opt, 'value': opt} for opt in sorted(master_data['coupon_rate'].unique())]
    ytm = [{'label': opt, 'value': opt} for opt in sorted(master_data['years_to_maturity'].unique())]
    maxio = [{'label': opt, 'value': opt} for opt in sorted(master_data['max_interest_only_period'].unique())]
    isin = [{'label': opt, 'value': opt} for opt in sorted(master_data['isin'].unique())]
    logging.info(log_text)
    return inst, coup, ytm, maxio, isin


def data_bars(df, column):
    n_bins = 100
    bounds = [i * (1.0 / n_bins) for i in range(n_bins + 1)]
    ranges = [
        ((df[column].max() - df[column].min()) * i) + df[column].min()
        for i in bounds
    ]
    styles = []
    for i in range(1, len(bounds)):
        min_bound = ranges[i - 1]
        max_bound = ranges[i]
        max_bound_percentage = bounds[i] * 100
        styles.append({
            'if': {
                'filter_query': (
                    '{{{column}}} >= {min_bound}' +
                    (' && {{{column}}} < {max_bound}' if (i < len(bounds) - 1) else '')
                ).format(column=column, min_bound=min_bound, max_bound=max_bound),
                'column_id': column
            },
            'background': (
                """
                    linear-gradient(90deg,
                    #0074D9 0%,
                    #0074D9 {max_bound_percentage}%,
                    white {max_bound_percentage}%,
                    white 100%)
                """.format(max_bound_percentage=max_bound_percentage)
            ),
            'paddingBottom': 2,
            'paddingTop': 2
        })

    return styles


def data_bars_diverging(df, column, color_above='#3D9970', color_below='#FF4136', zero_mid=False):
    n_bins = 100
    bounds = [i * (1.0 / n_bins) for i in range(n_bins + 1)]

    if zero_mid:
        col_max = df[column].abs().max()
        col_min = -col_max
        midpoint = 0
    else:
        col_max = df[column].max()
        col_min = df[column].min()
        midpoint = (col_max + col_min) / 2

    ranges = [((col_max - col_min) * i) + col_min for i in bounds]
    styles = []
    for i in range(1, len(bounds)):
        min_bound = ranges[i - 1]
        max_bound = ranges[i]

        min_bound_percentage = bounds[i - 1] * 100
        max_bound_percentage = min(bounds[i] * 100, 99.2)

        style = {
            'if': {
                'filter_query': (
                    '{{{column}}} >= {min_bound}' +
                    (' && {{{column}}} < {max_bound}' if (i < len(bounds) - 1) else '')
                ).format(column=column, min_bound=min_bound, max_bound=max_bound),
                'column_id': column
            },
            'paddingBottom': 2,
            'paddingTop': 2
        }
        if max_bound > midpoint:
            background = (
                f"""
                    linear-gradient(90deg,
                    white 0%,
                    white 50%,
                    {color_above} 50%,
                    {color_above} {max_bound_percentage}%,
                    white {max_bound_percentage}%,
                    white 100%)
                """
            )
        else:
            background = (
                f"""
                    linear-gradient(90deg,
                    white 0%,
                    white {min_bound_percentage}%,
                    {color_below} {min_bound_percentage}%,
                    {color_below} 50%,
                    white 50%,
                    white 100%)
                """
            )
        style['background'] = background
        styles.append(style)

    return styles


def table_type(df_column):
    if isinstance(df_column.dtype, pd.DatetimeTZDtype):
        return 'datetime',
    elif (isinstance(df_column.dtype, pd.StringDtype) or
            isinstance(df_column.dtype, pd.BooleanDtype) or
            isinstance(df_column.dtype, pd.CategoricalDtype) or
            isinstance(df_column.dtype, pd.PeriodDtype)):
        return 'text'
    elif (isinstance(df_column.dtype, pd.SparseDtype) or
            isinstance(df_column.dtype, pd.IntervalDtype) or
            isinstance(df_column.dtype, pd.Int8Dtype) or
            isinstance(df_column.dtype, pd.Int16Dtype) or
            isinstance(df_column.dtype, pd.Int32Dtype) or
            isinstance(df_column.dtype, pd.Int64Dtype)):
        return 'numeric'
    else:
        return 'any'


def get_split_camelcase_string(string: str) -> str:
    words = re.findall(r"[A-Z](?:[a-z]+|[A-Z]*(?=[A-Z]|$))", string)
    words = [words[i].lower() if i != 0 else words[i] for i in range(len(words))]
    return str.join(" ", words)


def make_indicator(status):
    layout = []
    for i, row in status.iterrows():
        cur_id = f'{row["institute"]}-status-indicator'
        last_update = row['last_data_time'].tz_localize("UTC").tz_convert('Europe/Copenhagen')
        layout.extend([
            Indicator(
                label={'label': row['institute'], 'style': {'font-size': '1.25rem'}},
                color=getattr(Status, row['status'], Status.ExchangeClosed).value,
                className='uptime_indicator',
                id=cur_id,
            ),
            dbc.Tooltip(
                f'Status: {get_split_camelcase_string(row["status"])} \n Last updated at: \n {last_update.strftime("%Y-%m-%d %H:%M")} {last_update.tzname()}',
                target=cur_id,
                style={'font-size': '1.3rem'}
            )
        ])
    return layout
