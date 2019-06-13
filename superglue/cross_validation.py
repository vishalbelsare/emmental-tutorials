"""
THE PLAN:
Make temp directory
Merge and shuffle train and val files
fill subdirectories with splits
Run search.py with a config that points to the subdirs
Combine the probabilities from all runs

Sample command sequence:
python cross_validation.py --task_name WiC --cv_dir $SUPERGLUEDATA/WiC/folds --data_dir $SUPERGLUEDATA --folds 10
[UPDATE config.json with only data_dir in the search space]
python search.py --config config.json --max_search 10 --logdir /path/to/logs
python merge_probs.py --task_name WiC --root /path/to/logs

"""

import os
import random
import subprocess

import click

from task_config import SuperGLUE_TASK_SPLIT_MAPPING

@click.command()
@click.option('--task_name', required=True)
@click.option('--cv_dir', required=True)
@click.option('--data_dir', default=os.environ["SUPERGLUEDATA"])
@click.option('--seed', default=111)
@click.option('--folds', default=5)
def make_cv_files(task_name, cv_dir, data_dir, seed, folds):
    random.seed(seed)

    # Make temp dir
    if not os.path.exists(cv_dir):
        os.makedirs(cv_dir)
    
    # Merge and shuffle train and val files
    train_name = SuperGLUE_TASK_SPLIT_MAPPING[task_name]["train"]
    train = os.path.join(data_dir, task_name, train_name)

    val_name = SuperGLUE_TASK_SPLIT_MAPPING[task_name]["val"]
    val = os.path.join(data_dir, task_name, val_name)

    test_name = SuperGLUE_TASK_SPLIT_MAPPING[task_name]["test"]
    test = os.path.join(data_dir, task_name, test_name)

    combined = os.path.join(cv_dir, "combined.jsonl")
    subprocess.call(f'cat {train} {val} | shuf > {combined}', shell=True)
    
    # Fill subdirectories with splits
    total_lines = int((subprocess.check_output(f'wc -l {combined}', shell=True)).split()[0])
    print(f"Making {folds} folds out of {total_lines} total examples.")
    subprocess.call(f"cd {cv_dir}; split -l {int(total_lines/folds)} -a 1 -d {combined}", shell=True)
    assert folds <= 10  # Based on format of files generated by `split` command
    fold_subdirs = []
    for val_fold_idx in range(folds):
        train_folds = [f"{cv_dir}/x{fold}" for fold in range(folds) if fold != val_fold_idx]
        val_fold = f"{cv_dir}/x{val_fold_idx}"
        fold_subdir = os.path.join(cv_dir, f"fold{val_fold_idx}", task_name)
        fold_subdirs.append(fold_subdir)
        if not os.path.exists(fold_subdir):
            os.makedirs(fold_subdir)
        subprocess.call(f"cat {' '.join(train_folds)} > {fold_subdir}/train.jsonl", shell=True)
        subprocess.call(f"cp {val_fold} {fold_subdir}/val.jsonl", shell=True)
        subprocess.call(f"cp {test} {fold_subdir}/test.jsonl", shell=True)
    
    # Print files necessary for search.py
    print("Data directories for search.py:")
    for fold_subdir in fold_subdirs:
        print('/'.join(fold_subdir.split('/')[:-1]))

if __name__ == '__main__':
    make_cv_files()