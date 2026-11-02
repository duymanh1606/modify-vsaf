#!/usr/bin/env python3
"""
confluence_fetch.py — Fetch a Confluence page and convert to clean Markdown.

Usage:
  python confluence_fetch.py --base-url http://host:8090 --token <PAT> --url <page-url>
  python confluence_fetch.py --base-url http://host:8090 --token <PAT> --page-id 123456

Output: JSON to stdout
  { "page_id": "...", "title": "...", "url": "...", "markdown": "..." }
"""

import sys
import json
import re
import argparse
import urllib.request
import urllib.parse
import html as html_module
from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# Page ID extraction
# ---------------------------------------------------------------------------

def extract_page_id(url):
    """Pull the numeric Confluence page ID from various URL forms."""
    # ?pageId=123456
    m = re.search(r'[?&]pageId=(\d+)', url)
    if m:
        return m.group(1)
    # /pages/123456/Title  (Confluence Cloud style)
    m = re.search(r'/pages/(\d+)', url)
    if m:
        return m.group(1)
    # bare numeric string
    if re.fullmatch(r'\d+', url.strip()):
        return url.strip()
    return None


# ---------------------------------------------------------------------------
# HTML → Markdown converter
# ---------------------------------------------------------------------------

class _HTMLToMD(HTMLParser):
    """Single-pass HTML → Markdown converter tuned for Confluence storage format."""

    SKIP_TAGS = {
        'style', 'script', 'head',
        # Confluence macros / metadata
        'ac:structured-macro', 'ac:parameter', 'ac:plain-text-body',
        'ac:rich-text-body', 'ac:image', 'ac:link', 'ac:emoticon',
        'ri:attachment', 'ri:page', 'ri:space', 'ri:url',
    }
    BLOCK_TAGS = {'p', 'div', 'section', 'article', 'blockquote', 'figure'}
    HEADING_TAGS = {'h1': '#', 'h2': '##', 'h3': '###', 'h4': '####', 'h5': '#####', 'h6': '######'}

    def __init__(self, base_url=''):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url.rstrip('/')
        self._out = []
        self._tag_stack = []      # (tag, attrs_dict)
        self._skip_depth = 0      # depth inside a SKIP_TAG tree
        self._list_stack = []     # ('ul'|'ol', counter)
        self._in_pre = False
        self._in_code = False
        self._table_rows = []     # list of lists of cell strings
        self._current_row = []
        self._current_cell = []
        self._in_table = False
        self._pending_newlines = 0

    # ---- helpers -----------------------------------------------------------

    def _flush_newlines(self):
        if self._pending_newlines:
            self._out.append('\n' * self._pending_newlines)
            self._pending_newlines = 0

    def _nl(self, n=1):
        self._pending_newlines = max(self._pending_newlines, n)

    def _write(self, text):
        if not text:
            return
        self._flush_newlines()
        self._out.append(text)

    def _attrs(self, attrs):
        return dict(attrs)

    # ---- tag handlers ------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = self._attrs(attrs)
        self._tag_stack.append((tag, attrs_dict))

        if self._skip_depth or tag in self.SKIP_TAGS:
            self._skip_depth += 1
            return

        if self._in_table and tag not in ('table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td'):
            if not self._in_pre:
                return  # inside a cell; data handled in handle_data

        if tag in self.HEADING_TAGS:
            self._nl(2)
            self._write(self.HEADING_TAGS[tag] + ' ')

        elif tag in self.BLOCK_TAGS:
            self._nl(2)

        elif tag == 'br':
            self._write('  \n')

        elif tag == 'hr':
            self._nl(2)
            self._write('---')
            self._nl(2)

        elif tag in ('strong', 'b'):
            self._write('**')

        elif tag in ('em', 'i'):
            self._write('*')

        elif tag == 'code':
            if not self._in_pre:
                self._write('`')
                self._in_code = True

        elif tag == 'pre':
            self._nl(2)
            self._write('```')
            self._nl(1)
            self._in_pre = True

        elif tag in ('ul', 'ol'):
            self._list_stack.append((tag, 0))
            self._nl(1)

        elif tag == 'li':
            if self._list_stack:
                kind, counter = self._list_stack[-1]
                indent = '  ' * (len(self._list_stack) - 1)
                if kind == 'ul':
                    prefix = f'{indent}- '
                else:
                    counter += 1
                    self._list_stack[-1] = (kind, counter)
                    prefix = f'{indent}{counter}. '
                self._nl(1)
                self._write(prefix)

        elif tag == 'a':
            href = attrs_dict.get('href', '')
            # We'll close the link in end tag; for now just write [
            self._write('[')

        elif tag == 'table':
            self._in_table = True
            self._table_rows = []
            self._nl(2)

        elif tag in ('thead', 'tbody', 'tfoot'):
            pass

        elif tag == 'tr':
            self._current_row = []

        elif tag in ('th', 'td'):
            self._current_cell = []

        elif tag == 'img':
            alt = attrs_dict.get('alt', 'image')
            src = attrs_dict.get('src', '')
            self._write(f'![{alt}]({src})')

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._tag_stack and self._tag_stack[-1][0] == tag:
            _, saved_attrs = self._tag_stack.pop()
        else:
            saved_attrs = {}

        if self._skip_depth:
            self._skip_depth -= 1
            return
        if tag in self.SKIP_TAGS:
            return

        if tag in self.HEADING_TAGS:
            self._nl(2)

        elif tag in self.BLOCK_TAGS:
            self._nl(2)

        elif tag in ('strong', 'b'):
            self._write('**')

        elif tag in ('em', 'i'):
            self._write('*')

        elif tag == 'code':
            if self._in_code:
                self._write('`')
                self._in_code = False

        elif tag == 'pre':
            self._nl(1)
            self._write('```')
            self._nl(2)
            self._in_pre = False

        elif tag in ('ul', 'ol'):
            if self._list_stack:
                self._list_stack.pop()
            self._nl(2)

        elif tag == 'li':
            self._nl(1)

        elif tag == 'a':
            href = saved_attrs.get('href', '')
            if href.startswith('/'):
                href = self.base_url + href
            self._write(f']({href})')

        elif tag in ('th', 'td'):
            cell_text = ''.join(self._current_cell).strip().replace('\n', ' ')
            self._current_row.append(cell_text)
            self._current_cell = []

        elif tag == 'tr':
            if self._current_row:
                self._table_rows.append(self._current_row)

        elif tag == 'table':
            self._render_table()
            self._in_table = False
            self._table_rows = []
            self._nl(2)

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data  # convert_charrefs=True already decoded entities

        if self._in_table and not self._in_pre:
            self._current_cell.append(text)
            return

        if self._in_pre:
            self._write(text)
            return

        # Collapse whitespace outside pre/code
        text = re.sub(r'[ \t]+', ' ', text)
        if text.strip():
            self._write(text)
        elif text == ' ':
            self._write(' ')

    def _render_table(self):
        if not self._table_rows:
            return
        # First row = header if it came from <th>; otherwise treat first row as header anyway
        header = self._table_rows[0]
        rows = self._table_rows[1:]
        cols = max(len(r) for r in self._table_rows)

        def pad(row):
            return row + [''] * (cols - len(row))

        self._write('| ' + ' | '.join(pad(header)) + ' |\n')
        self._write('|' + '|'.join(['---'] * cols) + '|\n')
        for row in rows:
            self._write('| ' + ' | '.join(pad(row)) + ' |\n')

    def get_markdown(self):
        self._flush_newlines()
        md = ''.join(self._out)
        # Remove empty bold/italic markers (e.g. **** or ** **)
        md = re.sub(r'\*\*\s*\*\*', '', md)
        md = re.sub(r'\*\s*\*', '', md)
        md = re.sub(r'``', '', md)
        # Normalise blank lines (max 2 consecutive)
        md = re.sub(r'\n{3,}', '\n\n', md)
        return md.strip()


