from parse.parse_common import detect_file_type
from parse.parse_csv import parse_csv
from parse.parse_json import parse_json
from parse.parse_xml import parse_xml

def parse_file(file_path):
    ftype = detect_file_type(file_path)
    if ftype == 'csv':
        return parse_csv(file_path)
    elif ftype == 'json':
        return parse_json(file_path)
    elif ftype == 'xml':
        return parse_xml(file_path)
    else:
        raise ValueError('Unsupported file type')
