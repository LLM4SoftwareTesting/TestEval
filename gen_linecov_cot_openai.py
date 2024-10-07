import os
from argparse import ArgumentParser
from tqdm import tqdm
import openai
from openai import OpenAI
openai.api_key=os.getenv("OPENAI_API_KEY") 
client=OpenAI(api_key=openai.api_key)
from pathlib import Path
from data_utils import read_jsonl, write_jsonl, add_lineno, add_lineno_comment


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--model", type=str, default='gpt-3.5-turbo')
    
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0)
    return parser.parse_args()


def generate_completion(args,prompt,system_message=''):
    response = client.chat.completions.create(
        model=args.model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )
    code_output=response.choices[0].message.content
    return code_output


def generate_twostep(args,prompt_cond, prompt_test,system_message=''):
    messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_cond},
        ]
    response = client.chat.completions.create(
        model=args.model,
        messages=messages,
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )
    cond=response.choices[0].message.content
    print(cond)
    print('---------------------------------')
    
    messages.append({"role": "assistant", "content": cond})
    messages.append({"role": "user", "content": prompt_test})
    response = client.chat.completions.create(
        model=args.model,
        messages=messages,
        temperature=args.temperature,
        max_tokens=args.max_tokens
    )
    generated_test=response.choices[0].message.content
    print(generated_test)
    return cond, generated_test


if __name__=='__main__':
    args=parse_args()
    print('Model:', args.model)
    output_dir = Path('predictions')

    #two steps reasoning: generate conditions, then generate a test that satisfies the conditions
    prompt_template_cond=open('prompt/line_oneshot_gencond.txt').read()
    prompt_template_test=open('prompt/line_oneshot_gentest.txt').read()
    system_template=open('prompt/system_exec.txt').read()
    system_message=system_template

    dataset=read_jsonl('data/leetcode-py-all.jsonl')

    data_size=len(dataset)
    #data_size=50
    testing_results=[]
    for i in tqdm(range(data_size)):
        data=dataset[i]
        func_name=data['func_name']
        desc=data['description']
        code=data['python_solution']
        difficulty=data['difficulty']
        #code_withlineno=add_lineno(code)   
        code_withlineno=add_lineno_comment(code) 
        #print(code_withlineno)       

        #generate test case
        target_lines=data['target_lines']
        tests={}
        conds={} #store generated conditions
        print(data['task_num'],target_lines)

        for lineno in target_lines: #line number to be tested
            code_lines=code.split('\n')
            target_line=code_lines[lineno-1]
            target_line_withlineno=f'{lineno}: {target_line}'

            code_input=code_withlineno
            line_input=target_line_withlineno

            prompt_cond=prompt_template_cond.format(program=code_input, targetline=lineno)
            generated_cond=generate_completion(args,prompt_cond,system_message)
            prompt_test=prompt_template_test.format(func_name=func_name, program=code_input, conditions=generated_cond)
            generated_test=generate_completion(args,prompt_test,system_message)
            print(generated_cond)
            print('--------')
            print(generated_test)
            print('<--------------------------------------->')
            tests[lineno]=generated_test
            conds[lineno]=generated_cond
        testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':tests, 'conditions':conds}
        
        
        testing_results.append(testing_data)
        print('<<<<----------------------------------------->>>>')
        write_jsonl(testing_results, output_dir / f'linecov2_{args.model}_temp.jsonl')
    write_jsonl(testing_results, output_dir / f'linecov2_{args.model}_1shot.jsonl')
