#!/usr/bin/env python3
import os

ref = os.environ['GITHUB_REF']
ref_name = os.environ['GITHUB_REF_NAME']
main_branch = os.environ['MAIN_BRANCH']

registry = os.environ['REGISTRY']
image_name = os.environ['IMAGE_NAME']

if ref.startswith('refs/tags/'):
    branch = main_branch
    tags = f'{registry}/{image_name}:latest'
else:
    branch = ref_name
    tags = f'{registry}/{image_name}:{ref_name}'


print(f'::set-output name=branch::{branch}')
print(f'::set-output name=tags::{tags}')
