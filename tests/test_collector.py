import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('collector', ROOT / 'scripts/collect.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

class CollectionTests(unittest.TestCase):
    def test_news_dates_and_source_attribution(self):
        xml = '<rss><channel><item><title>A new bike - Publisher</title><link>https://example.com/story</link><source>Publisher</source><pubDate>Fri, 02 Oct 2026 10:00:00 GMT</pubDate></item><item><title>Undated</title><link>https://example.com/</link></item></channel></rss>'
        items = collector.news_from_xml(xml, 'en', 'general', 'https://example.com/feed', datetime(2026, 10, 3, tzinfo=timezone.utc))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'A new bike')
        self.assertEqual(items[0]['source'], 'Publisher')

    def test_event_requires_real_dates_and_organizer_url(self):
        events = [{'@type': 'Event', 'name': 'Show', 'startDate': '2027-01-02', 'endDate': '2027-01-03'}, {'@type': 'Event', 'name': 'Invalid', 'startDate': '2027-02-30'}, {'@type': 'Event', 'name': 'Redirect', 'startDate': '2027-01-02', 'url': 'https://other.example/pay'}]
        html = '<script type="application/ld+json">' + json.dumps(events) + '</script>'
        source = {'url': 'https://organizer.example/', 'kind': 'show', 'country': {'pt': 'Brasil', 'en': 'Brazil'}}
        result = collector.events_from_html(html, source)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]['automated'])
        self.assertEqual(result[0]['url'], source['url'])

    def test_cancelled_event_remains_identified(self):
        html = '<script type="application/ld+json">{"@type":"SportsEvent","name":"Race","startDate":"2027-01-01","eventStatus":"https://schema.org/EventCancelled"}</script>'
        result = collector.events_from_html(html, {'url': 'https://example.com', 'kind': 'race', 'country': 'Test'})
        self.assertEqual(result[0]['status'], 'cancelled')

    def test_catalog_and_bilingual_content(self):
        data = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
        for section in ['brands', 'races', 'clubs', 'programs', 'events', 'sources']:
            self.assertTrue(data[section])
            for item in data[section]:
                self.assertTrue(collector.https(item['url']))
                self.assertTrue(item['text']['pt'])
                self.assertTrue(item['text']['en'])
        self.assertTrue(any(p['id'] == 'iba' for p in data['programs']))

if __name__ == '__main__':
    unittest.main()
