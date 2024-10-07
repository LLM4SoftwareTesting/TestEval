import os
import transformers
import torch
import textwrap
from argparse import ArgumentParser
from tqdm import tqdm
from pathlib import Path

from transformers import LlamaForCausalLM, CodeLlamaTokenizer, AutoTokenizer, AutoModelForCausalLM
from transformers import pipeline
access_token=os.getenv("HUGGINGFACE_TOKEN")

from data_utils import read_jsonl, write_jsonl, add_lineno, add_lineno_comment

def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--lang", type=str, default='python', choices=['python', 'java', 'c++'])
    parser.add_argument("--model", type=str, default='meta-llama/Meta-Llama-3-8B-Instruct')
    parser.add_argument("--covmode", type=str, default='line', choices=['line', 'branch'], help='cover targets at line level or branch level')
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=1e-5)
    return parser.parse_args()


#models do not support system message
models_nosys=['google/gemma-1.1-7b-it',
            'bigcode/starcoder2-15b-instruct-v0.1',
            'mistralai/Mistral-7B-Instruct-v0.3']


def generate_completion(args, generator, prompt, system_message=''):
    if args.model in models_nosys: #models don't support system message
        messages=[{"role": "user", "content": system_message+prompt}]
    else:
        messages=[
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    prompt = generator.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    generated=generator(prompt, 
                        max_new_tokens=args.max_tokens, 
                        temperature=args.temperature, 
                        return_full_text=False)
    generated_text=generated[0]['generated_text']
    return generated_text


if __name__=='__main__':
    args=parse_args()
    model_abbrv=args.model.split('/')[-1]
    print('Model:', model_abbrv)
    print('task:', args.covmode)
    output_dir = Path('predictions')

    prompt_template_cond=open('prompt/line_oneshot_gencond.txt').read()
    prompt_template_test=open('prompt/line_oneshot_gentest.txt').read()
    system_template=open('prompt/system_exec.txt').read()
    system_message=system_template

    dataset=read_jsonl('data/leetcode-py-all.jsonl')

    model = AutoModelForCausalLM.from_pretrained(args.model, token=access_token, torch_dtype=torch.bfloat16, trust_remote_code=True, device_map='auto')
    tokenizer = AutoTokenizer.from_pretrained(args.model, token=access_token, torch_dtype=torch.bfloat16, trust_remote_code=True, device_map='auto')
    generator = pipeline("text-generation",model=model, tokenizer=tokenizer, torch_dtype=torch.bfloat16, device_map='auto', token=access_token)

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
            generated_cond=generate_completion(args,generator,prompt_cond,system_message)
            prompt_test=prompt_template_test.format(func_name=func_name, program=code_input, conditions=generated_cond)
            generated_test=generate_completion(args,generator,prompt_test,system_message)
            print(generated_cond)
            print('--------')
            print(generated_test)
            print('<--------------------------------------->')
            tests[lineno]=generated_test
            conds[lineno]=generated_cond
        testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':tests, 'conditions':conds}

        testing_results.append(testing_data)
        print('<<<<----------------------------------------->>>>')
        write_jsonl(testing_results, output_dir / f'linecov2_{model_abbrv}_temp.jsonl')
    write_jsonl(testing_results, output_dir / f'linecov2_{model_abbrv}_1shot.jsonl')
