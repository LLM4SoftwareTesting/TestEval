import google.generativeai as genai
from google.generativeai import GenerationConfig

api_key=os.getenv("GOOGLE_API_KEY")

import os
import time
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm

from data_utils import read_jsonl, write_jsonl, add_lineno
from prompt_utils import generate_path

genai.configure(api_key=api_key)

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--lang", type=str, default='python')
    parser.add_argument("--model", type=str, default='models/gemini-1.5-flash-latest', choices=['models/gemini-1.0-pro-latest', 'models/gemini-1.5-pro-latest', 'models/gemini-1.5-flash-latest'])
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max_tokens", type=int, default=256)
    return parser.parse_args()


if __name__=='__main__':
    args=parse_args()
    print('Model:', args.model)
    model_abbrv=args.model.split('/')[-1]
    model = genai.GenerativeModel(args.model)
    output_dir = Path('predictions')

    prompt_template=open('prompt/template_path.txt').read()
    system_template=open('prompt/system.txt').read()
    system_message=system_template.format(lang='python')

    generation_config = GenerationConfig(
        candidate_count=1,
        max_output_tokens=args.max_tokens,
        temperature=args.temperature
    )

    dataset=read_jsonl('data/leetcode-py-instrumented.jsonl')
    path_dataset=read_jsonl('data/tgt_paths.jsonl')
    data_size=len(dataset)
    testing_results=[]

    for i in tqdm(range(data_size)):
        data=dataset[i]
        func_name=data['func_name']
        desc=data['description']
        code=data['python_solution']
        difficulty=data['difficulty']
        code_withlineno=add_lineno(code)           
        log_paths=path_dataset[i]['sampled_paths']
        condition_paths=path_dataset[i]['sampled_condition_paths']
        generated_path_tests=[]
        for j in range(len(log_paths)):
            log_path=log_paths[j]
            condition_path=condition_paths[j]
            #print(log_path, condition_path)
            
            path_prompt=generate_path(condition_path)
            prompt=prompt_template.format(func_name=func_name, description=desc, program=code_withlineno, path=path_prompt)
            prompt=system_message+prompt

            generated=model.generate_content(prompt, generation_config=generation_config)
            if generated.candidates[0].finish_reason==1: #normal stop
                generated_test=generated.text
            else: #max_token, safety, ...
                generated_test=''
            print(generated_test)
            generated_path_tests.append(generated_test)
        
        testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':generated_path_tests}
        testing_results.append(testing_data)

    write_jsonl(testing_results, output_dir / f'pathcov_{model_abbrv}.jsonl')
