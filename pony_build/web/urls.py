base_url = None

named_rss_feed_url = '/rss2/%(feedname)s'
generic_rss_feed_root = '/rss2/_generic/%(package)s/'
package_url_template = 'p/%(package)s/'
per_result_url_template = 'p/%(package)s/%(result_key)s/'

def calculate_base_url(host, port, script_name=''):
    if not host.strip():
        host = 'localhost'
    url = 'http://%s:%s' % (host, port)
    if script_name:
        url += '/' + script_name.strip('/')

    return url

def set_base_url(url):
    global base_url
    base_url = url
