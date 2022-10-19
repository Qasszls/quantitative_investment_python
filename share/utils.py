"""
    我是注释
"""
import json


def to_json_parse(data):
    if type(data) == str:
        return json.loads(data)
    else:
        raise Exception('请输入字符串参数，该函数会帮助你解析')

def to_json_stringify(data):
    return json.dumps(data)