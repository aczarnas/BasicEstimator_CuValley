from datetime import datetime
from math import sqrt

from pandas import read_csv, DataFrame, merge, to_datetime


def load_temperatures_file(filename: str) -> DataFrame:
    temperature_df = read_csv(filename, sep=';')
    temperature_df = temperature_df.rename(columns={"Czas": "czas"})
    temperature_df['czas'] = to_datetime(temperature_df['czas'].str[:16], format="%Y-%m-%d %H:%M")
    temperature_df['minut_od_epochu'] = ((temperature_df['czas'] - datetime(1970, 1, 1)).dt.total_seconds() / 60).astype('int64')
    return temperature_df


def compare_proper_with_estimated(proper_temperatures: DataFrame, estimated_temperatures: DataFrame):
    combined = merge(left=proper_temperatures, right=estimated_temperatures, on='czas', how='inner')
    combined['blad_kwadratowy'] = (combined['temp_zuz'] - combined['temp_estymowana']) ** 2
    error_sum = combined['blad_kwadratowy'].sum()
    error_count = combined.index.size
    return sqrt(error_sum / error_count)
