#!/usr/bin/env python
import subprocess as sp

for url in open('youtube-urls.txt').read().split():
    sp.check_call(['yt-dlp', '--concurrent-fragments', '4', '--write-auto-subs', url])

