import h2o
import sys
from utils import save_model


def print_module():
    x = {
          'id': 'train_kmeans',
          'name': 'Run KMeans',
          'type': 'TRAIN',
          'priority': '100',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Model Set)",
              "description": "the suffix for the created model set",
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
              "id": "categorical_encoding",
              "name": "Categorical Encoding",
              "description": "Encoding scheme for categorical features",
              "type": "SELECT",
              "options": ["auto", "enum", "one_hot_internal", "one_hot_explicit", "binary", "eigen", "label_encoder", "sort_by_response", "enum_limited"],
              "value": "auto",
            },
            {
              "id": "estimate_k",
              "name": "Estimate K",
              "description": "Whether to estimate the number of clusters (<=k) iteratively and deterministically.",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "fold_assignment",
              "name": "Fold Assignment",
              "description": "Cross-validation fold assignment scheme, if fold_column is not specified. The ‘Stratified’ option will stratify the folds based on the response variable, for classification problems.",
              "type": "SELECT",
              "options": ["auto", "random", "modulo", "stratified"],
              "value": "auto",
            },
            {
              "id": "ignore_const_cols",
              "name": "Ignore Const Cols",
              "description": "Ignore constant columns.",
              "type": "BOOL",
              "value": "true",
            },
            {
              "id": "init",
              "name": "Init",
              "description": "Initialization mode",
              "type": "SELECT",
              "options": ["random", "plus_plus", "furthest", "user"],
              "value": "furthest",
            },
            {
              "id": "k",
              "name": "K",
              "description": "The max. number of clusters. If estimate_k is disabled, the model will find k centroids, otherwise it will find up to k centroids.",
              "type": "TEXT",
              "value": "1",
            },
            {
              "id": "keep_cross_validation_fold_assignment",
              "name": "Keep Cross Validation Fold Assignment",
              "description": "Whether to keep the cross-validation fold assignment.",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "keep_cross_validation_models",
              "name": "Keep Cross Validation Models",
              "description": "Whether to keep the cross-validation models.",
              "type": "BOOL",
              "value": "true",
            },
            {
              "id": "keep_cross_validation_predictions",
              "name": "Keep Cross Validation Predictions",
              "description": "Whether to keep the predictions of the cross-validation models.",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "max_iterations",
              "name": "Max Iterations",
              "description": "Maximum training iterations (if estimate_k is enabled, then this is for each inner Lloyds iteration)",
              "type": "TEXT",
              "value": "10",
            },
            {
              "id": "max_runtime_secs",
              "name": "Max Runtime Secs",
              "description": "Maximum allowed runtime in seconds for model training. Use 0 to disable.",
              "type": "TEXT",
              "value": "0",
            },
            {
              "id": "nfolds",
              "name": "N Folds",
              "description": "Number of folds for K-fold cross-validation (0 to disable or >= 2).",
              "type": "TEXT",
              "value": "0",
            },
            {
              "id": "score_each_iteration",
              "name": "Score Each Iteration",
              "description": "Whether to score during each iteration of model training.",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "seed",
              "name": "Seed",
              "description": "RNG Seed",
              "type": "TEXT",
              "value": "-1",
            },
            {
              "id": "standardize",
              "name": "Standardize",
              "description": "Standardize columns before computing distances",
              "type": "BOOL",
              "value": "true",
            },
          ]
        }
    import json
    print(json.dumps(x))
    

def main(config):
    from h2o.estimators import H2OKMeansEstimator

    h2o_config = config['h2o']
    params = config['parameters']

    h2o.init(url=h2o_config.get('url'))
    frame_id = params.get('frame_id')
    execute(h2o, params, {'frame_id': frame_id})


def execute(h2o, params, config):
    frame_id = config.get('frame_id')

    df = h2o.get_frame(frame_id)

    input_columns=params.get("input_columns")
    if input_columns is None or len(input_columns) == 0:
        input_columns = df.col_names
    else:
        import json
        input_columns = json.loads(input_columns)

    kmeans_model = H2OKMeansEstimator(
        categorical_encoding=params.get("categorical_encoding"),
        estimate_k=bool(params.get("estimate_k")),
        fold_assignment=params.get("fold_assignment"),
        ignore_const_cols=bool(params.get("ignore_const_cols")),
        init=params.get("init"),
        k=int(params.get("k")),
        keep_cross_validation_fold_assignment=bool(params.get("keep_cross_validation_fold_assignment")),
        keep_cross_validation_models=bool(params.get("keep_cross_validation_models")),
        keep_cross_validation_predictions=bool(params.get("keep_cross_validation_predictions")),
        max_iterations=int(params.get("max_iterations")),
        max_runtime_secs=float(params.get("max_runtime_secs")),
        nfolds=int(params.get("nfolds")),
        score_each_iteration=bool(params.get("score_each_iteration")),
        seed=int(params.get("seed")),
        standardize=bool(params.get("standardize")))
    kmeans_model.train(x=input_columns, training_frame=df)
    kmeans_model.show()

    save_model(params, kmeans_model.model_id)

    return {'frame_id': frame_id, 'model_id': kmeans_model.model_id}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)


