import h2o
import json
import sys
from utils import append_frame_id


def print_module():
    x = {
          'id': 'frame_fillna',
          'name': 'Fill NA',
          'type': 'FRAME',
          'priority': '120',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "fillna",
            },
            {
              "id": "method",
              "name": "Method",
              "type": "SELECT",
              "options": ["forward", "backward"],
              "value": "forward",
            },
            {
              "id": "axis",
              "name": "Axis",
              "description": "0 for columnar-wise or 1 for row-wise fill",
              "type": "SELECT",
              "options": ["0", "1"],
              "value": "0",
            },
            {
              "id": "maxlen",
              "name": "Max Len",
              "description": "Max number of consecutive NA’s to fill",
              "type": "TEXT",
              "value": "1",
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

    df_fillna = df.fillna(method=params.get('method'),
                          axis=int(params.get('axis')),
                          maxlen=int(params.get('maxlen')))

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_fillna, dest_frame_id)

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


