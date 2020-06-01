import h2o
import sys
from utils import save_model, append_frame_id, to_bool


def print_module():
    x = {
          'id': 'frame_tokenize',
          'name': 'Tokenize Strings',
          'type': 'FRAME',
          'priority': '240',
          'components': [
            {
              "id": "suffix",
              "name": "Suffix (Frame ID)",
              "description": "the suffix for the created frame",
              "type": "TEXT",
              "value": "tokenize",
            },
            {
              "id": "target_column",
              "name": "Column",
              "description": "the columns to apply word2vec",
              "type": "COLUMN",
            },
            {
              "id": "regex",
              "name": "Regex",
              "description": "the regular expression to tokenize on.",
              "type": "TEXT",
              "value": "\\W",
            },
            {
              "id": "analyzer",
              "name": "Analyzer",
              "description": "the analyzer to tokenize on.",
              "type": "SELECT",
              "options": [
                "arabic",
                "armenian",
                "basque",
                "brazilian",
                "bulgarian",
                "catalan",
                "czech",
                "danish",
                "dutch",
                "english",
                "finnish",
                "french",
                "galician",
                "german",
                "greek",
                "hindi",
                "hungarian",
                "indonesian",
                "irish",
                "italian",
                "japanese",
                "korean",
                "latvian",
                "lithuanian",
                "norwegian",
                "persian",
                "portuguese",
                "romanian",
                "russian",
                "simplified_chinese",
                "sorani",
                "spanish",
                "swedish",
                "thai",
                "traditional_chinese",
                "turkish",
                "vietnamese"],
              "value": "",
            },
            {
              "id": "url",
              "name": "URL",
              "description": "the api server to perform the text analysis.",
              "type": "TEXT",
              "value": "http://es01:9200/fess.search/_analyze",
            },
            {
              "id": "lower_case",
              "name": "Lower Case",
              "description": "convert to lower case",
              "type": "BOOL",
              "value": "false",
            },
            {
              "id": "min_word_len",
              "name": "Min Word Length",
              "description": "the minimum word length",
              "type": "TEXT",
              "value": "0",
            },
            {
              "id": "use_stop_words",
              "name": "Use Stop Words",
              "description": "remove stop words",
              "type": "BOOL",
              "value": "false",
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

    target_column = params.get("target_column")
    analyzer = params.get("analyzer")
    if len(analyzer) > 0:
        url = params.get("url")
        df_token = df[target_column].tokenize(f'tokenize:elasticsearch:{url}?analyzer={analyzer}_analyzer')
    else:
        df_token = df[target_column].tokenize(params.get('regex'))
       
    if to_bool(params.get('lower_case')):
        df_token = df_token.tolower()

    min_word_len = int(params.get('min_word_len'))
    if min_word_len > 0:
        df_token = df_token[(df_token.nchar() >= min_word_len) | (df_token.isna()),:]

    if to_bool(params.get('use_stop_words')):
        df_token = df_token[(df_token.isna()) | (~ df_token.isin(STOP_WORDS)),:]

    dest_frame_id = append_frame_id(frame_id, params.get('suffix'))
    h2o.assign(df_token, dest_frame_id)

    return {'frame_id': dest_frame_id}


STOP_WORDS = ["ax","i","you","edu","s","t","m","subject","can",
              "lines","re","what","there","all","we","one","the",
              "a","an","of","or","in","for","by","on","but","is",
              "in","a","not","with","as","was","if","they","are",
              "this","and","it","have","from","at","my","be","by",
              "not","that","to","from","com","org","like","likes",
              "so"]

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_module()
        sys.exit()
    config_file = sys.argv[1]
    import configparser
    config = configparser.ConfigParser()
    config.read([config_file])
    main(config)


