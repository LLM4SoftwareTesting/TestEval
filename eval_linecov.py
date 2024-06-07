import os
import subprocess
import json
import signal
import random
random.seed(42)
import shutil
import time
import re
from pathlib import Path
from tqdm import tqdm
from argparse import ArgumentParser
from copy import deepcopy
from data_utils import read_jsonl


class TimeoutHandler:
    def __init__(self, timeout, error_message=None):
        self.timeout = timeout
        self.error_message = error_message
    
    def __enter__(self):
        signal.signal(signal.SIGALRM, self.raise_timeout) #SIGALRM only support unix
        signal.alarm(self.timeout)
    
    def __exit__(self, type, value, traceback):
        signal.alarm(0)
    
    def raise_timeout(self, *args):
        raise TimeoutError(self.error_message)
    

def execute(test_code,timeout=5):
    """try to execute test code"""  
    try:
        exec_globals = {}
        with TimeoutHandler(timeout):
            exec(test_code, globals()) #add globals() to avoid name errors related to import
            return True
    except AssertionError: #assertionerror is considered as executable
        return True
    except TimeoutError:
        #print("timed out")
        return False
    except Exception as e: 
        #print(f"failed: {type(e).__name__}")
        return type(e).__name__, e #return error type and error message     
    

def eval_correctness(generated_data, covmode='branch'):
    """Compute syntactical and execution correctness (with coverage)."""
    total_cases=0
    total_syn_correct=0
    total_comp_correct=0
    total_exec_correct=0
    syn_failed=0

    exec_fails=[]

    total_line_cov=0
    total_branch_cov=0
    cov_line_success=0
    remove_pattern=re.compile(r'tmp*')

    for i, data in tqdm(enumerate(generated_data)):
        task_num=data['task_num']
        difficulty=data['difficulty']
        func_name=data['func_name']
        code=data['code']
        #code=ADDITIONAL_IMPORTS+code #add possibly missing imports
        test_cases=data['tests']
        test_import=f'from tmp_{i}_{difficulty}.under_test import Solution\n'
        test_import_simple=f'from under_test import Solution\n'
        os.makedirs(f'tmp_{i}_{difficulty}',exist_ok=True) #create different tmp folders for different problems to avoid conflicts
        with open(f'tmp_{i}_{difficulty}/under_test.py','w') as f: #write program under test and test cases into tmp files
            f.write(code)
        passed_tests={}
        
        for lineno in test_cases:
            testcase=test_cases[lineno]
            #testcase=test_cases[fixed_testcase_num] #comparison: use the first test case
            lineno=int(lineno)
            total_cases+=1

            try:
                res=compile(testcase,'<string>','exec') #check syntax correctness
                total_syn_correct+=1

                test_code=test_import+testcase+f'\ntest_{func_name}()'
                time.sleep(0.01)
                res=execute(test_code) 
                if res==True:
                    if test_code.find(f'solution.{func_name}')==-1: #if the function under test is not called, also consider as failed
                        print('func under test not called')
                        exec_fails.append({'task':task_num, 'error':'not called'})
                    else:
                        total_exec_correct+=1
                        test_code_simple=test_import_simple+testcase #write to files for computing coverage
                        with open(f'tmp_{i}_{difficulty}/test_{lineno}.py','w') as f:
                            f.write(test_code_simple)
                        passed_tests[lineno]=f'test_{lineno}.py'
                        #print('correct')
                else:
                    exec_fails.append({'task':task_num,'test_line':lineno,'error':res})
                    #print(res)
                    #print(test_code)
            except:
                syn_failed+=1
                #print('syntax error')
                pass
               
        if len(passed_tests)>0: #start measuring coverage
            #check if cover the selected line
            cov_command_prefix=['pytest', '--cov=under_test', '--cov-branch', '--cov-report=json:coverage.json']
            subprocess.run(f'cp .coveragerc tmp_{i}_{difficulty}/.coveragerc',shell=True) #copy config file to tmp_folder
            os.chdir(f'tmp_{i}_{difficulty}') #enter tmp_ folder for testing
            for lineno in passed_tests:
                test=passed_tests[lineno]
                cov_command=deepcopy(cov_command_prefix)
                cov_command.append(test)

                subprocess.run(cov_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                cov_report=json.load(open('coverage.json'))
                executed_lines=cov_report['files']['under_test.py']['executed_lines']
                #missline_lines=
                if lineno in executed_lines:
                    cov_line_success+=1
                    print(f'covered line {lineno}')
                else:
                    print('not covered')
                    pass
            os.chdir('..') #exit tmp_ folder
        else: #no test cases passed
            pass

    for dirpath, dirnames, filenames in os.walk('./', topdown=False): #execute() runs too fast, remove dirs at last
        # Filter dirnames based on the regex pattern
        for dirname in dirnames:
            if remove_pattern.match(dirname):
                shutil.rmtree(dirname)
    
    syn_correct=total_syn_correct/total_cases
    exec_correct=total_exec_correct/total_cases
    print(total_syn_correct, total_exec_correct,total_cases)
    print(f'Syntax Correctness: {syn_correct}')
    print(f'Executable Correctness: {exec_correct}')

    cov_line_rate=cov_line_success/total_cases
    cov_line_rate_exec=cov_line_success/total_exec_correct
    print(f'Accuracy in cover selected line: {cov_line_rate}')

    return {'syn_correct':syn_correct,'exec_correct':exec_correct, 'cov_line':cov_line_rate}, exec_fails

    
def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--path", type=str, default='linecov_gpt-3.5-turbo.jsonl')
    return parser.parse_args()



if __name__=='__main__':
    args=parse_args()
    print(args.path)
    output_dir = Path('predictions')
    predictions=read_jsonl(output_dir / args.path)
    print(len(predictions))

    eval_correctness(predictions)
