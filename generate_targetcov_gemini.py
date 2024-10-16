import google.generativeai as genai
from google.generativeai import GenerationConfig
from google.api_core.exceptions import InternalServerError, ResourceExhausted

api_key=os.getenv("GOOGLE_API_KEY")

import os
import time
from argparse import ArgumentParser
from tqdm import tqdm
from pathlib import Path

from data_utils import read_jsonl, write_jsonl, add_lineno

genai.configure(api_key=api_key)

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--lang", type=str, default='python')
    parser.add_argument("--model", type=str, default='models/gemini-1.0-pro-latest', choices=['models/gemini-1.0-pro-latest', 'models/gemini-1.5-pro-latest'])
    parser.add_argument("--covmode", type=str, default='line', choices=['line', 'branch'], help='cover targets at line level or branch level')
    parser.add_argument("--max_tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0)
    return parser.parse_args()


if __name__=='__main__':
    args=parse_args()
    print('Model:', args.model)
    model_abbrv=args.model.split('/')[-1]
    model = genai.GenerativeModel(args.model)
    print('task:', args.covmode)
    output_dir = Path('predictions')

    prompt_template=open('prompt/template_line.txt').read()
    prompt_template_branch=open('prompt/template_branch.txt').read()
    system_template=open('prompt/system.txt').read()
    system_message=system_template.format(lang='python')

    dataset=read_jsonl('data/leetcode-py.jsonl')

    generation_config = GenerationConfig(
            candidate_count=1,
            max_output_tokens=args.max_tokens,
            temperature=args.temperature
        )
    
    data_size=len(dataset)
    testing_results=[]
    for i in tqdm(range(data_size)):
        data=dataset[i]
        func_name=data['func_name']
        desc=data['description']
        code=data['python_solution']
        difficulty=data['difficulty']
        code_withlineno=add_lineno(code)          

        #generate test case
        if args.covmode=='line':
            target_lines=data['target_lines']
            tests={}
            print(data['task_num'],target_lines)
            for lineno in target_lines: #line number to be tested
                code_lines=code.split('\n')
                target_line=code_lines[lineno-1]
                target_line_withlineno=f'{lineno}: {target_line}'

                code_input=code_withlineno
                line_input=target_line_withlineno

                prompt=prompt_template.format(lang='python', program=code_input, description=desc, func_name=func_name, lineno=line_input)
                prompt=system_message+prompt

                generated=model.generate_content(prompt, generation_config=generation_config)

                if generated.candidates[0].finish_reason==1: #normal stop
                    generated_test=generated.text
                else: #max_token, safety, ...
                    generated_test=''

                print(generated_test)
                tests[lineno]=generated_test                
            testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':tests}
        
        elif args.covmode=='branch':
            tests_branch=[]
            print(data['task_num'])
            branches=data['blocks']
            for branch in branches:
                print(branch)
                startline=branch['start']
                endline=branch['end']
                
                code_input=code_withlineno
                split_lines=code_withlineno.split('\n')
                target_lines=split_lines[startline-1:endline]
                target_branch_withlineno='\n'.join(target_lines)
                branch_input="\n'''\n"+target_branch_withlineno+"\n'''"

                prompt=prompt_template_branch.format(lang='python', program=code_input, description=desc, func_name=func_name, branch=branch_input)
                prompt=system_message+prompt
                generated=model.generate_content(prompt, generation_config=generation_config)
                if generated.candidates[0].finish_reason==1: #normal stop
                    generated_test=generated.text
                else: #max_token, safety, ...
                    generated_test=''
                print(generated_test)
                generatedtest_branch={'start':startline,'end':endline,'test':generated_test}
                tests_branch.append(generatedtest_branch)
            testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':tests_branch}

        testing_results.append(testing_data)
        
        print('<<<<----------------------------------------->>>>')
        write_jsonl(testing_results, output_dir / f'{args.covmode}cov_{model_abbrv}_temp.jsonl')
    write_jsonl(testing_results, output_dir / f'{args.covmode}cov_{model_abbrv}.jsonl')
