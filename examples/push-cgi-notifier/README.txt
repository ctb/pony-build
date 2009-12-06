This is a set of example code for dealing with PubSubHubbub (PuSH)
notifications and the RSS2 output from pony-build.

Files:

 - feedparser.py is Mark Pilgrim's universal feed parser, from
         http://feedparser.org/.  It's used to parse the RSS.

 - parse_pony_build_rss.py parses the pony-build RSS format and
         extracts some useful information from an RSS item.

 - push-subscriber.cgi is a CGI script that receives PuSH
         notifications and sends an e-mail 

 - rss-test-example.rss is a sample RSS file from pony-build.

 - test-post-rss.py mimics a PuSH notification server and POSTs
         rss-test-example.rss to your installed push-subscriber.cgi.

CTB 10/5/09
