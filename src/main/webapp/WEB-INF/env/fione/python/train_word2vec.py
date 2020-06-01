import h2o
import sys
from utils import save_model, append_frame_id, to_bool


def print_module():
    x = {
          'id': 'train_word2vec',
          'name': 'Run Word2Vec',
          'type': 'TRAIN',
          'priority': '300',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Model Set)",
              "description": "the suffix for the created model set",
              "type": "TEXT",
              "value": "word2vec",
            },
            {
              "id": "is_transform",
              "name": "Transform",
              "description": "Convert to word vectors",
              "type": "BOOL",
              "value": "true",
            },
            {
              "id": "transform_suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame",
              "type": "TEXT",
              "value": "word2vec",
            },
            {
              "id": "epochs",
              "name": "Epoch",
              "description": "Number of training iterations to run",
              "type": "TEXT",
              "value": "5",
            },
            {
              "id": "init_learning_rate",
              "name": "Init Learning Rate",
              "description": "Set the starting learning rate",
              "type": "TEXT",
              "value": "0.025",
            },
            {
              "id": "max_runtime_secs",
              "name": "Max Runtime Secs",
              "description": "Maximum allowed runtime in seconds for model training. Use 0 to disable.",
              "type": "TEXT",
              "value": "0",
            },
            {
              "id": "min_word_freq",
              "name": "Min Word Freq",
              "description": "This will discard words that appear less than <int> times",
              "type": "TEXT",
              "value": "5",
            },
            # norm_model
            {
              "id": "sent_sample_rate",
              "name": "Sent Sample Rate",
              "description": "Set threshold for occurrence of words. Those that appear with higher frequency in the training data will be randomly down-sampled; useful range is (0, 1e-5)",
              "type": "TEXT",
              "value": "0.001",
            },
            {
              "id": "vec_size",
              "name": "Vec Size",
              "description": "Set size of word vectors ",
              "type": "TEXT",
              "value": "100",
            },
            {
              "id": "window_size",
              "name": "Window Size",
              "description": "Set max skip length between words",
              "type": "TEXT",
              "value": "5",
            },
            # word_model
            {
              "id": "aggregate_method",
              "name": "Aggregate Method",
              "description": "Specifies how to aggregate sequences of words",
              "type": "SELECT",
              "options": ["NONE", "AVERAGE"],
              "value": "AVERAGE",
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

    from h2o.estimators import H2OWord2vecEstimator
    w2v_model = H2OWord2vecEstimator(epochs=int(params.get('epochs')),
                                     init_learning_rate=float(params.get('init_learning_rate')),
                                     max_runtime_secs=float(params.get('max_runtime_secs')),
                                     min_word_freq=int(params.get('min_word_freq')),
                                     sent_sample_rate=float(params.get('sent_sample_rate')),
                                     vec_size=int(params.get('vec_size')),
                                     window_size=int(params.get('window_size')))

    w2v_model.train(training_frame=df)

    save_model(params, w2v_model.model_id)

    is_transform = params.get("is_transform")
    if is_transform is not None and to_bool(is_transform):
        df_vecs = w2v_model.transform(df, aggregate_method=params.get('aggregate_method'))
        dest_frame_id = append_frame_id(frame_id, params.get('transform_suffix'))
        h2o.assign(df_vecs, dest_frame_id)
    else:
        dest_frame_id = frame_id

    return {'frame_id': dest_frame_id, 'model_id': w2v_model.model_id}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)


