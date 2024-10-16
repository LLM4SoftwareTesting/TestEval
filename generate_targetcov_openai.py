import os
from argparse import ArgumentParser
from tqdm import tqdm
import openai
from openai import OpenAI
openai.api_key=os.getenv("OPENAI_API_KEY") 
client=OpenAI(api_key=openai.api_key)
from pathlib import Path
from data_utils import read_jsonl, write_jsonl, add_lineno


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--model", type=str, default='gpt-3.5-turbo', choices=['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o'])
    parser.add_argument("--covmode", type=str, default='line', choices=['line', 'branch'], help='cover targets at line level or branch level')
    parser.add_argument("--max_tokens", type=int, default=256)
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


if __name__=='__main__':
    args=parse_args()
    print('Model:', args.model)
    print('task:', args.covmode)
    output_dir = Path('predictions')

    prompt_template=open('prompt/template_line.txt').read()
    prompt_template_branch=open('prompt/template_branch.txt').read()
    system_template=open('prompt/system.txt').read()
    system_message=system_template.format(lang='python')

    dataset=read_jsonl('data/leetcode-py.jsonl')

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

                generated_test=generate_completion(args,prompt,system_message)
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

                generated_test=generate_completion(args,prompt,system_message)
                print(generated_test)
                generatedtest_branch={'start':startline,'end':endline,'test':generated_test}
                tests_branch.append(generatedtest_branch)
            testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':tests_branch}
        
        testing_results.append(testing_data)
        print('<<<<----------------------------------------->>>>')
        write_jsonl(testing_results, output_dir / f'{args.covmode}cov_{args.model}_temp.jsonl')
    write_jsonl(testing_results, output_dir / f'{args.covmode}cov_{args.model}.jsonl')
