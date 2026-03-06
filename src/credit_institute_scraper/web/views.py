from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import plotly.io as pio

from ..utils.date_helper import get_active_time_range
from .services import (
    build_spot_price_series,
    constrained_options,
    get_filtered_prices,
    get_master_data,
    latest_timestamp,
    make_ohlc_figure,
    make_spot_prices_figure,
    make_spot_rates_figure,
    options_for,
    query_df,
)

FILTER_KEYS = ['institute', 'coupon_rate', 'years_to_maturity', 'max_interest_only_period']


def _spot_filters(request) -> dict[str, list[str] | None]:
    filters: dict[str, list[str] | None] = {}
    for key in FILTER_KEYS:
        values = [v for v in request.GET.getlist(key) if v]
        filters[key] = values or None
    return filters


def _normalize_filter_values(filters: dict[str, list[str] | None], options: dict[str, list[str]]) -> dict[str, list[str] | None]:
    clean: dict[str, list[str] | None] = {}
    for key, values in filters.items():
        if not values:
            clean[key] = None
            continue
        allowed = set(options.get(key, []))
        kept = [v for v in values if v in allowed]
        clean[key] = kept or None
    return clean


def home(request):
    return render(request, 'web/home.html')


def prices(request):
    start_utc, end_utc = get_active_time_range(force_9_17=True)
    master_data = get_master_data(start_utc=start_utc, end_utc=end_utc)
    filters = _spot_filters(request)

    dynamic_options = constrained_options(master_data, filters)
    filters = _normalize_filter_values(filters, dynamic_options)

    filtered_prices = get_filtered_prices(master_data, filters, start_utc=start_utc, end_utc=end_utc)
    fig = make_spot_prices_figure(filtered_prices, start_utc=start_utc, end_utc=end_utc)

    context = {
        'title': 'Fixed loan prices',
        'plot': pio.to_html(fig, full_html=False, include_plotlyjs=True, config={'responsive': True, 'displayModeBar': False}),
        'filters': filters,
        'options': constrained_options(master_data, filters),
        'auto_apply': True,
        'is_spot_prices_page': True,
        'poll_url': '/prices/poll/',
        'poll_since': latest_timestamp(filtered_prices) or '',
    }
    return render(request, 'web/graph_page.html', context)


def prices_poll(request):
    start_utc, end_utc = get_active_time_range(force_9_17=True)
    master_data = get_master_data(start_utc=start_utc, end_utc=end_utc)
    filters = _spot_filters(request)
    since = request.GET.get('since')

    rows = get_filtered_prices(master_data, filters, start_utc=start_utc, end_utc=end_utc, since=since)
    series = build_spot_price_series(rows)

    return JsonResponse(
        {
            'series': series,
            'latest_timestamp': latest_timestamp(rows),
            'row_count': int(len(rows)),
        }
    )


def rates(request):
    fig = make_spot_rates_figure()
    return render(
        request,
        'web/graph_page.html',
        {'title': 'Flex loan rates', 'plot': pio.to_html(fig, full_html=False, include_plotlyjs=True, config={'responsive': True, 'displayModeBar': False}), 'filters': {}, 'options': {}, 'auto_apply': False},
    )


def ohlc(request):
    master_data = get_master_data()
    isin = request.GET.get('isin')
    fig = make_ohlc_figure(isin)
    return render(
        request,
        'web/graph_page.html',
        {
            'title': 'OHLC prices',
            'plot': pio.to_html(fig, full_html=False, include_plotlyjs=True, config={'responsive': True, 'displayModeBar': False}),
            'filters': {'isin': [isin] if isin else None},
            'options': {'isin': options_for(master_data, 'isin')},
            'auto_apply': True,
        },
    )


def export_csv(request):
    data = query_df('select * from prices order by timestamp desc')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="BondstatsExport.csv"'
    response.write(data.to_csv(index=False))
    return response
