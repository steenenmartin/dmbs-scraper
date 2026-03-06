from __future__ import annotations

from django.http import HttpResponse
from django.shortcuts import render
import plotly.io as pio

from .services import (
    constrained_options,
    filter_data,
    get_master_data,
    make_ohlc_figure,
    make_spot_prices_figure,
    make_spot_rates_figure,
    options_for,
    query_df,
)


def home(request):
    return render(request, 'web/home.html')


def prices(request):
    master_data = get_master_data()
    filters = {
        'institute': request.GET.get('institute'),
        'coupon_rate': request.GET.get('coupon_rate'),
        'years_to_maturity': request.GET.get('years_to_maturity'),
        'max_interest_only_period': request.GET.get('max_interest_only_period'),
        'isin': request.GET.get('isin'),
    }

    dynamic_options = constrained_options(master_data, filters)

    # Clean impossible selections when other filters constrain the option space.
    for key, value in list(filters.items()):
        if value and value not in dynamic_options[key]:
            filters[key] = None

    filtered_master = filter_data(master_data, filters)
    price_df = query_df('select * from prices')
    filtered_prices = price_df[price_df['isin'].isin(filtered_master['isin'].unique())]

    fig = make_spot_prices_figure(filtered_prices)
    context = {
        'title': 'Fixed loan prices',
        'plot': pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={'responsive': True, 'displayModeBar': False}),
        'filters': filters,
        'options': constrained_options(master_data, filters),
        'auto_apply': True,
    }
    return render(request, 'web/graph_page.html', context)


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
