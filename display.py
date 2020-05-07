from datetime import timedelta

import pandas as pd
import panel as pn
import pygal
from bokeh.models import HoverTool, DatetimeTickFormatter, ColumnDataSource
from bokeh.palettes import Category20
from bokeh.plotting import figure

from analysis import calculate_discrete_derivatives
from data_access import last_date, last_full_date


def add_hover_tool(plot):
    plot.tools.append(HoverTool(tooltips=[
        ("City", "$name"),
        ("Date", "@date{%F}"),
        ("Value", "$y"), ],
        formatters={'@date': 'datetime', }))


def make_graph(df, column):
    p = figure(title=column)
    p.xaxis.formatter = DatetimeTickFormatter()
    add_hover_tool(p)

    source = ColumnDataSource(df.pivot(index='date', columns='combined_name', values=column))
    for palette, city in enumerate(source.column_names):
        if city == 'date': continue  # TODO:  FixMe
        p.line('date', city, name=city,
               legend_label=city, color=Category20[20][palette], source=source, width=2)
    p.legend.location = "top_left"
    return pn.Row(column, pn.pane.Bokeh(p, name=column), name=column)


def column_summary(inframe, column):
    ret = []
    deltas, smoothed_deltas, ddeltas, smoothed_ddeltas, dddeltas, smoothed_dddeltas, predicted_deltas = calculate_discrete_derivatives(
        inframe, column)
    p = figure(title=f'{column}/day', )
    p.xaxis.formatter = DatetimeTickFormatter()
    add_hover_tool(p)
    source = ColumnDataSource(deltas)
    for palette, city in enumerate(source.column_names):
        if city == 'date': continue  # TODO:  FixMe
        p.line('date', city, name=city, legend_label=city,
               color=Category20[len(source.column_names)][palette], source=source, width=2)
    p.legend.location = "top_left"
    ret.append((f'{column}/day', p))

    p = figure(title=f'{column}/day 5 day avg')
    p.xaxis.formatter = DatetimeTickFormatter()
    add_hover_tool(p)
    source = ColumnDataSource(smoothed_deltas)
    source_predicted = ColumnDataSource(predicted_deltas)
    for palette, city in enumerate(source.column_names):
        if city == 'date': continue  # TODO:  FixMe
        p.line('date', city, name=city, legend_label=city,
               color=Category20[len(source.column_names)][palette], source=source, width=2)
    for palette, city in enumerate(source_predicted.column_names):
        if city == 'date': continue  # TODO:  FixMe
        p.line('date', city, name=f'{city} predicted',
               color=Category20[len(source_predicted.column_names)][palette], source=source_predicted,
               width=1, line_dash="dashed")
    p.legend.location = "top_left"
    ret.append((f'{column}/day 5 day avg', p))

    #     p = figure(title=f'{column}/day 5 day avg 2nd order')
    #     p.xaxis.formatter = DatetimeTickFormatter()
    #     add_hover_tool(p)
    #     source = ColumnDataSource(smoothed_ddeltas)
    #     for palette, city in enumerate(city_list):
    #         p.line('date', city, name=city, legend_label=city,
    #                color=Category20[len(city_list)][palette],source=source, width=2)
    #     p.legend.location = "top_left"
    #     tabs.append((f'{column} 2nd order',p))

    summary = pd.DataFrame(smoothed_deltas.loc[last_full_date].sort_values())
    if column.startswith('per_capita'):
        summary['less than 1 in a million'] = summary < 10e-6
    ret.append(pn.pane.DataFrame(summary, name=f'{column} latest avg'))
    return ret


def state_summary(full_df, lookback, label=None):
    sparks = []
    daily_totals = full_df.groupby('date').sum()
    for measure in ['confirmed', 'deaths']:
        chart = pygal.Line()
        chart.add('', daily_totals[measure])

        dchart = pygal.Line()
        dchart.add('', daily_totals[measure].diff().fillna(0))
        sparks.append(pn.Row(
            pn.widgets.StaticText(name=f'{lookback} days {measure}', value=chart.render_sparktext()),
            pn.widgets.StaticText(name=f'diffs', value=dchart.render_sparktext())))

    diag_to_death = pn.widgets.IntSlider(name='Days from diagnosis to death to estimate CFR', value=7, start=1,
                                         end=lookback)

    @pn.depends(diag_to_death)
    def cfr(diag_to_death):
        return pn.widgets.StaticText(name='Case Fatality Rate',
                                     value=daily_totals['deaths'][last_full_date] /
                                           daily_totals['confirmed'][last_date - timedelta(days=diag_to_death)])

    df = full_df.xs(last_full_date, level=1).copy()
    if 'recovered' in df.columns:
        del df['recovered']
    totals = df.sum()
    df['per capita confirmed'] = df['confirmed'] / df['population']
    df['per capita deaths'] = df['deaths'] / df['population']
    for measure in ['population', 'confirmed', 'deaths']:
        df[f'percent of {measure}'] = 100 * df[measure] / totals[measure]
    return pn.Column(
        *sparks,
        cfr,
        diag_to_death,
        '(Not editable in .html reports)',
        pn.widgets.StaticText(name=f'Totals {last_full_date.date()}', value=''),
        totals,
        pn.widgets.StaticText(name='Breakdown', value=''),
        pn.pane.DataFrame(df, width=600),
        name=label)
