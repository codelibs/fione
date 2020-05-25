import h2o
import json
import sys
from utils import append_frame_id


def print_module():
    x = {
          'id': 'frame_cor',
          'name': 'Compute Correlation',
          'type': 'FRAME',
          'priority': '900',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "cor",
            },
            {
              "id": "columns",
              "name": "Columns",
              "description": "the columns included in the created frame",
              "type": "MULTICOLUMN",
            },
            {
              "id": "method",
              "name": "Method",
              "description": "Which method to use",
              "type": "SELECT",
              "options": ["Pearson", "Spearman"],
              "value": "Pearson",
            },
            {
              "id": "use",
              "name": "Use",
              "description": "A string indicating how to handle missing values.",
              "type": "SELECT",
              "options": ["", "everything", "all.obs", "complete.obs"],
              "value": "",
            },
            {
              "id": "na_rm",
              "name": "Remove NA",
              "description": "an alternative to use when this is True then default value for use is everything; and if False then default use is complete.obs. This parameter has no effect if use is given explicitly.",
              "type": "BOOL",
              "value": "false",
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
    if columns is not None and len(columns) > 2:
        columns = json.loads(columns)
        df = df[columns]

    use_value = params.get('use')
    if use_value is not None and len(use_value) == 0:
        use_value = None
    df_cor = df.cor(na_rm=bool(params.get('na_rm')),
                    use=use_value,
                    method=params.get('method'))

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_cor, dest_frame_id)

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


