import h2o
import json
import sys
from utils import append_frame_id


def print_module():
    x = {
          'id': 'frame_floor',
          'name': 'Apply Floor Func',
          'type': 'FRAME',
          'priority': '800',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "floor",
            },
            {
              "id": "columns",
              "name": "Columns",
              "description": "the columns included in the created frame",
              "type": "MULTICOLUMN",
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

    columns = params.get('columns')
    if columns is not None or len(columns) > 2:
        columns = json.loads(columns)
        df = df[columns]

    df_floor = df.floor()

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_floor, dest_frame_id)

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


