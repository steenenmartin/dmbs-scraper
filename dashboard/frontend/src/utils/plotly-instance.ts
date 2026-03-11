// Use the finance-only Plotly build (scatter + candlestick) instead of the full ~3.5 MB bundle.
// plotly.js/dist/plotly-finance is included in the plotly.js package — no extra install needed.
// @ts-expect-error — the finance dist has no separate TS declarations; types come from the main plotly.js package
import PlotlyFinance from "plotly.js/dist/plotly-finance";
import createPlotlyComponent from "react-plotly.js/factory";

export const Plot = createPlotlyComponent(PlotlyFinance as Parameters<typeof createPlotlyComponent>[0]);
