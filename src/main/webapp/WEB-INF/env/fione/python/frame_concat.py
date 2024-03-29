import h2o
import json
import sys
from utils import append_frame_id


def print_module():
    x = {
          'id': 'frame_concat',
          'name': 'Concat Frames',
          'type': 'FRAME',
          'priority': '132',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame id",
              "type": "TEXT",
              "value": "concat",
            },
            {
              "id": "frames",
              "name": "Frame IDs",
              "description": "list of frames that should be appended to the current frame.",
              "type": "MULTIFRAME",
            },
            {
              "id": "axis",
              "name": "Axis",
              "description": "if 1 then append column-wise, if 0 then append row-wise.",
              "type": "SELECT",
              "options": ["0", "1"],
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

    frames = params.get('frames')
    if frames is None or len(frames) <= 2:
        print("frames are empty.")
        sys.exit(1)
    frames = json.loads(frames)

    df_concat = df.concat([h2o.get_frame(x) for x in frames], axis=int(params.get('axis')))

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_concat, dest_frame_id)

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


