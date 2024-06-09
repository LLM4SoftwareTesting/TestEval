# TestEval

## Data

## Quick Start

Install dependencies

```bash
pip install -r requirements.txt
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

### Run baselines: targeted branch coverage

```bash
python eval_base.py --path {path_to_formatted_generated_tests}  #evaluate targeted line/branch coverage for baselines: use the test cases generate from the overall coverage task
```

### Run baselines: targeted path coverage

```bash
python eval_pathcov_base.py --path {path_to_formatted_generated_tests}  #evaluate targeted line/branch coverage for baselines: use the test cases generate from the overall coverage task
```
