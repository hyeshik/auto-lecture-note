#!/usr/bin/env python
import openai, os
import pandas as pd
from collections import deque
import json
import sys

openai.api_key_path = os.environ['HOME'] + '/.openai-api'

system_instruction = """\
You are a university lecturer teaching virology for biology majors. Based on \
the transcript provided by user, you will prepare lecture notes for the part. \
The lecture note should start with a brief title in a single sentence. \
The body must be prepared in multiple bullet points. The answer should be \
in Korean. In the body, the scientific terms should be used in Korean with \
the English term in parenthesis. The body should not miss any important points \
from the transcript. The body should be concise and easy to understand. The \
answer must be formatted in Markdown. Use the first level heading for the \
title and the body should be in bullet points under the title. \
"""

transcript_file = sys.argv[1]
output_dir = sys.argv[2]
context_size = 4

if not os.path.isdir(output_dir):
    os.makedirs(output_dir)

transcripts = pd.read_csv(transcript_file, sep='\t')
system_context = [{'role': 'system', 'content': system_instruction}]
context = deque()
for scene_no, row in transcripts.iterrows():
    scene_no += 1 # make it 1-based
    output_prefix = f'{output_dir}/{scene_no:04d}'
    context_file = output_prefix + '-context.json'

    if os.path.isfile(context_file):
        context = deque(json.load(open(context_file)))
        print(f'==> Skipping scene {scene_no}')
        continue

    transcript = row['transcript']
    context.append({
        'role': 'user',
        'content': transcript})
    while len(context) > context_size:
        context.popleft()

    print(f'==> Requesting completion for scene {scene_no}')
    response = openai.ChatCompletion.create(
        model='gpt-4',
        messages=system_context + list(context),
        temperature=0.4,
        top_p=1,
        max_tokens=1000,
        frequency_penalty=0.0
    )

    answer = response['choices'][0]['message']
    context.append(answer)

    json.dump(list(context), open(context_file, 'w'),
              indent=2, ensure_ascii=False)
    open(output_prefix + '-answer.md', 'w').write(answer['content'])

    title = answer['content'].splitlines()[0]
    num_bullets = sum(bool(l.strip()) for l in answer['content'].splitlines()) - 1

    print(f'   {title}')
    print(f'   {num_bullets} Bullets.')
    print(f'   - Used {response["usage"]["prompt_tokens"]} prompt and '
          f'{response["usage"]["completion_tokens"]} completion tokens.')

open(f'{output_dir}/done', 'w')
