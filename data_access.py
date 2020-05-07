from datetime import timedelta

import pandas as pd
import pymongo
from pymongo import MongoClient

MDB_URL = "mongodb+srv://readonly:readonly@covid-19.hip2i.mongodb.net/covid19"
client = MongoClient(MDB_URL)
db = client.get_database("covid19")
stats = db.get_collection("global_and_us")
metadata = db.get_collection("metadata")

# Get info about the last available date
meta = metadata.find_one()
last_date = meta["last_date"]
last_full_date = last_date - timedelta(days=1)

EARTH_RADIUS = 6371.0  # This is used in the $geoWithin query later.

def snag_data(columns=("date", "confirmed", "deaths", 'state'), **filters):
    df = pd.DataFrame(
        stats.find(filters)
            .sort("state", pymongo.DESCENDING)
    )
    if 'uid' in df.columns:
        del df['uid']
    if 'fips' in df.columns:
        del df['fips']
    if 'country_code' in df.columns:
        del df['country_code']
    df['deaths'] = df['deaths'].astype('Int64')
    df['confirmed'] = df['confirmed'].astype('Int64')
    df['population'] = df['population'].astype('Int64')
    return df


def get_for_country_day(country='US', stat_date=None, **filters):
    if stat_date is None:
        stat_date = last_date

    filters.update({'country': country, "date": stat_date})
    return snag_data(**filters)


def near_by_data(query_date=None, longitude=-74.114202, latitude=40.6737968, distance_km=250.0, group_by='state'):
    if query_date is None:
        query_date = last_full_date
    results = stats.find(
        {
            "date": query_date,
            "loc": {
                "$geoWithin": {
                    "$centerSphere": [[longitude, latitude], distance_km / EARTH_RADIUS]
                }
            },
        }
    )
    df = pd.DataFrame(results)
    if df.empty:
        return df
    df = df.groupby(group_by).sum()
    del df['uid']
    del df['fips']
    del df['country_code']
    df['per_capita_deaths'] = df['deaths'] / df['population']
    df['per_capita_confirmed'] = df['confirmed'] / df['population']
    return df


