#!/usr/bin/env python3
import os
import sys

ref = os.environ['GITHUB_REF']
ref_name = os.environ['GITHUB_REF_NAME']
main_branch = os.environ['MAIN_BRANCH']

digest = sys.argv[1]
sha = os.environ['GITHUB_SHA']

if ref.startswith('refs/tags/'):
    name = 'nana'
    tag = f'latest@{digest}'
    pretty = f'tag {ref_name}'
else:
    name = 'hachi' if ref_name == main_branch else 'snow'
    tag = f'{ref_name}@{digest}'
    pretty = f'{ref_name}@{sha[:7]}'

print(f'::set-output name=name::{name}')
print(f'::set-output name=tag::{tag}')
print(f'::set-output name=pretty::{pretty}')
