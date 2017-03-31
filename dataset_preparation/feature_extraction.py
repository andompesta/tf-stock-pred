__author__ = 'andompesta'

import configparser
import os
import pandas as pd
import utils.extraction_functions as ef


def run(path_conf):
    prop = configparser.ConfigParser()
    prop.read(path_conf)
    companies = ['apple', 'bank_of_america', 'cantel_medical_corp', 'capital_city_bank', 'goldman', 'google',
                 'ICU_medical', 'sunTrust_banks', 'wright_medical_group', 'yahoo']
    header_names = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'Ex-Dividend', 'Split Ratio', 'Adj_Open',
                    'Adj_High',
                    'Adj_Low', 'Adj_Close', 'Adj_Volume']

    path = '../data/stock'

    for company_name in companies:
        full_path = os.path.join(path, company_name) + '.csv'

        data = pd.read_csv(full_path, header=None, parse_dates=True, index_col="Date", names=header_names, skiprows=1)

        print("extract feature of %s" % company_name)

        for i in range(1, 20):
            data.insert(len(data.keys()), 'Close-{}'.format(i), ef.compute_delay(data['Close'], i))
            data.insert(len(data.keys()), 'Open-{}'.format(i), ef.compute_delay(data['Open'], i))
            data.insert(len(data.keys()), 'Low-{}'.format(i), ef.compute_delay(data['Low'], i))
            data.insert(len(data.keys()), "High-{}".format(i), ef.compute_delay(data['High'], i))
            data.insert(len(data.keys()), "Volume-{}".format(i), ef.compute_delay(data['Volume'], i))
            data.insert(len(data.keys()), "Split Ratio-{}".format(i), ef.compute_delay(data['Split Ratio'], i))

        data.insert(len(data.keys()), 'Close+1', ef.predict_value(data['Close']))

        # remove unused feature
        data = ef.remove_unused_key(data, remove_keys=['Adj_Close', 'Adj_Volume', 'Adj_High', 'Adj_Low', 'Adj_Open',
                                                       'Ex-Dividend'])

        # truncate the data accordingly to the value specified
        start_date = pd.Timestamp(prop.get('DATE', 'start_time'))
        end_date = pd.Timestamp(prop.get('DATE', 'end_time'))
        data = ef.truncate_timeseries(data, start_date, end_date)

        ef.check_data(data)

        data.to_csv(os.path.join(path, company_name) + '-fea.csv')


if __name__ == '__main__':
    run('../conf.ini')