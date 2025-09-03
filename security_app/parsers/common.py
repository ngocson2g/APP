#security_app/parser/common.py
"""
Common utilities cho parsers
"""
import os


def detect_file_type(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".csv":
        return "csv"
    if ext == ".json":
        return "json"
    if ext == ".xml":
        return "xml"
    raise ValueError("Unknown file type: " + ext)

