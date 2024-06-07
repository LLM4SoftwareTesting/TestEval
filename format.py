import os
import textwrap
import ast
from pathlib import Path
from argparse import ArgumentParser

from data_utils import read_jsonl, write_jsonl


def change_function_name(code, new_name):
    try:
        # Parse the code into an AST
        tree = ast.parse(code)

        # Find the first function definition and change its name
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name!=new_name:
                    node.name = new_name
                    break
                else:
                    break

        # Convert the modified AST back to code
        new_code = ast.unparse(tree)
        return new_code
    except Exception as e: #cannoot parse
        return code


def reformat_case_byrules(testcase, func_name, lang='python'):
    if testcase.startswith(' '): #remove extra indents (encountered in codellama, mistral-7b starts with one space...)
        testcase=textwrap.dedent(testcase)
    lines=testcase.split('\n')

    if lang=='python':
        last_line=lines[-1] #if last line is not complete (due to token limit), remove it    
        last_line=textwrap.dedent(last_line)
        try:
            compile(last_line,'<string>','exec')
        except:
            #print('imcomplete last line, remove it', last_line)
            lines=lines[:-1] #last line cannot compile

    testcase='\n'.join(lines)
    testcase=change_function_name(testcase, func_name)
    return testcase


def remove_extra(testcase, func_name, lang='python'):
    """Remove extra test inputs and natural language descriptions before and after the test method.
    Only keep the contents between def test() and solution.{func_name}"""
    lines=testcase.split('\n')
    func_startline=0 #the line when test function starts (def test....)
    for i in range(len(lines)):
        if lines[i].find('def test')>=0:
            func_startline=i
            break
    test_endline=len(lines)
    for i in range(len(lines)):
        if lines[i].find(f'solution.{func_name}')>=0: #first call to the function under test
            test_endline=i+1
            break
    new_testcase='\n'.join(lines[func_startline:test_endline])
    return new_testcase
    
    num_inputs=testcase.count(f'solution.{func_name}')
    if num_inputs>1:
        lines=testcase.split('\n')
        new_testcase=[]
        for line in lines:
            new_testcase.append(line)
            if line.find(f'solution.{func_name}')>=0: #discard statements after the first test input
                break
        new_testcase='\n'.join(new_testcase)
        return new_testcase
    else:
        return testcase


def reformat_line(datapath,newpath):
    data=read_jsonl(datapath)
    formatted_data=[]
    for e in data:
        code=e['code']
        func_name=e['func_name']
        test_funcname=f'test_{func_name}'
        #print(code)
        tests=e['tests']
        #formated_tests=[]
        for lineno in tests:
            testcase=tests[lineno]
            print(testcase)
            testcase=remove_extra(testcase, func_name)
            reformatted_testcase=reformat_case_byrules(testcase, test_funcname, 'python')
            #print('------')
            print(reformatted_testcase)
            print('<---------------------->')
            tests[lineno]=reformatted_testcase
        e['tests']=tests

        formatted_data.append(e)
    write_jsonl(formatted_data, newpath)


def reformat_branch(datapath,newpath):
    data=read_jsonl(datapath)
    formatted_data=[]
    for e in data:
        code=e['code']
        func_name=e['func_name']
        test_funcname=f'test_{func_name}'
        #print(code)
        tests=e['tests']
        formated_tests=[]
        for branch in tests:
            testcase=branch['test']
            print(testcase)
            testcase=remove_extra(testcase, func_name)
            reformatted_testcase=reformat_case_byrules(testcase, test_funcname, 'python')
            #print('------')
            print(reformatted_testcase)
            print('<---------------------->')
            branch['test']=reformatted_testcase
            formated_tests.append(branch)
        e['tests']=formated_tests

        formatted_data.append(e)
    write_jsonl(formatted_data, newpath)


def reformat_cov(datapath,newpath):
    data=read_jsonl(datapath)
    formatted_data=[]
    for e in data:
        #print(code)
        func_name=e['func_name']
        test_funcname=f'test_{func_name}'
        formatted_test_cases=[]
        testcases=e['tests']
        for testcase in testcases:
            print(testcase)
            extracted_testcase=remove_extra(testcase, func_name)
            #if extracted_testcase!=testcase:
                #print(testcase)
                #print('----')
                #print(extracted_testcase)
            reformatted_testcase=reformat_case_byrules(extracted_testcase, test_funcname, 'python')
            print('------')
            print(reformatted_testcase)
            print('<---------------------->')
            formatted_test_cases.append(reformatted_testcase)
        e['tests']=formatted_test_cases

        formatted_data.append(e)
    write_jsonl(formatted_data, newpath)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--path", type=str, default='Linecov_python_gemini-1.0-pro-latest.jsonl')
    parser.add_argument("--mode", type=str, default='overall', choices=['line', 'branch', 'overall'])
    return parser.parse_args()


if __name__=='__main__':
    args=parse_args()
    print('generated answers:', args.path)
    print('coverage mode:', args.mode)
    output_dir = Path('predictions')
    finename,ext=os.path.splitext(args.path)
    newpath=f'{finename}format{ext}'
    print(newpath)
    if args.mode=='line':
        print('reformat line coverage')
        reformat_line(output_dir / args.path, output_dir / newpath)
    elif args.mode=='overall':
        print('reformat overall coverage')
        reformat_cov(output_dir / args.path, output_dir / newpath)
    elif args.mode=='branch':
        print('reformat branch coverage')
        reformat_branch(output_dir / args.path, output_dir / newpath)
