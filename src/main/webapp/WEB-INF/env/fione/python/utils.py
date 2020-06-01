import h2o
import json
import sys


def print_module():
    x = {
          'id': 'utils',
          'name': 'Utility',
          'type': 'LIBRARY',
          'priority': '999',
          'components': []
        }
    print(json.dumps(x))
    

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


def parse_row_condition(df, value, mask=None):
    and_op = value.find('&')
    or_op = value.find('|')
    if (and_op < or_op and and_op != -1) or (and_op >= 0 and or_op == -1):
        mask = parse_value_condition(df, value[:and_op].strip(), mask)
        mask = parse_row_condition(df, value[and_op+1:], mask)
    elif (or_op < and_op and or_op != -1) or (or_op >= 0 and and_op == -1):
        mask = parse_value_condition(df, value[:or_op].strip(), mask)
        mask = parse_row_condition(df, value[or_op+1:], mask)
    else:
        mask = parse_value_condition(df, value.strip(), mask)
    return mask


def parse_value_condition(df, value, mask):
    op = None
    for x in ['==', '!=', '<', '<=', '>', '>=']:
        if value.find(f' {x} ') != -1:
            values = value.split(f' {x} ')
            k = values[0].strip()
            v = values[1].strip()
            c_type = df.types[k]
            op = x
            break

    if op is None:
        return mask

    if c_type == 'real':
        v = float(v)
    elif c_type == 'int':
        v = int(v)

    if op == '==':
        condition = (df[k] == v)
    elif op == '!=':
        condition = (df[k] != v)
    elif op == '<':
        condition = (df[k] < v)
    elif op == '<=':
        condition = (df[k] <= v)
    elif op == '>':
        condition = (df[k] > v)
    elif op == '>=':
        condition = (df[k] >= v)

    if mask is None:
        mask = condition
    else:
        mask = mask | condition

    return mask


def save_model(params, model_id):
    import json
    x = json.dumps({
        'type': 'model',
        'leaderboard_id': params.get('project_name') + '@@' + params.get('suffix'),
        'model_id': model_id
      })
    print(f'FIONE:{x}')


def send_progress(progress, message):
    import json
    x = json.dumps({
        'type': 'progress',
        'progress': progress,
        'message': message
      })
    print(f'FIONE:{x}')


def to_bool(value):
    if value is None:
        return False
    if value == 'true':
        return True
    else:
        return False


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()


