import h2o
import sys
from utils import append_frame_id


def print_module():
    x = {
          'id': 'frame_pivot',
          'name': 'Pivot Tables',
          'type': 'FRAME',
          'priority': '180',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "pivot",
            },
            {
              "id": "index",
              "name": "Index",
              "description": "the column where pivoted rows should be aligned on",
              "type": "COLUMN",
            },
            {
              "id": "column",
              "name": "Column",
              "description": "the column to pivot",
              "type": "COLUMN",
            },
            {
              "id": "value",
              "name": "Value",
              "description": "values of the pivoted table",
              "type": "COLUMN",
            },
          ]
        }
    import json
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

    df_pivot = df.pivot(index=params.get('index'), column=params.get('column'), value=params.get('value'))

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_pivot, dest_frame_id)

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


