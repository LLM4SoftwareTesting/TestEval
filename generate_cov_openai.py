#baseline for targeted line coverage: not providing the target line number
import os
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm
import openai
from openai import OpenAI
openai.api_key=os.getenv("OPENAI_API_KEY") #personal key
client=OpenAI(api_key=openai.api_key)

from data_utils import read_jsonl, write_jsonl, add_lineno


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--lang", type=str, default='python')
    parser.add_argument("--model", type=str, default='gpt-3.5-turbo', choices=['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o'])
    parser.add_argument("--num_tests", type=int, default=10, help='number of tests generated per program')
    parser.add_argument("--temperature", type=float, default=0)
    parser.add_argument("--max_tokens", type=int, default=256)
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


def testgeneration_multiround(args,prompt,system_message=''):
    """generate test cases with multi-round conversation, each time generate one test case"""
    template_append="Generate another test method for the function under test. Your answer must be different from previously-generated test cases, and should cover different statements and branches."
    generated_tests=[]
    messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]
    for i in range(args.num_tests):
        response = client.chat.completions.create(
            model=args.model,
            messages=messages,
            temperature=args.temperature,
            max_tokens=args.max_tokens
        )
        generated_test=response.choices[0].message.content
        messages.append({"role": "assistant", "content": generated_test})
        messages.append({"role": "user", "content": template_append})

        generated_tests.append(generated_test)
        print(generated_test)

    return generated_tests


lang_exts={'python':'py', 'java':'java', 'c++':'cpp'}


if __name__=='__main__':
    args=parse_args()
    print('Model:', args.model)
    output_dir = Path('predictions')

    dataset=read_jsonl('data/leetcode-py.jsonl')

    prompt_template=open('prompt/template_base.txt').read()
    system_template=open('prompt/system.txt').read()
    system_message=system_template.format(lang='python')

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

        #generate test case
        prompt=prompt_template.format(lang='python', program=code, description=desc, func_name=func_name)
        generated_tests=testgeneration_multiround(args,prompt,system_message)
                   
        testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':generated_tests}
        testing_results.append(testing_data)
        print('<<<<----------------------------------------->>>>')
        write_jsonl(testing_results, output_dir / f'totalcov_{args.model}_temp.jsonl')

    write_jsonl(testing_results, output_dir / f'totalcov_{args.model}.jsonl')
