from leetcode import LeetCodeDataset
import os
import json
import textwrap

def read_leetcode():
    """Read dataset from https://huggingface.co/datasets/greengerong/leetcode"""
    dataset = LeetCodeDataset()
    return dataset


def format_leetcode(code,lang):
    if lang=='python':
        lines=code.split('\n')
        new_code='\n'.join(lines[1:])
        new_code=textwrap.dedent(new_code)
        return new_code
    

def read_LC():
    """Read dataset from https://github.com/walkccc/LeetCode (used by leetcode-hard-gym)
    This dataset only contains canonical solutions."""
    data_dir='/data/wangwenhan/LeetCode/solutions/'
    data_dir='LC_data/solutions/'
    metadata_path='LC_data/leetcode-all-meta.jsonl'
    dataset=[]
    with open(metadata_path,'r') as f:
        for line in f:
            data=json.loads(line)
            task_num=data['task_num']
            title=data['task_title']
            difficulty=data['difficulty']
            func_name=data['func_name']
            description=data['description']
            task_dir=os.path.join(data_dir,str(task_num))
            cpp_path=os.path.join(task_dir,f'{task_num}.cpp')
            java_path=os.path.join(task_dir,f'{task_num}.java')
            python_path=os.path.join(task_dir,f'{task_num}.py')
            if os.path.exists(python_path) and os.path.exists(java_path) and os.path.exists(cpp_path):
                python_code=open(python_path,'r').read()
                #print(python_code)
                python_code=format_leetcode(python_code,'python')
                java_code=open(java_path,'r').read()
                cpp_code=open(cpp_path,'r').read()
                data['python_solution']=python_code
                data['java_solution']=java_code
                data['c++_solution']=cpp_code
                dataset.append(data)
            else:
                #print('skip:',task_num)
                continue
        print(len(dataset))
    return dataset


def write_LC():
    """Read dataset from https://github.com/walkccc/LeetCode and write solutions to a new file."""
    data_dir='/data/wangwenhan/LeetCode/solutions/'
    data_dir='LC_data/solutions/'
    metadata_path='LC_data/leetcode-all-meta.jsonl'

    new_solutions_path='LC_data/leetcode-all-solutions.jsonl'
    dataset=[]
    with open(metadata_path,'r') as f:
        for line in f:
            data=json.loads(line)
            task_num=data['task_num']
            title=data['task_title']
            difficulty=data['difficulty']
            func_name=data['func_name']
            description=data['description']
            task_dir=os.path.join(data_dir,str(task_num))
            cpp_path=os.path.join(task_dir,f'{task_num}.cpp')
            java_path=os.path.join(task_dir,f'{task_num}.java')
            python_path=os.path.join(task_dir,f'{task_num}.py')
            if os.path.exists(python_path) and os.path.exists(java_path) and os.path.exists(cpp_path):
                python_code=open(python_path,'r').read()
                #print(python_code)
                #python_code=format_leetcode(python_code,'python')
                java_code=open(java_path,'r').read()
                cpp_code=open(cpp_path,'r').read()
                data['python_solution']=python_code
                data['java_solution']=java_code
                data['c++_solution']=cpp_code
                dataset.append(data)
            else:
                print('skip:',task_num)
                continue
        print(len(dataset))
    with open(new_solutions_path,'w') as f:
        for data in dataset:
            f.write(json.dumps(data)+'\n')
    return dataset


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


def remove_examples(desc):
    """Remove example test cases from description."""
    desc_split=desc.split('Example 1:')
    if len(desc_split)!=2:
        desc_split=desc.split('Example :')
    assert len(desc_split)==2
    return desc_split[0]

def filter_nobranch():
    data=read_jsonl('LC_data/leetcode-all-solutions.jsonl')
    nobranches=[]
    data_filtered=[]
    for e in data:
        code=e['python_solution']
        java_code=e['java_solution']
        cpp_code=e['c++_solution']
        if ('if ' not in code and 'for ' not in code and 'while ' not in code) or ('if' not in java_code and 'for' not in java_code and 'while' not in java_code) or ('if' not in cpp_code and 'for' not in cpp_code and 'while' not in cpp_code and 'switch' not in cpp_code):
            print(e['task_num'],e['task_title'])
            nobranches.append(e['task_num'])
            print(code)
            #print('---')
        else:
            data_filtered.append(e)
    print(len(nobranches))
    write_jsonl(data_filtered,'LC_data/leetcode-solutions-branch.jsonl') #problems with branches in solutions

if __name__=='__main__':
    #write_LC()
    #filter_nobranch()
    pass