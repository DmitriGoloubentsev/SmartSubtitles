#!/usr/bin/env python3
"""Embed local img sources in an existing HTML guide for single-file uploads."""
import argparse
import base64
import html
import mimetypes
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def embed_images(path):
    path = Path(path).resolve()
    count = 0

    def replace(match):
        nonlocal count
        source = html.unescape(match['source'])
        url = urlsplit(source)
        if url.scheme or url.netloc:
            return match.group(0)
        image = (path.parent / unquote(url.path)).resolve()
        mime = mimetypes.guess_type(image.name)[0]
        if not mime or not mime.startswith('image/'):
            raise ValueError(f'Unsupported image: {image}')
        encoded = base64.b64encode(image.read_bytes()).decode('ascii')
        count += 1
        return match['prefix'] + match['quote'] + f'data:{mime};base64,{encoded}' + match['quote']

    # Preserve the existing HTML exactly except for quoted img src attributes.
    pattern = r'''(?P<prefix><img\b[^>]*?\bsrc\s*=\s*)(?P<quote>["'])(?P<source>.*?)(?P=quote)'''
    result = re.sub(pattern, replace, path.read_text(encoding='utf-8'), flags=re.I | re.S)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(result, encoding='utf-8')
    temporary.replace(path)
    print(f'{path}: embedded {count} images ({path.stat().st_size:,} bytes)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('html_file', type=Path)
    embed_images(parser.parse_args().html_file)
