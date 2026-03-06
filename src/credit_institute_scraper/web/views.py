from __future__ import annotations

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
import plotly.io as pio

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


def _spot_filters(request) -> dict[str, str | None]:
    return {
        'institute': request.GET.get('institute'),
        'coupon_rate': request.GET.get('coupon_rate'),
        'years_to_maturity': request.GET.get('years_to_maturity'),
        'max_interest_only_period': request.GET.get('max_interest_only_period'),
        'isin': request.GET.get('isin'),
    }


def home(request):
    return render(request, 'web/home.html')


def prices(request):
    master_data = get_master_data()
    filters = _spot_filters(request)

    dynamic_options = constrained_options(master_data, filters)
    for key, value in list(filters.items()):
        if value and value not in dynamic_options[key]:
            filters[key] = None

    filtered_prices = get_filtered_prices(master_data, filters)
    fig = make_spot_prices_figure(filtered_prices)

    context = {
        'title': 'Fixed loan prices',
        'plot': pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={'responsive': True, 'displayModeBar': False}),
        'filters': filters,
        'options': constrained_options(master_data, filters),
        'auto_apply': True,
        'is_spot_prices_page': True,
        'poll_url': '/prices/poll/',
        'poll_since': latest_timestamp(filtered_prices) or '',
    }
    return render(request, 'web/graph_page.html', context)


def prices_poll(request):
    master_data = get_master_data()
    filters = _spot_filters(request)
    since = request.GET.get('since')

    rows = get_filtered_prices(master_data, filters, since=since)
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
        {'title': 'Flex loan rates', 'plot': pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={'responsive': True, 'displayModeBar': False}), 'filters': {}, 'options': {}, 'auto_apply': False},
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
            'plot': pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={'responsive': True, 'displayModeBar': False}),
            'filters': {'isin': isin},
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
