import h2o
import json
import sys
from utils import append_frame_id, parse_row_condition, to_bool


def print_module():
    x = {
          'id': 'frame_sort',
          'name': 'Sort Column',
          'type': 'FRAME',
          'priority': '210',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "sort",
            },
            {
              "id": "column",
              "name": "Column",
              "description": "the target column to sort values",
              "type": "COLUMN",
            },
            {
              "id": "ascending",
              "name": "Ascending",
              "description": "True for ascending sort and False for descending sort.",
              "type": "BOOL",
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

    column = params.get('column')
    ascending = to_bool(params.get('ascending'))

    df_sort = df.sort(by=[column], ascending=[ascending])

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_sort, dest_frame_id)

    return {'frame_id': dest_frame_id}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)

