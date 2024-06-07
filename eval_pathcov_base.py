import os
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
        #with time_limit(timeout):
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
    


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--path", type=str, default='pathcov_gpt-3.5-turboformat.jsonl')
    return parser.parse_args()


def match_path(generated_path, ref_path):
    """Compute path similarity based on longest common subsequence.
    Return similarity: len(lcs(generated_path, ref_path))/len(ref_path)"""
    ref_len=len(ref_path)
    generated_len=len(generated_path)

    dp = [[0]*(ref_len+1) for _ in range(generated_len+1)]
    max_length = 0
    for i in range(1, generated_len+1):
        for j in range(1, ref_len+1):
            if generated_path[i-1] == ref_path[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                max_length = max(max_length, dp[i][j])
    similarity = max_length / ref_len
    return similarity



def eval_correctness(generated_data):
    """Compute syntactical and execution correctness (with coverage)."""
    ref_dataset=read_jsonl('data/tgt_paths.jsonl')
    instrumented_dataset=read_jsonl('data/leetcode-py-instrumented.jsonl')
    total_cases=0
    total_paths=0
    total_syn_correct=0
    total_exec_correct=0
    syn_failed=0

    exec_fails=[]

    total_path_match=0
    total_path_similarity=0 #similarity score: based on longest common subsequence
    remove_pattern=re.compile(r'tmp*')

    for i, data in tqdm(enumerate(generated_data)):
        task_num=data['task_num']
        difficulty=data['difficulty']
        func_name=data['func_name']
        task_title=instrumented_dataset[i]['task_title']
        instrumented_code=instrumented_dataset[i]['python_solution_instrumented']
        test_cases=data['tests']
        baseline_test=test_cases[0] #use the first generated test in overall coverage as the baseline
        test_import=f'from tmp_{i}_{difficulty}.under_test import Solution\n'
        test_import_simple=f'from under_test import Solution\n'
        os.makedirs(f'tmp_{i}_{difficulty}',exist_ok=True) #create different tmp folders for different problems to avoid conflicts
        with open(f'tmp_{i}_{difficulty}/under_test.py','w') as f: #write program under test into tmp files
            f.write(instrumented_code)
        passed_tests=[]
        
        os.chdir(f'tmp_{i}_{difficulty}') #enter tmp_ folder for testing
        os.makedirs('test_logs',exist_ok=True)
        
        total_cases+=1
        total_paths+=len(ref_dataset[i]['sampled_paths'])
        with open(f'test_logs/{task_title}.log', 'w') as f:
            f.write('') #add empty log file
        try:
            res=compile(baseline_test,'<string>','exec') #check syntax correctness
            total_syn_correct+=1

            test_code=test_import+baseline_test+f'\ntest_{func_name}()'
            time.sleep(0.01)
            res=execute(test_code) 
            if res==True:
                if test_code.find(f'solution.{func_name}')==-1: #if the function under test is not called, also consider as failed
                    print('func under test not called')
                    exec_fails.append({'task':task_num,'test_num':j,'error':'not called'})
                else: #sucussfully execution, start calculating path coverage
                    total_exec_correct+=1
                    with open(f'test_logs/{task_title}.log') as f:
                        lines=f.readlines()
                        print(lines)
                        generated_path=tuple(lines)
                    for j in range(len(ref_dataset[i]['sampled_paths'])):
                        #total_paths+=1 #total paths should be added before execution
                        ref_path=ref_dataset[i]['sampled_paths'][j]
                        #print(ref_path)
                        
                        path_sim=match_path(generated_path, ref_path)
                        print(generated_path, ref_path, path_sim)
                        if path_sim==1:
                            total_path_match+=1
                        total_path_similarity+=path_sim

                        passed_tests.append({'path': f'test.py', 'pass': True})
            else:
                exec_fails.append({'task':task_num,'test_num':j,'error':res})
                #print(res)
                #print(test_code)
                passed_tests.append({'path': f'test.py', 'pass': False})
        except:
            syn_failed+=1
            #print('syntax error')
            passed_tests.append({'path': f'test.py', 'pass': False})
            pass
        #print(passed_tests)
        os.chdir('..') #exit tmp_ folder
    
    for dirpath, dirnames, filenames in os.walk('./', topdown=False): #execute() runs too fast, remove dirs at last
        # Filter dirnames based on the regex pattern
        for dirname in dirnames:
            if remove_pattern.match(dirname):
                shutil.rmtree(dirname)

    syn_correct=total_syn_correct/total_cases
    exec_correct=total_exec_correct/total_cases
    print(f'Syntax Correctness: {syn_correct}')
    print(f'Executable Correctness: {exec_correct}')
    
    print(total_exec_correct,total_cases, total_path_match,total_paths)
    path_exactmatch_acc=total_path_match/total_paths
    path_similarity_score=total_path_similarity/total_paths
    print('path exact match accuracy:', path_exactmatch_acc)
    print('path similarity score:', path_similarity_score)



if __name__=='__main__':
    args=parse_args()
    print(args.path)
    output_dir = Path('predictions')
    predictions=read_jsonl(output_dir / args.path)
    print(len(predictions))

    eval_correctness(predictions)
