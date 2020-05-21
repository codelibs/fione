import h2o
import json
import sys
from utils import append_frame_id, parse_row_condition


def print_module():
    x = {
          'id': 'frame_filter',
          'name': 'Filter Frame',
          'type': 'FRAME',
          'priority': '100',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "filtered",
            },
            {
              "id": "selected_columns",
              "name": "Column Filter",
              "description": "the columns included in the created frame",
              "type": "MULTICOLUMN",
            },
            {
              "id": "row_conditions",
              "name": "Row Filter",
              "description": "the filter condition for rows",
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

    row_conditions = params.get('row_conditions')
    if row_conditions is not None and len(row_conditions) > 0:
        mask = parse_row_condition(df, row_conditions)
        df = df[mask, :]

    columns = params.get('selected_columns')
    if columns is None or len(columns) <= 2:
        columns = df.columns
    else:
        columns = json.loads(columns)

    df_filtered = df[columns]

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_filtered, dest_frame_id)

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


