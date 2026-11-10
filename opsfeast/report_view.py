"""Read-only, bounded report artifacts over the existing result/hash resolver."""
import hashlib
import html
from html.parser import HTMLParser
from pathlib import Path

from . import ConfigError

VERSION = '0.1.0'
MAX_BYTES = 16 * 1024 * 1024
PREVIEW_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"


class ArtifactError(ConfigError):
    """Fixed public artifact reason, without server paths or arbitrary output."""


class StaticHTML(HTMLParser):
    """Readable static report markup, with no scripts, navigation or remote URLs.

    CSP and the caller's opaque-origin sandbox are independent layers. Original
    bytes remain available only as an explicit attachment download.
    """
    tags = set('html head body title style h1 h2 h3 h4 h5 h6 p div section article header footer main nav aside span pre code blockquote strong em b i u s small sub sup ul ol li dl dt dd table caption colgroup col thead tbody tfoot tr th td a br hr img details summary figure figcaption svg g path rect circle ellipse line polyline polygon text tspan defs lineargradient radialgradient stop clippath'.split())
    attributes = set('class id title style role aria-label colspan rowspan span width height alt viewbox xmlns d x y x1 x2 y1 y2 cx cy r rx ry points fill stroke stroke-width transform opacity offset stop-color stop-opacity text-anchor font-size preserveaspectratio'.split())
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []; self.suppressed = False; self.in_style = False

    def handle_starttag(self, tag, attrs):
        if tag == 'script': self.suppressed = True
        if self.suppressed or tag not in self.tags: return
        safe = []
        for key, value in attrs:
            if value is None: continue
            if key in self.attributes or (tag == 'img' and key == 'src' and
                    value.lower().startswith(('data:image/png;base64,', 'data:image/jpeg;base64,', 'data:image/gif;base64,', 'data:image/webp;base64,'))):
                safe.append(' ' + key + '="' + html.escape(value, quote=True) + '"')
        self.output.append('<' + tag + ''.join(safe) + '>')
        if tag == 'style': self.in_style = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == 'script': self.suppressed = False; return
        if self.suppressed or tag not in self.tags: return
        if tag == 'style': self.in_style = False
        self.output.append('</' + tag + '>')

    def handle_data(self, data):
        if not self.suppressed:
            self.output.append(data if self.in_style else html.escape(data))


def list_reports(profile, *, offset=0, limit=50):
    from recipe_reports import results
    data = results(profile.root, kind='report')
    rows = [{key: row.get(key) for key in ('result_id', 'recipe_reference', 'recipe_version', 'status', 'reason_code', 'started_at', 'completed_at')}
            for row in data['results']]
    return {'schema_version': VERSION, 'profile': profile.name, 'status': data['status'],
            'items': rows[offset:offset+limit], 'total': len(rows), 'invalid_result_count': len(data['errors']),
            'next_offset': offset+limit if len(rows)>offset+limit else None}


def show_report(profile, identifier):
    from recipe_reports import show_result, result_path
    try:
        data = show_result(profile.root, identifier, kind='report')
        result_id = result_path(profile.root, identifier).relative_to(profile.root).as_posix()
        artifacts = [{key: a[key] for key in ('path','title','media_type','size_bytes','sha256')} for a in data.get('artifacts', [])]
    except (ConfigError, ValueError, TypeError, KeyError, OSError):
        raise ArtifactError('report_unavailable_or_invalid') from None
    return {'schema_version': VERSION, 'profile': profile.name, 'result_id': result_id,
            'status': data['status'], 'reason_code': data.get('reason_code'),
            'recipe_reference': data['recipe'].get('reference'),
            'started_at': data.get('started_at'), 'completed_at': data.get('completed_at'),
            'artifacts': artifacts, 'artifact_bytes_limit': MAX_BYTES}


def read_artifact(profile, identifier, name):
    from recipe_reports import show_artifact
    try:
        info = show_artifact(profile.root, identifier, name, max_bytes=MAX_BYTES)
        path = Path(info['path'])
        # Recheck the exact bytes served, not only the earlier filesystem digest.
        with path.open('rb') as stream: content = stream.read(MAX_BYTES+1)
        if len(content)>MAX_BYTES or len(content)!=info['size_bytes'] or hashlib.sha256(content).hexdigest()!=info['sha256']:
            raise ConfigError('artifact changed during read')
    except (ConfigError, ValueError, TypeError, KeyError, OSError):
        raise ArtifactError('artifact_unavailable_changed_or_too_large') from None
    return {key: info[key] for key in ('title','media_type','size_bytes','sha256','relative_path')}, content


def static_html(content):
    try:
        parser = StaticHTML(); parser.feed(content.decode('utf-8')); parser.close()
    except (ValueError, UnicodeError, RecursionError):
        raise ArtifactError('artifact_is_not_readable_utf8') from None
    return '<!doctype html><meta charset="utf-8">' + ''.join(parser.output)
