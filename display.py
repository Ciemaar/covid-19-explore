from datetime import timedelta
from os import environ

import pandas as pd
import panel as pn
import pygal
from bokeh.models import HoverTool, DatetimeTickFormatter, ColumnDataSource
from bokeh.palettes import viridis
from bokeh.plotting import figure
import colorcet as cc

from analysis import calculate_discrete_derivatives
from data_access import last_date, last_full_date


def add_hover_tool(plot):
    plot.tools.append(HoverTool(tooltips=[
        ("City", "$name"),
        ("Date", "@date{%F}"),
        ("Value", "$y"), ],
        formatters={'@date': 'datetime', }))


def make_graph(df, title, extra_df=None, extra_suffix='', warm=None):
    p = figure(title=title)
    p.xaxis.formatter = DatetimeTickFormatter()
    add_hover_tool(p)

    source = ColumnDataSource(df)
    for palette, city in enumerate(source.column_names):
        if city == 'date': continue  # TODO:  FixMe
        p.line('date', city, name=city,
               legend_label=city, 
               color=(cc.glasbey_warm+cc.glasbey_cool if warm is not None and warm[city] else cc.glasbey_cool+cc.glasbey_warm)[palette], 
               source=source, width=2)
    if extra_df is not None:
        extra_source = ColumnDataSource(extra_df)
        for palette, city in enumerate(extra_source.column_names):
            if city == 'date': continue  # TODO:  FixMe
            p.line('date', city, name=f'{city} {extra_suffix}',
                   color=(cc.glasbey_warm+cc.glasbey_cool if warm is not None and warm[city] else cc.glasbey_cool+cc.glasbey_warm)[palette], 
                   source=extra_source, width=1, line_dash="dashed")
    p.legend.location = "top_left"
    return pn.pane.Bokeh(p, name=title)


def column_summary(inframe, column, rolling_avg=5,cfr=None):
    ret = []
    deltas, smoothed_deltas, ddeltas, smoothed_ddeltas, dddeltas, smoothed_dddeltas, predicted_deltas = calculate_discrete_derivatives(inframe, column, rolling_avg=rolling_avg)
    ret.append(make_graph(deltas, f'{column}/day'))
    ret.append(make_graph(smoothed_deltas, f'{column}/day {rolling_avg} day avg', predicted_deltas, 'predicted'))

    summary = pd.DataFrame(smoothed_deltas.loc[last_full_date].sort_values())
    if column.startswith('per_capita'):
        summary['less than 1 in a million'] = summary < 10e-6
    ret.append(pn.pane.DataFrame(summary, name=f'{column} latest avg'))
    return ret


def state_summary(full_df, lookback, label=None, group_by='combined_name', cfr_widget=None):
    if cfr_widget is None:
        cfr_widget = pn.widgets.StaticText(name='Case Fatality Rate')
    sparks = []
    daily_totals = full_df.groupby('date').sum()
    full_df['per capita confirmed'] = full_df['confirmed'] / full_df['population']
    full_df['per capita deaths'] = full_df['deaths'] / full_df['population']
    

    for measure in ['confirmed', 'deaths']:         
        chart = pygal.Line()
        chart.add('', daily_totals[measure])

        dchart = pygal.Line()
        dchart.add('', daily_totals[measure].diff().fillna(0))
        sparks.append(pn.Row(
            pn.widgets.StaticText(name=f'{lookback} days {measure}', value=chart.render_sparktext()),
            pn.widgets.StaticText(name=f'diffs', value=dchart.render_sparktext())))

    diag_to_death = pn.widgets.IntSlider(name='Days from diagnosis to death to estimate CFR', value=7, start=1,
                                         end=lookback, disabled='STATIC_REPORT' in environ)

    @pn.depends(diag_to_death)
    def cfr(diag_to_death):
        nonlocal cfr_widget
        cfr_widget.value =  daily_totals['deaths'][last_full_date] / daily_totals['confirmed'][last_date - timedelta(days=diag_to_death)]
        return cfr_widget

    df = full_df.xs(last_full_date, level=1).copy()
    if 'recovered' in df.columns:
        del df['recovered']
    totals = df.sum()

    full_df.reset_index(inplace=True)
    observed = pn.Tabs(dynamic=False)
    rolling_avg=5
    for column in ['deaths', 'per capita deaths', 'confirmed', 'per capita confirmed']:
        deltas, smoothed_deltas, ddeltas, smoothed_ddeltas, dddeltas, smoothed_dddeltas, predicted_deltas = calculate_discrete_derivatives(full_df, column, rolling_avg=rolling_avg, group_by=group_by)
        observed.append(make_graph(smoothed_deltas, f'{column}/day {rolling_avg} day avg', 
                                   predicted_deltas, 'predicted',
                                  #warm=smoothed_ddeltas.loc[last_full_date]>0
                                  ))

        observed.append(make_graph(full_df.pivot(index='date', columns=group_by,
                                                 values=column), column))

    for measure in ['population', 'confirmed', 'deaths']:
        df[f'percent of {measure}'] = 100 * df[measure] / totals[measure]
    return pn.Column(
        *sparks,
        cfr,
        diag_to_death,
        '(Not editable in .html reports)',
        pn.widgets.StaticText(name=f'Totals {last_full_date.date()}', value=''),
        totals,
        observed,
        pn.widgets.StaticText(name='Breakdown', value=''),
        pn.pane.DataFrame(df, width=600),
        name=label)
