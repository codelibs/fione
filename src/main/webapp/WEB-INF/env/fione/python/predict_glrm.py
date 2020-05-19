import h2o
import sys

def print_module():
    x = {
          'id': 'predict_glrm',
          'name': 'Predict (GLRM)',
          'type': 'PREDICT',
          'priority': '300',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the predicted frame id",
              "type": "TEXT",
              "value": "glrm",
            },
            {
              "id": "column_header",
              "name": "Column Header",
              "description": "Column number(s) to use as the row names",
              "type": "TEXT",
            },
            {
              "id": "topn_output",
              "name": "Top N Output",
              "description": "Create the frame of top N columns",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "topn_percent",
              "name": "Top N Percent",
              "description": "a top percentage of the column values to return",
              "type": "TEXT",
              "value": "10",
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
    df = h2o.get_frame(frame_id)
    column_header = params.get('column_header')
    if len(column_header) > 0:
        df_head = df[:int(column_header)]
        df = df[int(column_header):]

    model_id = params.get('model_id')
    pred_model = h2o.get_model(model_id)

    df_pred = pred_model.predict(df)
    df_pred.columns = [x[len('reconstr_'):] for x in df_pred.columns]

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))

    if bool(params.get('topn_output')):
        df_topn = get_topN(df_pred, int(params.get('topn_percent')))
        if df_head is not None:
            df_topn = df_head.cbind(df_topn)
        h2o.assign(df_topn, dest_frame_id)
        h2o.remove(str(df_pred.frame_id))
    else:
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


def get_topN(df, nPercent=10):
    df_transpose = df.transpose()
    i = 0
    c = 'Original_Row_Indices'
    data = [df.columns[x] for x in df_transpose.topN(column=i, nPercent=nPercent).as_data_frame()[c].values]
    df_new = h2o.H2OFrame(data,
                          column_names=[f'{i}'])

    size = df.shape[0]
    for i in range(1, df.shape[0]):
        data = [df.columns[x] for x in df_transpose.topN(column=i, nPercent=nPercent).as_data_frame()[c].values]
        df_new[f'{i}'] = h2o.H2OFrame(data)
        if i % 100 == 0:
            send_progress(i/size, f'Process top N rows ({i}/{size})')

    return df_new.transpose()


def send_progress(progress, message):
    import json
    x = json.dumps({
        'type': 'progress',
        'progress': progress,
        'message': message
      })
    print(f'FIONE:{x}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)


