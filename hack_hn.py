
import re

import requests
import bs4

from urllib.parse import urljoin

from django.core.validators import ValidationError, URLValidator

hn_url = 'https://news.ycombinator.com'

def _first_int_or_none(text):
    try:
        return int(re.search('\d+', text).group(0))
    except (AttributeError, TypeError, OverflowError, ValueError):
        ...

def _points(text):
    return _first_int_or_none(text)

def _comments(text):
    return _first_int_or_none(text)

def _date(text):
    return text

def _title(text):
    return text

def _relative_url(text):
    try:
        path = re.match('^item\?id\=\d+$', text).group(0)
        url = urljoin(hn_url, path)
        URLValidator()(url)
    except (AttributeError, ValidationError):
        ...
    else:
        return url

def _url(text):
    try:
        text = text.strip()
        URLValidator()(text)
    except ValidationError:
        return _relative_url(text)
    except AttributeError:
        ...
    else:
        return text

def hn_data(html):
    for tag in bs4.BeautifulSoup(html).find_all(class_='subtext'):

        spans = tag.find_all('span')
        as_ = tag.find_all('a')

        try:
            comments = as_[-1].text
        except IndexError:
            comments = None

        try:
            date = as_[0].next_sibling
        except IndexError:
            date = None

        try:
            points = spans[0].text
        except IndexError:
            points = None

        title_tag = tag.parent.previous_sibling.find_all(class_='title')[-1]
        url = title_tag.a.attrs.get('href')
        title = title_tag.a.text

        data = {'title': _title(title),
                'url': _url(url),
                'points': _points(points),
                'comments': _comments(comments),
                'date': _date(date)}

        yield {key: value for key, value
                   in data.items() if value is not None}

def _get_html(path):
    return requests.get(urljoin(hn_url, path), headers={'User-Agent': 'foo'}).content.decode()

def stats(path):
    import statistics

    html = _get_html(path)

    data = list(hn_data(html))

    def _ratios():
        for article in data:
            points = article.get('points', 0.0)
            comments = article.get('comments', 0.0)
            try:
                yield points / comments
            except ZeroDivisionError:
                yield 0.0

    def _rundown(name, data, indent=' ' * 4):
        double = indent * 2

        print(indent, '{}:'.format(name))
        print(double, 'avg    :', statistics.mean(data))
        print(double, 'stdev  :', statistics.stdev(data))
        print(double, 'median :', statistics.median(data))
        print()
        print(double, 'min      :', min(data))
        print(double, 'max      :', max(data))
        print(double, 'min of >0:', min(value for value in data if value > 0))

    print(path)
    print()
    print('    articles:', len(data))
    print()

    _rundown('points', [article.get('points', 0.0) for article in data])
    print()
    _rundown('comments', [article.get('comments', 0.0) for article in data])
    print()
    _rundown('ratio', list(_ratios()))

def rundown(paths):
    for path in paths:
        stats(path)
        print()

def plot(paths):
    import numpy
    import matplotlib.pyplot as plt

    def lines():
        for path in paths:
            html = _get_html(path)
            line = [(article.get('points', 0.0), article.get('comments', 0.0)) for article in hn_data(html)]
            yield line

    plt.xlabel('points')
    plt.ylabel('comments')

    colors = ['red', 'green', 'yellow', 'orange', 'blue']

    for i, (path, line) in enumerate(zip(paths, lines())):
        xs, ys = zip(*line)

        plt.scatter(xs, ys, color=colors[i % len(paths) - 1], label=path)

    plt.legend()
    plt.show()

if __name__ == '__main__':
    paths = ['/news', '/news?p=2', '/newest', '/show', '/shownew']
    paths = ['/news', '/newest', '/show']
    #rundown(paths)
    plot(paths)

