import json
import h2o
import sys
from utils import append_frame_id


def print_module():
    x = {
          'id': 'predict_kmeans',
          'name': 'Predict (KMeans)',
          'type': 'PREDICT',
          'priority': '100',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "kmeans",
            },
            {
              "id": "input_columns",
              "name": "Input Columns",
              "description": "the columns for the input frame",
              "type": "MULTICOLUMN",
            },
            {
              "id": "output_columns",
              "name": "Output Columns",
              "description": "the column to append them to the output frame",
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
    model_id = params.get('model_id')
    execute(h2o, params, {'frame_id':frame_id, 'model_id':model_id})


def execute(h2o, params, config):
    frame_id = config.get('frame_id')
    model_id = config.get('model_id')
    
    df = h2o.get_frame(frame_id)

    input_columns=params.get("input_columns")
    if input_columns is None or len(input_columns) <= 2:
        input_columns = df.col_names
    else:
        input_columns = json.loads(input_columns)

    output_columns=params.get("output_columns")
    if output_columns is None or len(output_columns) <= 2:
        output_columns = []
    else:
        output_columns = json.loads(output_columns)

    pred_model = h2o.get_model(model_id)

    df_pred = pred_model.predict(df[input_columns])
    for col_name in output_columns:
        df_pred[col_name] = df[col_name]

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_pred, dest_frame_id)

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


