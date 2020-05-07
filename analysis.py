from datetime import timedelta

import pandas as pd

from data_access import last_full_date


def calculate_discrete_derivatives(inframe, column):
    df = inframe.pivot(index='date', columns='combined_name', values=column)
    deltas = pd.DataFrame([df[c].diff() for c in df.columns]).transpose()
    deltas.fillna(0, inplace=True)
    smoothed_deltas = deltas.rolling(5).mean()

    ddeltas = pd.DataFrame([smoothed_deltas[c].diff() for c in smoothed_deltas.columns]).transpose()
    ddeltas.fillna(0, inplace=True)
    smoothed_ddeltas = ddeltas.rolling(5).mean()

    dddeltas = pd.DataFrame([smoothed_ddeltas[c].diff() for c in smoothed_ddeltas.columns]).transpose()
    dddeltas.fillna(0, inplace=True)
    smoothed_dddeltas = dddeltas.rolling(5).mean()

    predicted_deltas = pd.DataFrame({last_full_date + timedelta(days=day): smoothed_deltas.loc[last_full_date] +
                                                                           smoothed_ddeltas.loc[last_full_date] * day
                                     for day in range(-7, 7)}).transpose()
    predicted_deltas.index.name = 'date'
    return deltas, smoothed_deltas, ddeltas, smoothed_ddeltas, dddeltas, smoothed_dddeltas, predicted_deltas
