import os
import json

def read_jsonl(path):
    data=[]
    with open(path,'r') as f:
        for line in f:
            data.append(json.loads(line))
    return data


def write_jsonl(data,path):
    with open(path,'w') as f:
        for d in data:
            f.write(json.dumps(d)+'\n')


def add_lineno(code):
    """Add line numbers to code."""
    lines=code.split('\n')
    new_code=''
    for i, line in enumerate(lines):
        new_code+=f'{i+1}. {line}\n'
    return new_code
