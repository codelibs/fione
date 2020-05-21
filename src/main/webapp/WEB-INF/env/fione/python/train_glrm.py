import h2o
import sys
from utils import save_model


def print_module():
    x = {
          'id': 'train_glrm',
          'name': 'Run GLRM',
          'type': 'TRAIN',
          'priority': '300',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Model Set)",
              "description": "the suffix for the created model set",
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
              "id": "expand_user_y",
              "name": "Expand User Y",
              "description": "Expand categorical columns in user-specified initial Y",
              "type": "BOOL",
              "value": "true",
            },
            {
              "id": "gamma_x",
              "name": "Gamma X",
              "description": "Regularization weight on X matrix",
              "type": "TEXT",
              "value": "0",
            },
            {
              "id": "gamma_y",
              "name": "Gamma Y",
              "description": "Regularization weight on Y matrix",
              "type": "TEXT",
              "value": "0",
            },
            {
              "id": "ignore_const_cols",
              "name": "Ignore Const Cols",
              "description": "Ignore constant columns",
              "type": "BOOL",
              "value": "true",
            },
            # ignored_columns
            {
              "id": "impute_original",
              "name": "Impute Original",
              "description": "Reconstruct original training data by reversing transform",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "init",
              "name": "Init",
              "description": "Initialization mode",
              "type": "SELECT",
              "options": ["random", "svd", "plus_plus", "user"],
              "value": "plus_plus",
            },
            {
              "id": "init_step_size",
              "name": "Init Step Size",
              "description": "Initial step size",
              "type": "TEXT",
              "value": "1",
            },
            {
              "id": "k",
              "name": "K",
              "description": "Rank of matrix approximation",
              "type": "TEXT",
              "value": "1",
            },
            # loading_name
            {
              "id": "loss",
              "name": "Loss",
              "description": "Numeric loss function",
              "type": "SELECT",
              "options": ["quadratic", "absolute", "huber", "poisson", "hinge", "logistic", "periodic"],
              "value": "quadratic",
            },
            # loss_by_col
            # loss_by_col_idx
            {
              "id": "max_iterations",
              "name": "Max Iterations",
              "description": "Maximum number of iterations",
              "type": "TEXT",
              "value": "1000",
            },
            {
              "id": "max_runtime_secs",
              "name": "Max Runtime Secs",
              "description": "Maximum allowed runtime in seconds for model training. Use 0 to disable.",
              "type": "TEXT",
              "value": "0",
            },
            {
              "id": "max_updates",
              "name": "Max Updates",
              "description": "Maximum number of updates, defaults to 2*max_iterations",
              "type": "TEXT",
              "value": "2000",
            },
            {
              "id": "min_step_size",
              "name": "Min Step Size",
              "description": "Minimum step size",
              "type": "TEXT",
              "value": "0.0001",
            },
            {
              "id": "multi_loss",
              "name": "Multi Loss",
              "description": "Categorical loss function",
              "type": "SELECT",
              "options": ["categorical", "ordinal"],
              "value": "categorical",
            },
            {
              "id": "period",
              "name": "Period",
              "description": "Length of period (only used with periodic loss function)",
              "type": "TEXT",
              "value": "1",
            },
            {
              "id": "recover_svd",
              "name": "Recover SVD",
              "description": "Recover singular values and eigenvectors of XY",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "regularization_x",
              "name": "Regularization X",
              "description": "Regularization function for X matrix",
              "type": "SELECT",
              "options": ["none", "quadratic", "l2", "l1", "non_negative", "one_sparse", "unit_one_sparse", "simplex"],
              "value": "none",
            },
            {
              "id": "regularization_y",
              "name": "Regularization Y",
              "description": "Regularization function for Y matrix",
              "type": "SELECT",
              "options": ["none", "quadratic", "l2", "l1", "non_negative", "one_sparse", "unit_one_sparse", "simplex"],
              "value": "none",
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
              "description": "RNG seed for initialization",
              "type": "TEXT",
              "value": "-1",
            },
            {
              "id": "svd_method",
              "name": "SVD Method",
              "description": "Method for computing SVD during initialization (Caution: Randomized is currently experimental and unstable)",
              "type": "SELECT",
              "options": ["gram_s_v_d", "power", "randomized"],
              "value": "randomized",
            },
            # user_x
            # user_y
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
    column_header = params.get('column_header')
    if len(column_header) > 0:
        df = df[int(column_header):]

    from h2o.estimators.glrm import H2OGeneralizedLowRankEstimator
    glrm_model = H2OGeneralizedLowRankEstimator(
        expand_user_y=bool(params.get('expand_user_y')),
        gamma_x=float(params.get('gamma_x')),
        gamma_y=float(params.get('gamma_y')),
        ignore_const_cols=bool(params.get('ignore_const_cols')),
        impute_original=bool(params.get('impute_original')),
        init=str(params.get('init')),
        init_step_size=float(params.get('init_step_size')),
        k=int(params.get('k')),
        loss=str(params.get('loss')),
        max_iterations=int(params.get('max_iterations')),
        max_runtime_secs=float(params.get('max_runtime_secs')),
        max_updates=int(params.get('max_updates')),
        min_step_size=float(params.get('min_step_size')),
        multi_loss=str(params.get('multi_loss')),
        period=int(params.get('period')),
        recover_svd=bool(params.get('recover_svd')),
        regularization_x=str(params.get('regularization_x')),
        regularization_y=str(params.get('regularization_y')),
        score_each_iteration=bool(params.get('score_each_iteration')),
        seed=int(params.get('seed')),
        svd_method=str(params.get('svd_method')))
    glrm_model.train(training_frame=df)
    glrm_model.show()
    save_model(params, glrm_model.model_id)

    return {'frame_id': frame_id, 'model_id': glrm_model.model_id}


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)


