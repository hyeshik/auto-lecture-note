VIDEOFILES = glob_wildcards('video/{name}.mp4').name
SCENEDETECTION_THRESHOLD = 10

rule all:
    input:
        expand('scenes/{name}-Scenes.csv', name=VIDEOFILES),
        expand('scenes/{name}-Stats.csv', name=VIDEOFILES),
        expand('scene-transcripts/{name}.tsv', name=VIDEOFILES),
        expand('notes/{name}/done', name=VIDEOFILES)

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
    output: 'notes/{name}/done'
    params: output_dir='notes/{name}'
    resources: openai=1
    shell: 'python transcript-to-note.py "{input}" "{params.output_dir}"'