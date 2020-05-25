import h2o
import json
import sys
from utils import append_frame_id


def print_module():
    x = {
          'id': 'frame_split',
          'name': 'Split Frames',
          'type': 'FRAME',
          'priority': '220',
          'components': [
            {
              "id": "train_suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id of training data",
              "type": "TEXT",
              "value": "train",
            },
            {
              "id": "valid_suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id of validation data",
              "type": "TEXT",
              "value": "valid",
            },
            {
              "id": "test_suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id of test data",
              "type": "TEXT",
              "value": "test",
            },
            {
              "id": "train_ratio",
              "name": "Ratio (Training)",
              "description": "the ratio for Training Data.",
              "type": "TEXT",
              "value": "70",
            },
            {
              "id": "valid_ratio",
              "name": "Ratio (Validation)",
              "description": "the ratio for Validation Data.",
              "type": "TEXT",
              "value": "15",
            },
            {
              "id": "test_ratio",
              "name": "Ratio (Test)",
              "description": "the ratio for Test Data.",
              "type": "TEXT",
              "value": "15",
            },
            {
              "id": "seed",
              "name": "Seed",
              "description": "RNG seed for initialization.",
              "type": "TEXT",
            },
          ]
        }
    print(json.dumps(x))
    

def main(config):
    h2o_config = config['h2o']
    params = config['parameters']

    h2o.init(url=h2o_config.get('url'))
    frame_id = params.get('frame_id')
    execute(h2o, params, {'frame_id': frame_id})


def execute(h2o, params, config):
    frame_id = config.get('frame_id')

    df = h2o.get_frame(frame_id)

    train = int(params.get('train_ratio'))

    test = params.get('test_ratio')
    if test is None or len(test) == 0:
        test = 0
    else:
        test = int(test)

    valid = params.get('valid_ratio')
    if valid is None or len(valid) == 0:
        valid = 0
    else:
        valid = int(valid)

    seed = params.get('seed')
    if seed is None or len(seed) == 0:
        seed = None
    else:
        seed = int(seed)

    train_ratio = train / (train + test + valid)
    test_ratio = test / (train + test + valid)
    valid_ratio = valid / (train + test + valid)

    if valid == 0 and test == 0:
        return {'frame_id': frame_id}
    elif valid == 0:
        df_train, df_test = df.split_frame(ratios=[train_ratio], seed=seed)
        df_valid = None
    elif test == 0:
        df_train, df_valid = df.split_frame(ratios=[train_ratio], seed=seed)
        df_test = None
    else:
        df_train, df_test, df_valid = df.split_frame(ratios=[train_ratio, test_ratio], seed=seed)

    train_frame_id = append_frame_id(frame_id, params.get('train_suffix'))
    h2o.assign(df_train, train_frame_id)

    if df_test is None:
        test_frame_id = None
    else:
        test_frame_id = append_frame_id(frame_id, params.get('test_suffix'))
        h2o.assign(df_test, test_frame_id)

    if df_valid is None:
        valid_frame_id = None
    else:
        valid_frame_id = append_frame_id(frame_id, params.get('valid_suffix'))
        h2o.assign(df_valid, valid_frame_id)
 
    return {'frame_id': train_frame_id,
            'train_frame_id': train_frame_id,
            'test_frame_id': test_frame_id,
            'valid_frame_id': valid_frame_id,
           }


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)


