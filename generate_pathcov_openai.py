import os
from argparse import ArgumentParser
from tqdm import tqdm
import openai
from openai import OpenAI
#openai.api_key=os.getenv("OPENAI_API_KEY") #personal key
#client=OpenAI(api_key=openai.api_key)
openai.api_key=os.getenv("OPENAI_API_KEY_M") #organization key: momentum
client=OpenAI(organization='org-cu9xNONvTuLH8PG5yOSM2RcX', api_key=openai.api_key)
from pathlib import Path
from data_utils import read_jsonl, write_jsonl, add_lineno, remove_examples
from prompt_utils import generate_path

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--lang", type=str, default='python')
    parser.add_argument("--model", type=str, default='gpt-3.5-turbo', choices=['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo', 'gpt-4o'])
    parser.add_argument("--lineno", type=str, default='true', choices=['true', 'false'], help='add line numbers to program under test')
    parser.add_argument("--targetcode", type=str, default='true', choices=['true', 'false'], help='provide target code in prompt, if false, provide line numbers only')
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
    print('Model:', args.model, 'Language:', args.lang)
    lang_ext='py'
    output_dir = Path('predictions')

    prompt_template=open(f'prompt/template_path.txt').read()
    system_template=open('prompt/system.txt').read()
    system_message=system_template.format(lang='python')

    #dataset=read_jsonl('LC_data/leetcode-bench-py-instrumented2.jsonl')
    dataset=read_jsonl('LC_data/leetcode-bench-py-path-instrumented.jsonl') #version without duplicate removal
    path_dataset=read_jsonl('LC_data/tgtpath_condition_5.jsonl') #version without duplicate removal
    data_size=len(dataset)
    testing_results=[]

    for i in tqdm(range(data_size)):
        data=dataset[i]
        #print(data.keys())
        #print(data['random_input_generator'])
        #print('---------')
        #print(data['python_solution_instrumented'])
        func_name=data['func_name']
        desc=data['description']
        code=data['python_solution']
        difficulty=data['difficulty']
        code_withlineno=add_lineno(code)           
        desc_noeg=remove_examples(desc)
        log_paths=path_dataset[i]['sampled_paths']
        condition_paths=path_dataset[i]['sampled_condition_paths']
        generated_path_tests=[]
        print(len(log_paths))
        for j in range(len(log_paths)):
            log_path=log_paths[j]
            condition_path=condition_paths[j]
            #print(log_path, condition_path)
            path_prompt=generate_path(condition_path)
            #path_prompt=generate_path(log_path)

            prompt=prompt_template.format(func_name=func_name, description=desc_noeg, program=code_withlineno, path=path_prompt)
            #print(prompt)
            #quit()
            generated_test=generate_completion(args,prompt,system_message)
            print(generated_test)
            generated_path_tests.append(generated_test)
        
        testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':generated_path_tests}
        testing_results.append(testing_data)

    write_jsonl(testing_results, output_dir / f'pathcov_{args.model}_5_2.jsonl')


#versions
#5_1: remove start and end in condition path
#5_2: remove start and end in condition path, connect with , instead of -> (new version, update prompt)
#5-3: log path, connect with ->
#5-4: 5-2(new version, update prompt)==5_2