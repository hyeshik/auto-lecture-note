VIDEONAMES = glob_wildcards('video/{name}.mp4').name
SCENEDETECTION_THRESHOLD = 10

rule all:
    input:
        expand('scenes/{name}-Scenes.csv', name=VIDEONAMES),
        expand('scenes/{name}-Stats.csv', name=VIDEONAMES),
        expand('scene-transcripts/{name}.tsv', name=VIDEONAMES),
        expand('scene-notes/{name}/done', name=VIDEONAMES),
        expand('notes/{name}.{dtype}', name=VIDEONAMES, dtype=['md', 'html'])

rule detect_scene:
    input: 'video/{name}.mp4'
    output:
        scenes='scenes/{name}-Scenes.csv',
        stats='scenes/{name}-Stats.csv'
    params:
        stats_filename='{name}-Stats.csv'
    shell:
        'scenedetect -o scenes --input "{input}" --stats "{params.stats_filename}" \
            detect-content -t {SCENEDETECTION_THRESHOLD} \
            list-scenes'

rule split_transcripts:
    input:
        vtt='video/{name}.en.vtt',
        scenes='scenes/{name}-Scenes.csv'
    output: 'scene-transcripts/{name}.tsv'
    shell: 'python split-transcripts.py "{input.vtt}" "{input.scenes}" "{output}"'

rule convert_transcript_to_notes:
    input: 'scene-transcripts/{name}.tsv'
    output: 'scene-notes/{name}/done'
    params: output_dir='scene-notes/{name}'
    resources: openai=1
    shell: 'python transcript-to-note.py "{input}" "{params.output_dir}"'

rule merge_notes:
    input:
        transcripts='scene-transcripts/{name}.tsv',
        scene_notes_done_mark='scene-notes/{name}/done'
    output: 'notes/{name}.md'
    params: notedir='scene-notes/{name}'
    run:
        import pandas as pd

        notename = wildcards.name
        transcripts = pd.read_csv(input.transcripts, sep='\t')

        with open(output[0], 'w') as output:
            for scene_no, row in transcripts.iterrows():
                scene_no += 1 # make scene numbers 1-indexed

                notefile = f'{params.notedir}/{scene_no:04d}-answer.md'
                note = open(notefile).read().splitlines()
                note.insert(1, f'Time: {row["start_time"]} – {row["end_time"]}')

                print(*note, sep='\n', file=output, end='\n\n')

rule format_html_notes:
    input: 'notes/{name}.md'
    output: 'notes/{name}.html'
    shell: 'pandoc -f markdown -t html "{input}" -o "{output}"'
