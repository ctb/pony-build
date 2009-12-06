import feedparser
from datetime import datetime
from HTMLParser import HTMLParser

date_format = "%a, %d %b %Y %H:%M:%S GMT"

class _ExtractedInfo(HTMLParser):
    def __init__(self, content):
        HTMLParser.__init__(self)
        self.values = {}

        self.feed(content)
        self.close()
        
    def handle_data(self, data):
        k, v = data.split(': ', 1)
        self.values[k] = v

class PonyBuildRSSParser(object):
    def __init__(self):
        pass

    def consume_feed(self, content):
        # extract the most recent entry, return datetime, entry, k/v dict
        
        d = feedparser.parse(content)

        extract_date = lambda entry: datetime.strptime(entry.date, date_format)
        entries = sorted(d.entries, key=extract_date, reverse=True)

        latest_entry = entries[0]
        dt = datetime.strptime(latest_entry.date, date_format)
        p = _ExtractedInfo(latest_entry.summary_detail.value)

        return dt, latest_entry, p.values

if __name__ == '__main__':
    import sys

    p = PonyBuildRSSParser()
    dt, entry, values = p.consume_feed(open(sys.argv[1]))

    print dt
    print entry
    print values

    print entry.title_detail.value
    print entry.link
