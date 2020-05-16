import json
import h2o
import sys


def print_module():
    x = {
          'id': 'predict_kmeans',
          'name': 'Predict (KMeans)',
          'type': 'PREDICT',
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

    model_id = params.get('model_id')
    pred_model = h2o.get_model(model_id)

    df_pred = pred_model.predict(df[input_columns])
    for col_name in output_columns:
        df_pred[col_name] = df[col_name]

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_pred, dest_frame_id)


def append_frame_id(frame_id, name):
    if frame_id is None:
        return frame_id
    pos = frame_id.rfind('.')
    if pos != -1:
        prefix = frame_id[0:pos]
        suffix = frame_id[pos:]
    else:
        prefix = frame_id
        suffix = ''
    values = prefix.split('_')
    def b64encode(s):
        import base64
        return base64.urlsafe_b64encode(s.encode('utf-8')).decode('utf-8').rstrip('=')
    if len(values) >= 2:
        return values[0] + '_' + values[1] + '_' + b64encode(name) + suffix
    return prefix + '_' + b64encode(name) + suffix


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)