def html_to_markdown(raw_html, base_url=''):
    # Strip Confluence XML namespace tags that confuse the HTML parser
    raw_html = re.sub(r'<ac:[^>]*/>', '', raw_html)
    raw_html = re.sub(r'</?ac:[^>]*>', '', raw_html)
    raw_html = re.sub(r'<ri:[^>]*/>', '', raw_html)
    raw_html = re.sub(r'</?ri:[^>]*>', '', raw_html)
    parser = _HTMLToMD(base_url=base_url)
    parser.feed(raw_html)
    return parser.get_markdown()


# ---------------------------------------------------------------------------
# Confluence REST API fetch
# ---------------------------------------------------------------------------

def _get(base_url, token, path):
    """Internal GET helper — returns parsed JSON or raises."""
    req = urllib.request.Request(
        f'{base_url}{path}',
        headers={'Authorization': f'Bearer {token}'},
    )
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read().decode('utf-8'))


def fetch_children(base_url, token, page_id, limit=50):
    """Return a list of {id, title} for all direct child pages."""
    children = []
    start = 0
    while True:
        try:
            data = _get(base_url, token,
                        f'/rest/api/content/{page_id}/child/page?limit={limit}&start={start}')
        except Exception:
            break
        results = data.get('results', [])
        for r in results:
            children.append({'id': r['id'], 'title': r.get('title', '')})
        if len(results) < limit:
            break
        start += limit
    return children


def fetch_page(base_url, token, page_id):
    try:
        data = _get(base_url, token,
                    f'/rest/api/content/{page_id}?expand=body.storage,ancestors,space')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return {'error': f'HTTP {e.code}: {body[:300]}'}
    except Exception as e:
        return {'error': str(e)}

    title     = data.get('title', '')
    html_body = data.get('body', {}).get('storage', {}).get('value', '')
    space_key = data.get('space', {}).get('key', '')
    ancestors = [a.get('title', '') for a in data.get('ancestors', [])]
    page_url  = f'{base_url}/pages/viewpage.action?pageId={page_id}'
    markdown  = html_to_markdown(html_body, base_url=base_url)

    result = {
        'page_id':   page_id,
        'title':     title,
        'space':     space_key,
        'ancestors': ancestors,
        'url':       page_url,
        'markdown':  markdown,
        'is_index':  False,
        'children':  [],
    }

    # Index page: body is empty — fetch child pages so the caller can decide.
    if not markdown.strip():
        children = fetch_children(base_url, token, page_id)
        if children:
            result['is_index'] = True
            result['children'] = children

    return result


def fetch_pages_combined(base_url, token, page_ids):
    """Fetch multiple pages and return a list of individual results."""
    results = []
    for pid in page_ids:
        r = fetch_page(base_url, token, pid)
        if 'error' not in r:
            results.append(r)
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--token', required=True)
    parser.add_argument('--page-ids', nargs='+',
                        help='One or more numeric page IDs to fetch and combine')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--url', help='Full Confluence page URL (single page)')
    group.add_argument('--page-id', help='Numeric Confluence page ID (single page)')
    args = parser.parse_args()

    if args.page_ids:
        result = fetch_pages_combined(args.base_url, args.token, args.page_ids)
    else:
        page_id = args.page_id or (extract_page_id(args.url) if args.url else None)
        if not page_id:
            print(json.dumps({'error': 'Provide --url, --page-id, or --page-ids'}))
            sys.exit(1)
        result = fetch_page(args.base_url, args.token, page_id)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()