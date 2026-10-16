#!/usr/bin/env python3
"""Render an agent-authored Markdown guide; embed local illustrations."""
import argparse
from pathlib import Path
import markdown
from embed_guide_images import embed_images


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('markdown_file', type=Path)
    args = parser.parse_args()
    source = args.markdown_file.resolve()
    output = source.with_suffix('.html')
    body = markdown.markdown('[TOC]\n\n' + source.read_text(encoding='utf-8'),
                             extensions=['tables', 'fenced_code', 'toc'])
    css = ('body{max-width:1100px;margin:40px auto;padding:0 24px;font:18px/1.6 system-ui}'
           'img{max-width:100%;height:auto}table{border-collapse:collapse;width:100%}'
           'td,th{padding:9px;border:1px solid #ccd;vertical-align:top}'
           'pre{white-space:pre-wrap;overflow-wrap:anywhere}')
    output.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                      '<meta name="viewport" content="width=device-width,initial-scale=1">'
                      '<title>Viewing guide</title><style>' + css + '</style></head><body>'
                      + body + '</body></html>', encoding='utf-8')
    embed_images(output)


if __name__ == '__main__':
    main()
