"""Bounded public-source collector. Never treats a news headline as a confirmed event."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 4_000_000

def now():
    return datetime.now(timezone.utc).isoformat()

def https(url):
    try:
        parsed = urlsplit(url)
        return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username
    except ValueError:
        return False

def fetch(url):
    if not https(url):
        raise ValueError('HTTPS required')
    req = Request(url, headers={'User-Agent': 'MotoAtlas/1.0 (public motorcycle news and event directory)', 'Accept': 'text/html,application/rss+xml,application/xml'})
    with urlopen(req, timeout=18) as response:
        if not https(response.url):
            raise ValueError('Unexpected redirect')
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError('Response too large')
        return content.decode('utf-8', errors='replace')

def clean(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', '', unescape(str(value or '')))).strip()[:500]

def news_from_xml(xml, language, category, feed_url, clock=None):
    clock = clock or datetime.now(timezone.utc)
    result = []
    root = ET.fromstring(xml)
    for item in root.findall('.//item')[:35]:
        title, url = clean(item.findtext('title')), item.findtext('link') or ''
        source = clean(item.findtext('source'))
        try:
            published = parsedate_to_datetime(item.findtext('pubDate'))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if not title or not source or not https(url) or published > clock + timedelta(hours=6) or published < clock - timedelta(days=180):
            continue
        suffix = ' - ' + source
        if title.endswith(suffix):
            title = title[:-len(suffix)]
        identifier = hashlib.sha256((title.lower() + source.lower()).encode()).hexdigest()[:18]
        result.append({'id': identifier, 'title': title, 'url': url, 'source': source, 'date': published.isoformat(), 'language': language, 'category': category, 'feed': feed_url})
    return result

class StructuredData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active, self.chunks, self.documents = False, [], []
    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type', '').lower() == 'application/ld+json':
            self.active, self.chunks = True, []
    def handle_data(self, data):
        if self.active:
            self.chunks.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            try:
                self.documents.append(json.loads(''.join(self.chunks)))
            except (ValueError, TypeError):
                pass
            self.active = False

def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)

def events_from_html(html, source):
    parser = StructuredData()
    parser.feed(html)
    result, seen = [], set()
    for doc in parser.documents:
        for obj in walk(doc):
            types = obj.get('@type', [])
            if isinstance(types, str):
                types = [types]
            if not any(t in ['Event', 'SportsEvent', 'Festival', 'ExhibitionEvent'] for t in types):
                continue
            start = str(obj.get('startDate', ''))[:10]
            end = str(obj.get('endDate') or start)[:10]
            try:
                if date.fromisoformat(end) < date.fromisoformat(start):
                    continue
            except ValueError:
                continue
            name = clean(obj.get('name'))
            url = urljoin(source['url'], str(obj.get('url') or source['url']))
            # Structured events may only link to the source organizer's own host.
            if not name or not https(url) or urlsplit(url).hostname != urlsplit(source['url']).hostname:
                continue
            key = (name, start, end)
            if key in seen:
                continue
            seen.add(key)
            location = obj.get('location') or {}
            place = clean(location.get('name')) if isinstance(location, dict) else clean(location)
            status = str(obj.get('eventStatus', ''))
            result.append({'id': 'auto-' + hashlib.sha256('|'.join(key).encode()).hexdigest()[:15], 'name': name, 'kind': source['kind'], 'country': source['country'], 'place': place, 'start': start, 'end': end, 'text': {'pt': 'Datas extraídas dos dados estruturados do organizador. Confira programação, acesso e alterações na fonte.', 'en': 'Dates extracted from organizer structured data. Check program, access and changes with the source.'}, 'url': url, 'automated': True, 'status': 'cancelled' if 'Cancelled' in status or 'Postponed' in status else 'scheduled', 'fetchedAt': now()})
    return result[:30]

QUERIES = [
    ('pt', 'general', 'motocicletas Honda Yamaha BMW Ducati Harley Davidson lançamento when:7d'),
    ('en', 'general', 'motorcycles motorcycle industry launch when:7d'),
    ('pt', 'racing', 'MotoGP Superbike motocross enduro rally motos when:7d'),
    ('en', 'racing', 'MotoGP superbike motocross enduro Dakar rally motorcycle when:7d'),
    ('pt', 'events', 'encontro motos festival motociclistas feira motos Brasil Portugal when:30d'),
    ('en', 'events', 'motorcycle rally show meet festival Europe Australia USA when:30d'),
    ('pt', 'community', 'Iron Butt HOG Ducati clube motociclistas viagem when:30d'),
    ('en', 'community', 'Iron Butt Ride 365 motorcycle owners club touring when:30d'),
    ('en', 'racing', 'site:fim-moto.com when:30d'),
    ('pt', 'events', 'Capital Moto Week Sertões motos quando encontro when:30d'),
    ('en', 'events', 'EICMA Motorcycle Live Sturgis Isle of Man TT when:30d'),
    ('en', 'community', 'Indian Riders Group Royal Enfield Vespa club when:30d'),
]

def main():
    catalog = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
    previous_path = ROOT / 'snapshot.json'
    try:
        previous = json.loads(previous_path.read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        previous = {'news': [], 'events': [], 'sources': []}
    jobs = []
    for language, category, query in QUERIES:
        query_params = {'q': query, 'hl': 'pt-BR' if language == 'pt' else 'en-US', 'gl': 'BR' if language == 'pt' else 'US', 'ceid': 'BR:pt-419' if language == 'pt' else 'US:en'}
        jobs.append({'name': 'Google News · ' + category + ' · ' + language, 'url': 'https://news.google.com/rss/search?' + urlencode(query_params), 'language': language, 'category': category})
    for country in catalog.get('countries', []):
        language = 'pt' if country['id'] in ['br', 'pt'] else 'en'
        query = (f'(motos OR motociclistas) (encontro OR rally OR festival) "{country[language]}" when:30d' if language == 'pt' else f'(motorcycle OR motorbike) (rally OR festival OR meetup OR show) "{country[language]}" when:30d')
        params = {'q': query, 'hl': 'pt-BR' if language == 'pt' else 'en-US', 'gl': 'BR' if language == 'pt' else 'US', 'ceid': 'BR:pt-419' if language == 'pt' else 'US:en'}
        jobs.append({'name': 'Event discovery · ' + country['en'], 'url': 'https://news.google.com/rss/search?' + urlencode(params), 'language': language, 'category': 'events', 'countryId': country['id']})
    # Include all manufacturer, association and program reference pages in source checks.
    references = catalog['sources'] + catalog['brands'] + catalog['clubs'] + catalog['programs'] + catalog['events']
    seen = set()
    for item in references:
        if item['url'] in seen:
            continue
        seen.add(item['url'])
        job = {'name': item['name'], 'url': item['url']}
        if 'kind' in item:
            job.update(kind=item['kind'], country=item['country'])
        jobs.append(job)
    old_sources = {s['url']: s for s in previous.get('sources', [])}
    def collect(job):
        checked = now()
        try:
            content = fetch(job['url'])
            news = news_from_xml(content, job['language'], job['category'], job['url']) if 'language' in job else []
            if 'countryId' in job:
                # Search scope is not evidence of the actual event location.
                for item in news:
                    item['countryQueries'] = [job['countryId']]
                news = [item for item in news if re.search(r'rally|rali|encontro|festival|show|meet|bike\s?week|moto\s?week|gathering|ride|passeio|exhibition|feira|race|corrida|grand prix|motogp|superbike|enduro|motocross|sertoes|sertões', item['title'], re.I)][:14]
            found = events_from_html(content, job) if 'kind' in job else []
            return {'name': job['name'], 'url': job['url'], 'ok': True, 'checkedAt': checked, 'lastSuccess': checked}, news, found
        except Exception as error:
            status = {'name': job['name'], 'url': job['url'], 'ok': False, 'checkedAt': checked, 'lastSuccess': old_sources.get(job['url'], {}).get('lastSuccess'), 'error': type(error).__name__}
            return status, [n for n in previous.get('news', []) if n.get('feed') == job['url']], [e for e in previous.get('events', []) if urlsplit(e['url']).hostname == urlsplit(job['url']).hostname] if 'kind' in job else []
    news, found_events, source_status = [], [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for status, feed_news, feed_events in pool.map(collect, jobs):
            source_status.append(status)
            news.extend(feed_news)
            found_events.extend(feed_events)
    limit_date = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
    unique_news = {}
    for item in news:
        if item['date'] < limit_date:
            continue
        if item['id'] in unique_news:
            queries = set(unique_news[item['id']].get('countryQueries', [])) | set(item.get('countryQueries', []))
            unique_news[item['id']]['countryQueries'] = sorted(queries)
        else:
            unique_news[item['id']] = item
    unique_events = {e['id']: e for e in found_events}
    snapshot = {'generatedAt': now(), 'news': sorted(unique_news.values(), key=lambda n: n['date'], reverse=True)[:650], 'events': list(unique_events.values()), 'sources': source_status}
    # Atomic replacement preserves the previous edition if serialization fails.
    temporary = ROOT / 'snapshot.tmp'
    temporary.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(previous_path)
    print(f"Collected {len(snapshot['news'])} headlines, {len(snapshot['events'])} structured events; {sum(s['ok'] for s in source_status)}/{len(source_status)} sources available.")

if __name__ == '__main__':
    main()
