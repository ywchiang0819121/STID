import argparse
import pickle
import shutil
import numpy as np
import os
import pandas as pd

"""
PEMS-BAY dataset (traffic speed dataset) default settings:
    - normalization:
        standard norm
    - dataset division: 
        7:1:2
    - windows size:
        12
    - features:
        traffic speed
        time in day
        day in week
    - target:
        predicting the traffic speed
"""

def standard_transform(data: np.array, output_dir: str, train_index: list) -> np.array:
    """standard normalization.

    Args:
        data (np.array): raw time series data.
        output_dir (str): output dir path.
        train_index (list): train index.

    Returns:
        np.array: normalized raw time series data.
    """
    # data: L, N, C
    data_train  = data[:train_index[-1][1], ...]
    
    Min, Max   = data_train[..., 0].min(), data_train[..., 0].max()

    print("Min (training data):", Min)
    print("Max (training data):", Max)
    scaler = {}
    scaler['func'] = re_max_min_normalization.__name__
    scaler['args'] = {"min":Min, "max":Max}
    pickle.dump(scaler, open(output_dir + "/scaler.pkl", 'wb'))
    
    def normalize(x):
        return (x - Min) / (Max-Min)
    
    data_norm = normalize(data)
    return data_norm

def re_max_min_normalization(x, **kwargs):
    _min, _max = kwargs['min'], kwargs['max']
    x = (x + 1.) / 2.
    x = 1. * x * (_max - _min) + _min
    return x

def generate_data(args):
    """preprocess and generate train/valid/test datasets.

    Args:
        args (Namespace): args for processing data.
    """
    C = args.C
    future_seq_len  = args.future_seq_len
    history_seq_len = args.history_seq_len
    add_time_in_day = True
    add_day_in_week = args.dow
    output_dir      = args.output_dir

    # read data
    data = np.load('data/2021_2way.npz')['x']
    # df   = pd.read_hdf(args.data_file_path)
    # data = np.expand_dims(df.values, axis=-1)

    data = data[..., C]
    print("Data shape: {0}".format(data.shape))

    L, N, F = data.shape
    num_samples     = L - (history_seq_len + future_seq_len) + 1
    train_num_short = round(num_samples * train_ratio)
    valid_num_short = round(num_samples * valid_ratio)
    test_num_short  = num_samples - train_num_short - valid_num_short
    print("train_num_short:{0}".format(train_num_short))
    print("valid_num_short:{0}".format(valid_num_short))
    print("test_num_short:{0}".format(test_num_short))

    index_list = []
    for i in range(history_seq_len, num_samples + history_seq_len):
        index = (i-history_seq_len, i, i+future_seq_len)
        index_list.append(index)

    train_index = index_list[:train_num_short]
    valid_index = index_list[train_num_short: train_num_short + valid_num_short]
    test_index  = index_list[train_num_short + valid_num_short: train_num_short + valid_num_short + test_num_short]
    
    scaler      = standard_transform
    data_norm   = scaler(data, output_dir, train_index)

    # add external feature
    feature_list = [data_norm]
    if add_time_in_day:
        # numerical time_in_day
        time_ind    = (np.load('./data/time.npz')['x'][:,1]-1) / 24
        time_in_day = np.tile(time_ind, [1, N, 1]).transpose((2, 1, 0))
        feature_list.append(time_in_day)

    if add_day_in_week:
        # numerical day_in_week
        dow = (np.load('./data/time.npz')['x'][:,0]-1) / 7
        dow_tiled = np.tile(dow, [1, N, 1]).transpose((2, 1, 0))
        feature_list.append(dow_tiled)

    raw_data = np.concatenate(feature_list, axis=-1)
    print("raw_data shape: {0}".format(raw_data.shape))

    # dump data
    index = {}
    index['train'] = train_index
    index['valid'] = valid_index
    index['test']  = test_index
    pickle.dump(index, open(output_dir + "/index.pkl", "wb"))

    data = {}
    data['raw_data'] = raw_data
    pickle.dump(data, open(output_dir + "/data.pkl", "wb"))
    # copy adj
    # shutil.copyfile(args.graph_file_path, output_dir + '/adj_mx.pkl')      # copy models

if __name__ == "__main__":
    history_seq_len = 12                    # sliding window size for generating history sequence and target sequence
    future_seq_len  = 12
    
    train_ratio     = 0.7
    valid_ratio     = 0.1
    C               = [0, 1]                   # selected channels

    name            = "BAST"
    dow             = True                  # if add day_of_week feature
    output_dir      = 'datasets/' + name
    data_file_path  = 'datasets/raw_data/{0}/{1}.h5'.format(name, name)
    graph_file_path = 'datasets/raw_data/{0}/adj_{1}.pkl'.format(name, name)
    
    parser  = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default=output_dir, help="Output directory.")
    parser.add_argument("--data_file_path", type=str, default=data_file_path, help="Raw traffic readings.")
    parser.add_argument("--graph_file_path", type=str, default=graph_file_path, help="Raw traffic readings.")
    parser.add_argument("--history_seq_len", type=int, default=history_seq_len, help="Sequence Length.")
    parser.add_argument("--future_seq_len", type=int, default=future_seq_len, help="Sequence Length.")
    parser.add_argument("--dow", type=bool, default=dow, help='Add feature day_of_week.')
    parser.add_argument("--C", type=list, default=C, help='Selected channels.')
    parser.add_argument("--train_ratio", type=float, default=train_ratio, help='Train ratio')
    parser.add_argument("--valid_ratio", type=float, default=valid_ratio, help='Validate ratio.')
    
    args = parser.parse_args()
    if os.path.exists(args.output_dir):
        reply = str(input(f'{args.output_dir} exists. Do you want to overwrite it? (y/n)')).lower().strip()
        if reply[0] != 'y': exit
    else:
        os.makedirs(args.output_dir)
    generate_data(args)
