from argparse import ArgumentParser
from datetime import datetime
from os import listdir
from os.path import isdir, exists, join as path_join
from gzip import open as open_gzip
from pandas import read_csv, concat, to_datetime, DataFrame

from testing_methods import load_temperatures_file, compare_proper_with_estimated


def start_release_value(row_epoch: int):
    time_from_start = (row_epoch + 420) % 480
    if time_from_start == 0:
        return 1.124
    if time_from_start <= 60:
        return 0.764
    if time_from_start <= 120:
        return -1.416
    if time_from_start <= 180:
        return 0.317
    if time_from_start <= 240:
        return -0.403
    if time_from_start <= 300:
        return -0.103
    if time_from_start <= 360:
        return 0.129
    return -0.403


params = [1287.1, 0.597, -0.095, -0.067, 0.022, 0.007]


def temperature_estimator(input_batch_sum: float, dust_flow: float, roasted_input: float, energy: float, energy_balance: float) -> float:
    if dust_flow == 0:
        dust_result = 1
    else:
        dust_result = dust_flow ** params[2]
    if roasted_input == 0:
        roaster_result = 1
    else:
        roaster_result = roasted_input ** params[3]
    return params[0] + input_batch_sum ** params[1] + dust_result + roaster_result - energy ** params[4] - energy_balance ** params[5]


def prepare_input_data(data_frames: list) -> DataFrame:
    result_df = None

    for frame in data_frames:
        if result_df is not None:
            result_df = concat([result_df, frame])
        else:
            result_df = frame

    result_df['czas'] = to_datetime(result_df['czas'].str[:16], format="%Y-%m-%d %H:%M")
    result_df['minut_od_epochu'] = ((result_df['czas'] - datetime(1970, 1, 1)).dt.total_seconds() / 60).astype('int64')
    result_df = result_df.sort_values(by=['minut_od_epochu'])

    result_df['sumaryczna_moc_cieplna_w_MW'] = result_df['001nir0szr0.daca.pv']

    temp_to_average = [f'001tix010{n}.daca.pv' for n in range(63, 87)]
    result_df['sr_temp_K_pod_2_warstwa_wymorowki'] = (result_df[temp_to_average].sum(axis=1) + 273.15) / 24

    flow_columns_to_sum = [f'001fir013{n:02d}.daca.pv' for n in range(7, 14)] + ['001fir01315.daca.pv']
    result_df['suma_ciepla_wch'] = result_df[flow_columns_to_sum].sum(axis=1) * ((result_df['037tix00254.daca.pv'] + result_df['037tix00264.daca.pv']) / 2 + 273.15)

    result_df['suma_ciepla_wych'] = result_df['001fir01307.daca.pv'] * (result_df['001tir01357.daca.pv'] + 273.15) + \
                                    result_df['001fir01308.daca.pv'] * (result_df['001tir01358.daca.pv'] + 273.15) + \
                                    result_df['001fir01309.daca.pv'] * (result_df['001tir01359.daca.pv'] + 273.15) + \
                                    result_df['001fir01310.daca.pv'] * (result_df['001tir01360.daca.pv'] + 273.15) + \
                                    result_df['001fir01311.daca.pv'] * (result_df['001tir01361.daca.pv'] + 273.15) + \
                                    result_df['001fir01312.daca.pv'] * (result_df['001tir01362.daca.pv'] + 273.15) + \
                                    result_df['001fir01313.daca.pv'] * (result_df['001tir01363.daca.pv'] + 273.15) + \
                                    result_df['001fir01315.daca.pv'] * (result_df['001tir01365.daca.pv'] + 273.15)

    result_df['bilans_ciepla_wych_minus_wch'] = result_df['suma_ciepla_wych'] - result_df['suma_ciepla_wch']

    columns = result_df.columns.tolist()
    columns = columns[0:1] + columns[-6:-5] + columns[1:5] + columns[-5:-3] + columns[-1:]
    result_df = result_df[columns]

    return result_df


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--path-to-data', dest='data_path', type=str, required=True,
                        help='Path to directory with source data for simulation')
    parser.add_argument('--path-to-test-file', dest='test_file_path', type=str, required=True,
                        help='Path to test file with temperatures data')

    args = parser.parse_args()
    data_path = args.data_path
    test_file_path = args.test_file_path
    if not isdir(data_path) or not exists(test_file_path):
        print("Invalid parameters, check all values")
        parser.print_help()
        exit(1)

    print("Extracting and loading data to memory")
    input_dfs = []
    for f in listdir(data_path):
        if '.gz' not in f:
            continue
        with open_gzip(path_join(data_path, f), 'r') as unzipped:
            input_dfs.append(read_csv(unzipped))

    merged = prepare_input_data(input_dfs)

    estimated_temperatures = []
    for i in range(merged.index.size):
        current_row = merged.iloc[i]
        estimated_temperatures.append(temperature_estimator(input_batch_sum=(current_row['001fcx00211.pv'] + current_row['001fcx00221.pv']),
                                                            dust_flow=current_row['001fcx00231.pv'],
                                                            roasted_input=current_row['001fcx00241.pv'],
                                                            energy=current_row['sumaryczna_moc_cieplna_w_MW'],
                                                            energy_balance=current_row['bilans_ciepla_wych_minus_wch']))

    merged['temp_estymowana'] = estimated_temperatures

    proper_temperatures_df = load_temperatures_file(test_file_path)

    print("Średni błąd kwadratowy danych estymowanych do danych testowych")
    print(compare_proper_with_estimated(proper_temperatures_df, merged))
