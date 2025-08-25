#security_app/parser/dispatch.py
from security_app.parsers.common import detect_file_type
from security_app.parsers.csv_parser import parse_csv
from security_app.parsers.json_parser import parse_json
from security_app.parsers.xml_parser import parse_xml


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
