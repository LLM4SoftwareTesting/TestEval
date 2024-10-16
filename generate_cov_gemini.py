import google.generativeai as genai
from google.generativeai import GenerationConfig
import os
import time
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm

api_key=os.getenv("GOOGLE_API_KEY")

from data_utils import read_jsonl, write_jsonl, add_lineno

genai.configure(api_key=api_key)

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--lang", type=str, default='python')
    parser.add_argument("--model", type=str, default='models/gemini-1.0-pro-latest', choices=['models/gemini-1.0-pro-latest', 'models/gemini-1.5-pro-latest', 'models/gemini-1.5-flash-latest'])
    parser.add_argument("--num_tests", type=int, default=20, help='number of tests generated per program')
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max_tokens", type=int, default=256)
    return parser.parse_args()


def testgeneration_multiround(args, model, prompt):
    """generate test cases with multi-round conversation, each time generate one test case"""
    template_append="Generate another test method for the function under test. Your answer must be different from previously-generated test cases, and should cover different statements and branches."
    generated_tests=[]

    for i in range(args.num_tests):
        generated=model.generate_content(prompt, generation_config=generation_config)
        if generated.candidates[0].finish_reason==1: #normal stop
            generated_test=generated.text
        else: #max_token, safety, ...
            generated_test=''
        print(generated_test)

        test_append=f'''Generated test:
        {generated_test}'''
        prompt+=test_append
        prompt+='\n'
        prompt+=template_append

        generated_tests.append(generated_test)

    return generated_tests


if __name__=='__main__':
    args=parse_args()
    print('Model:', args.model)
    model_abbrv=args.model.split('/')[-1]
    model = genai.GenerativeModel(args.model)
    #print(model)
    output_dir = Path('predictions')

    dataset=read_jsonl('LC_data/leetcode-bench-py.jsonl')

    prompt_template=open('prompt/template_base.txt').read()
    system_template=open('prompt/system.txt').read()
    system_message=system_template.format(lang='python')

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
        target_lines=data['target_lines']

        #generate test cases
        prompt=prompt_template.format(lang='python', program=code, description=desc, func_name=func_name)
        prompt=system_message+prompt
        generated_tests=testgeneration_multiround(args,model,prompt)

        testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':generated_tests}
        testing_results.append(testing_data)
        print('<<<<----------------------------------------->>>>')
        write_jsonl(testing_results, output_dir / f'totalcov_{model_abbrv}_temp.jsonl')
    
    write_jsonl(testing_results, output_dir / f'totalcov_{model_abbrv}.jsonl')
