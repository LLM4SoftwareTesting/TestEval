# TestEval

Dataset and benchmark for paper "TESTEVAL: Benchmarking Large Language Models for Test Case Generation".

## Data

### Dataset description

| category | data |
|------|------|
| total programs under test | 210 |
| total target lines | 1340 |
| total target branches | 983 |
| total target paths | 854 |

### Metadata

| field name | data type | description |
|------|------|------|
| task_num | int | Problem id in LeetCode |
| task_title | string | LeetCode problem title |
| difficulty | int | LeetCode problem difficulty: from 0 (easy) to 2 (hard) |
| func_name | string | Default function name for the solution |
| description | string | LeetCode problem description |
| python_solution | string | LeetCode problem solution in Python (the program under test) |
| blocks | list | The list for target branches |
| target_lines | list | The list for target lines |
| python_solution_instrumented | string | Add instrumentations to python_solution for recording execution paths |
| sampled_paths | list | The list of target paths, the format is the same as the execution paths collected from python_solution_instrumented |
| sampled_condition_paths | list | The list of target paths, used in prompts |

## Quick Start

Requirements: Python>=3.10

Install dependencies

```bash
pip install -r requirements.txt
```

Create folder to store generated tests

```bash
mkdir predictions
```

Set environment variables

```
OPENAI_API_KEY: openai api key
GOOGLE_API_KEY: gemini api key
HUGGINGFACE_TOKEN: huggingface access token
```

### Run experiments: overall coverage

```bash
python generate_cov_{openai/gemini/hf}.py --model {model_name} --num_tests 20  #generate raw test cases
python format.py --mode overall --path {path_to_generated_tests}  #reformat test cases
python eval_overall.py --path {path_to_formatted_generated_tests}  #evaluate correctness and coverage metrics
```

### Run experiments: targeted line coverage

```bash
python generate_targetcov_{openai/gemini/hf}.py --covmode line --model {model_name} #generate raw test cases
python format.py --mode line --path {path_to_generated_tests}  #reformat test cases
python eval_linecov.py --path {path_to_formatted_generated_tests}  #evaluate correctness and coverage metrics
```

### Run experiments: targeted line coverage with two-step reasoning

```bash
python gen_linecov_cot_{openai/hf}.py --model {model_name} #generate reasoning steps and raw test cases
python format.py --mode line --path {path_to_generated_tests}  #reformat test cases
python eval_linecov.py --path {path_to_formatted_generated_tests}  #evaluate correctness and coverage metrics
```

### Run experiments: targeted branch coverage

```bash
python generate_targetcov_{openai/gemini/hf}.py --covmode branch --model {model_name} #generate raw test cases
python format.py --mode branch --path {path_to_generated_tests}  #reformat test cases
python eval_branchcov.py --path {path_to_formatted_generated_tests}  #evaluate correctness and coverage metrics
```

### Run experiments: targeted path coverage

```bash
python generate_pathcov_{openai/gemini/hf}.py --model {model_name} #generate raw test cases
python format.py --mode overall --path {path_to_generated_tests}  #reformat test cases
python eval_pathcov.py --path {path_to_formatted_generated_tests}  #evaluate correctness and coverage metrics
```

### Run baselines: targeted line/branch coverage

```bash
python eval_base.py --path {path_to_formatted_generated_tests}  #evaluate targeted line/branch coverage for baselines: use the test cases generate from the overall coverage task
```

### Run baselines: targeted path coverage

```bash
python eval_pathcov_base.py --path {path_to_formatted_generated_tests}  #evaluate targeted line/branch coverage for baselines: use the test cases generate from the overall coverage task
```

### Run your own pipeline

We encourage researchers to use their own test case generation pipeline other than our prompt framework. If you run your own pipeline, your generated test case file should be formatted as:

Overall coverage:

```
{'task_num': LeetCode problem id, 'difficulty': LeetCode problem difficulty, 'func_name': solution function name, 'code': solution code, 'tests': list of generated test cases}
```

Targeted line coverage: 

```
{'task_num': LeetCode problem id, 'difficulty': LeetCode problem difficulty, 'func_name': solution function name, 'code': solution code, 'tests': {target line number: test case for target line}}
```

Targeted branch coverage:

```
{'task_num': LeetCode problem id, 'difficulty': LeetCode problem difficulty, 'func_name': solution function name, 'code': solution code, 'tests': [{"start": branch start line, "end": branch end line, "test": test case for target branch}]}
```

Targeted path coverage:

```
{'task_num': LeetCode problem id, 'difficulty': LeetCode problem difficulty, 'func_name': solution function name, 'code': solution code, 'tests': list of generated test cases for each target path}
```

