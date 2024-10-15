import os
import transformers
import torch
import textwrap
from pathlib import Path
from argparse import ArgumentParser
from tqdm import tqdm

from transformers import LlamaForCausalLM, CodeLlamaTokenizer, AutoTokenizer, AutoModelForCausalLM
from transformers import pipeline
access_token=os.getenv("HUGGINGFACE_TOKEN")

from data_utils import read_jsonl, write_jsonl, add_lineno
from prompt_utils import generate_path


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--dataset", type=str, default='leetcode')
    parser.add_argument("--lang", type=str, default='python', choices=['python', 'java', 'c++'])
    parser.add_argument("--model", type=str, default='codellama/CodeLlama-7b-Instruct-hf')
    parser.add_argument("--temperature", type=float, default=1e-5)
    parser.add_argument("--max_tokens", type=int, default=256)
    return parser.parse_args()


model_list=['codellama/CodeLlama-7b-Instruct-hf','codellama/CodeLlama-13b-Instruct-hf','codellama/CodeLlama-34b-Instruct-hf',
            'meta-llama/Meta-Llama-3-8B-Instruct',
            'bigcode/starcoder2-15b-instruct-v0.1',
            'google/gemma-1.1-7b-it'
            'deepseek-ai/deepseek-coder-1.3b-instruct', 'deepseek-ai/deepseek-coder-6.7b-instruct',
            'deepseek-ai/deepseek-coder-33b-instruct',
            'mistralai/Mistral-7B-Instruct-v0.3'
            ]

#models do not support system message
models_nosys=['google/gemma-1.1-7b-it',
            'bigcode/starcoder2-15b-instruct-v0.1',
            'mistralai/Mistral-7B-Instruct-v0.3']


if __name__=='__main__':
    args=parse_args()
    model_abbrv=args.model.split('/')[-1]
    print('Model:', model_abbrv)
    output_dir = Path('predictions')

    prompt_template=open('prompt/template_path.txt').read()
    system_template=open('prompt/system.txt').read()
    system_message=system_template.format(lang='python')

    dataset=read_jsonl('data/leetcode-py-instrumented.jsonl')
    path_dataset=read_jsonl('data/tgt_paths.jsonl')
    data_size=len(dataset)
    testing_results=[]

    model = AutoModelForCausalLM.from_pretrained(args.model, token=access_token, torch_dtype=torch.bfloat16, trust_remote_code=True, device_map='auto')
    tokenizer = AutoTokenizer.from_pretrained(args.model, token=access_token, torch_dtype=torch.bfloat16, trust_remote_code=True, device_map='auto')
    generator = pipeline("text-generation",model=model, tokenizer=tokenizer, torch_dtype=torch.bfloat16, device_map='auto', token=access_token)

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
            generated_test=generated[0]['generated_text']
            if generated_test.startswith('  '): #remove extra indents (encountered in codellama)
                generated_test=textwrap.dedent(generated_test)
            print(generated_test)
            generated_path_tests.append(generated_test)
        
        testing_data={'task_num':data['task_num'],'task_title':data['task_title'],'func_name':func_name,'difficulty':difficulty,'code':code,'tests':generated_path_tests}
        testing_results.append(testing_data)

    write_jsonl(testing_results, output_dir / f'pathcov_{model_abbrv}.jsonl')
