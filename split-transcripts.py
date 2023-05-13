#!/usr/bin/env python
import webvtt
import re
import pandas as pd

pat_vtttime = re.compile(r'<\d\d:\d\d:\d\d\.\d\d\d>')

def strip_c(txt):
    if txt.startswith('<c>'):
        txt = txt[3:]
    if txt.endswith('</c>'):
        txt = txt[:-4]
    return txt

def parse_vtt_line(row):
    linestart_in_seconds = row['start']
    txt = row['line2']

    matches = []
    for match in pat_vtttime.finditer(txt):
        tm = match.group()[1:-1]
        toks = list(map(float, tm.split(':')))
        assert len(toks) == 3
        timemark = toks[0] * 3600 + toks[1] * 60 + toks[2]
        matches.append((match.start(), match.end(), timemark))

    matches = pd.DataFrame(matches, columns=['start', 'end', 'timemark'])

    txtparts = pd.DataFrame({
        'txtstart': [0] + list(matches['end']),
        'txtend': list(matches['start']) + [len(txt)],
        'timestart': [linestart_in_seconds] + list(matches['timemark']),
    })
    txtparts['txt'] = txtparts.apply(lambda row: strip_c(txt[int(row['txtstart']):int(row['txtend'])]), axis=1)

    return txtparts

def load_vtt(vttfile):
    rows = []
    for caption in webvtt.read(vttfile):
        assert len(caption.lines) == 2
        rows.append([
            caption.start_in_seconds,
            caption.end_in_seconds,
            caption.lines[0],
            caption.lines[1],
        ])
    vtt = pd.DataFrame(rows, columns=['start', 'end', 'line1', 'line2'])

    tokentimings = []
    for _, row in vtt.iterrows():
        tokentimings.append(parse_vtt_line(row))
    tokentimings = pd.concat(tokentimings)

    tokentimings['timeend'] = tokentimings['timestart'].shift(-1)
    validtokens = tokentimings[tokentimings['txt'].apply(lambda x: len(x.strip())) > 0]
    validtokens = validtokens['timestart timeend txt'.split()].copy()
    validtokens.columns = ['start', 'end', 'token']
    validtokens['token'] = validtokens['token'].apply(lambda x: x.strip())

    return validtokens.reset_index(drop=True)

def load_scenic_transcripts(vttfile, scenefile, min_scene_length=5):
    transcript_tokens = load_vtt(vttfile)
    sceneinfo = pd.read_csv(scenefile, skiprows=1)

    scene_transcripts = []
    for _, scene in sceneinfo.iterrows():
        scenestart, sceneend = scene['Start Time (seconds)'], scene['End Time (seconds)']
        scene_transcript = transcript_tokens[transcript_tokens['start'].between(scenestart, sceneend)]
        scene_transcripts.append([
            scenestart, sceneend,
            scene['Start Timecode'], scene['End Timecode'],
            len(scene_transcript), ' '.join(scene_transcript['token'])])
    scene_transcripts = pd.DataFrame(scene_transcripts,
                                     columns='start end start_time end_time num_tokens transcript'.split())

    return scene_transcripts[scene_transcripts['num_tokens'] >= min_scene_length].reset_index(drop=True)

def diffuse_boundary(transcripts, max_diffusion=5):
    transcripts = transcripts.copy()

    tails = transcripts['transcript'].apply(lambda x: ' '.join(x.split()[-max_diffusion:]))
    heads = transcripts['transcript'].apply(lambda x: ' '.join(x.split()[:max_diffusion]))

    prefixes = pd.Series([''] + list(tails[:-1]))
    suffixes = pd.Series(list(heads[1:]) + [''])

    transcripts['transcript'] = prefixes + ' ' + transcripts['transcript'] + ' ' + suffixes
    return transcripts


if __name__ == '__main__':
    import sys
    subtitle_file = sys.argv[1]
    scene_file = sys.argv[2]
    output_file = sys.argv[3]

    transcripts = load_scenic_transcripts(subtitle_file, scene_file)
    diffuse_boundary(transcripts).to_csv(output_file, index=False, sep='\t')
