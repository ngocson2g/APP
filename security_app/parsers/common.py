import os

def detect_file_type(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.csv':
        return 'csv'
    elif ext == '.json':
        return 'json'
    elif ext == '.xml':
        return 'xml'
    else:
        raise ValueError('Unknown file type: ' + ext)
