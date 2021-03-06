
import collections
import re

import requests
import bs4

from urllib.parse import urljoin

from django.core.validators import ValidationError, URLValidator

HN_URL = 'https://news.ycombinator.com'

USER_AGENT = 'certainly-not-python'

class _Schema:
    keys = ['title', 'url', 'date', 'points', 'comments']

    def as_dict(self):
        items = ((key, getattr(self, key, lambda: None)()) for key in self.keys)
        return {key: value for key, value in items if value is not None}

class Scraped(_Schema):
    def __init__(self, tag):
        self._tag = tag
        self._anchors = self._tag.find_all('a')
        self._title_tag = self._tag.parent.previous_sibling.find_all(class_='title')[-1]

    def points(self):
        try:
            return self._tag.find_all('span')[0].text
        except IndexError:
            ...

    def comments(self):
        try:
            return self._anchors[-1].text
        except IndexError:
            ...

    def date(self):
        try:
            return self._anchors[0].next_sibling
        except IndexError:
            ...

    def title(self):
        return self._title_tag.a.text

    def url(self):
        return self._title_tag.a.attrs.get('href')

class Validated(_Schema):
    def __init__(self, data):
        self.data = data

    def points(self):
        return self._first_int_or_none(self.data.get('points'))

    def comments(self):
        return self._first_int_or_none(self.data.get('comments'))

    def date(self):
        try:
            return ''.join(char for char in self.data.get('date') if char.isalnum() or char.isspace()).strip()
        except TypeError:
            ...

    def title(self):
        return self.data.get('title')

    def url(self):
        try:
            url = self.data.get('url').strip()
            URLValidator()(url)
        except ValidationError:
            return self._relative_url(url)
        except AttributeError:
            ...
        else:
            return url

    def _first_int_or_none(self, text):
        try:
            return int(re.search('\d+', text).group(0))
        except (AttributeError, TypeError, OverflowError, ValueError):
            ...

    def _relative_url(self, url):
        try:
            path = re.match('^item\?id\=\d+$', url).group(0)
            absolute_url = urljoin(HN_URL, path)
            URLValidator()(absolute_url)
        except (AttributeError, ValidationError):
            ...
        else:
            return absolute_url

def hn_data(html):
    for article_tag in bs4.BeautifulSoup(html).find_all(class_='subtext'):
        scraped_data = Scraped(article_tag).as_dict()
        valid_data = Validated(scraped_data).as_dict()
        yield valid_data

def get_html(path='/news'):
    return requests.get(urljoin(HN_URL, path), headers={'User-Agent': USER_AGENT}).text

def stats(summary, indent=' ' * 4):
    def rundown(name, data):
        double = indent * 2

        print(indent, '{}:'.format(name))
        print(double, 'avg    :', statistics.mean(data))
        print(double, 'stdev  :', statistics.stdev(data))
        print(double, 'median :', statistics.median(data))
        print()
        print(double, 'min      :', min(data))
        print(double, 'max      :', max(data))
        print(double, 'min of >0:', min((value for value in data if value > 0), default=float('nan')))

    for path, data in summary.items():
        data = list(data)

        print(path)
        print()
        print(indent, 'articles:', len(data))
        print()
        rundown('points', [article.get('points', 0.0) for article in data])
        print()
        rundown('comments', [article.get('comments', 0.0) for article in data])
        print()

def plot(summary):
    colors = 'rgbcmyk'

    for i, (path, data) in enumerate(summary.items()):
        data = list(data)
        xs = [article.get('points', 0.0) for article in data]
        ys = [article.get('comments', 0.0) for article in data]
        plt.scatter(xs, ys, label=path, color=colors[i % len(colors)])

    plt.xlabel('points')
    plt.ylabel('comments')
    plt.legend()
    plt.show()

def test():
    assert [] == list(hn_data(''))

    with open('test.html') as f:
        data = {'title'   : 'CUPS 2.0',
                'url'     : 'https://www.cups.org/documentation.php/doc-2.0/relnotes.html',
                'date'    : '2 hours ago',
                'comments': 11,
                'points'  : 68}

        assert [data] == list(hn_data(f.read()))

if __name__ == '__main__':
    test()

    paths = ['/shownew', '/show', '/newest', '/news?p=2', '/news']

    summary = collections.OrderedDict((path, hn_data(get_html(path))) for path in paths)

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        import statistics
        stats(summary)
    else:
        plot(summary)

