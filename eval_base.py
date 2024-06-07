#evaluate target line/branch coverage for baselines
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




template_data=read_jsonl('data/leetcode-py.jsonl')
def eval_correctness(generated_data):
    """Compute syntactical and execution correctness (with coverage)."""
    total_cases_line=0
    total_cases_branch=0
    total_syn_correct=0
    total_exec_correct=0
    syn_failed=0
    total_easy=0 #for evaluating branches with different difficulties
    total_medium=0
    total_hard=0
    cov_easybranch=0
    cov_mediumbranch=0
    cov_hardbranch=0

    exec_fails=[]

    cov_line_success=0
    cov_branch_success=0
    remove_pattern=re.compile(r'tmp*')


    for i, data in tqdm(enumerate(generated_data)):
        task_num=data['task_num']
        difficulty=data['difficulty']
        func_name=data['func_name']
        code=data['code']
        generated_tests=data['tests']
        baseline_test=generated_tests[0] #use the first generated test in overall coverage as the baseline

        branches=template_data[i]['blocks']
        for test_branch in branches:
            branch_diff=test_branch['difficulty']
            if branch_diff==0:
                total_easy+=1
            elif branch_diff==1:
                total_medium+=1
            elif branch_diff==2:
                total_hard+=1
        target_lines=template_data[i]['target_lines']
        test_import=f'from tmp_{i}_{difficulty}.under_test import Solution\n'
        test_import_simple=f'from under_test import Solution\n'
        os.makedirs(f'tmp_{i}_{difficulty}',exist_ok=True) #create different tmp folders for different problems to avoid conflicts
        with open(f'tmp_{i}_{difficulty}/under_test.py','w') as f: #write program under test and test cases into tmp files
            f.write(code)

        passed_tests=[]

        total_cases_line+=len(target_lines)
        total_cases_branch+=len(branches)
        try:
            res=compile(baseline_test,'<string>','exec') #check syntax correctness
            total_syn_correct+=1

            test_code=test_import+baseline_test+f'\ntest_{func_name}()'
            time.sleep(0.01)
            res=execute(test_code) 
            if res==True:
                if test_code.find(f'solution.{func_name}')==-1: #if the function under test is not called, also consider as failed
                    print('func under test not called')
                    exec_fails.append({'task':task_num, 'error':'not called'})
                else:
                    total_exec_correct+=1
                    test_code_simple=test_import_simple+baseline_test #write to files for computing coverage
                    with open(f'tmp_{i}_{difficulty}/test.py','w') as f:
                        f.write(test_code_simple)
                    passed_tests.append('test.py')
                    #print('correct')
            else:
                exec_fails.append({'task':task_num,'test_line':lineno,'error':res})
                #print(res)
                #print(test_code)
        except:
            syn_failed+=1
            pass
               
        if len(passed_tests)>0: #start measuring coverage
            #check if cover the selected line
            cov_command_prefix=['pytest', '--cov=under_test', '--cov-branch', '--cov-report=json:coverage.json']
            subprocess.run(f'cp .coveragerc tmp_{i}_{difficulty}/.coveragerc',shell=True) #copy config file to tmp_folder
            os.chdir(f'tmp_{i}_{difficulty}') #enter tmp_ folder for testing
            cov_command=deepcopy(cov_command_prefix)
            cov_command.append('test.py')

            subprocess.run(cov_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            cov_report=json.load(open('coverage.json'))
            executed_lines=cov_report['files']['under_test.py']['executed_lines']

            for lineno in target_lines: #get line coverage
                if lineno in executed_lines:
                    cov_line_success+=1
                    print(f'covered line {lineno}')
                else:
                    print('line not covered')
                    pass
            for j,test_branch in enumerate(branches): #get branch coverage
                startline=test_branch['start']
                endline=test_branch['end'] 
                
                branch_firstline=startline+1 #if this line is covered, this branch is covered
                if branch_firstline in executed_lines: #use startline+1 to check whether branch is covered
                    branch_diff=test_branch['difficulty']
                    if branch_diff==0:
                        cov_easybranch+=1
                    elif branch_diff==1:
                        cov_mediumbranch+=1
                    elif branch_diff==2:
                        cov_hardbranch+=1
                    cov_branch_success+=1
                    print(f'covered branch {startline}-{endline}')
                else:
                    print('branch not covered')
                    pass
            os.chdir('..') #exit tmp_ folder
        else: #no test cases passed
            pass

    for dirpath, dirnames, filenames in os.walk('./', topdown=False): #execute() runs too fast, remove dirs at last
        # Filter dirnames based on the regex pattern
        for dirname in dirnames:
            if remove_pattern.match(dirname):
                shutil.rmtree(dirname)
    
    syn_correct=total_syn_correct/len(generated_data)
    exec_correct=total_exec_correct/len(generated_data)
    print(total_syn_correct, total_exec_correct,len(generated_data))
    print(f'Syntax Correctness: {syn_correct}')
    print(f'Executable Correctness: {exec_correct}')

    cov_line_rate=cov_line_success/total_cases_line
    cov_branch_rate=cov_branch_success/total_cases_branch
    easy_covrate=cov_easybranch/total_easy
    medium_covrate=cov_mediumbranch/total_medium
    hard_covrate=cov_hardbranch/total_hard
    print(f'Accuracy in cover selected line: {cov_line_rate}')
    print(f'Accuracy in cover selected branch: {cov_branch_rate}')
    print(f'Easy branch coverage rate: {easy_covrate}')
    print(f'Medium branch coverage rate: {medium_covrate}')
    print(f'Hard branch coverage rate: {hard_covrate}')

    return {'syn_correct':syn_correct,'exec_correct':exec_correct, 'cov_line':cov_line_rate, 'cov_branch':cov_branch_rate}, exec_fails

    
def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--path", type=str, default='predictions/totalcov_gpt-3.5-turbo.jsonl')
    return parser.parse_args()


if __name__=='__main__':
    args=parse_args()
    print(args.path)
    output_dir = Path('predictions')
    predictions=read_jsonl(output_dir / args.path)
    print(len(predictions))

    eval_correctness(predictions)
