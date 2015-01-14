# coding: utf-8
"""
    holocron.ext.generators.blog
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The package implements a Blog generator.

    :copyright: (c) 2014 by the Holocron Team, see AUTHORS for details.
    :license: 3-clause BSD, see LICENSE for details.
"""
import os
import datetime
from collections import defaultdict

import jinja2

from holocron.ext import abc
from holocron.content import Post
from holocron.utils import normalize_url, mkdir


class Blog(abc.Generator):
    """
    A blog generator extension.

    The class is a generator extension for Holocron that is designed to
    generate an index page - page listing posts available in the blog,
    a site feed - content distribution technology - in Atom format, and
    a number of tags pages - pages that appear when wants to see the posts
    under the certain tag.

    The Atom specification: http://www.ietf.org/rfc/rfc4287.txt

    See the :class:`~holocron.ext.Generator` class for interface details.
    """
    #: an atom template
    feed_template = jinja2.Template('\n'.join([
        '<?xml version="1.0" encoding="utf-8"?>',
        '  <feed xmlns="http://www.w3.org/2005/Atom" >',
        '    <title>{{ credentials.sitename }} Feed</title>',
        '    <updated>{{ credentials.date.isoformat() + "Z" }}</updated>',
        '    <id>{{ credentials.siteurl_alt }}</id>',
        '    ',
        '    <link href="{{ credentials.siteurl_self }}" rel="self" />',
        '    <link href="{{ credentials.siteurl_alt }}" rel="alternate" />',
        '    ',
        '    <generator>Holocron</generator>',

        '    {% for doc in documents %}',
        '    <entry>',
        '      <title>{{ doc.title }}</title>',
        '      <link href="{{ doc.abs_url }}" rel="alternate" />',
        '      <id>{{ doc.abs_url }}</id>',

        '      <published>{{ doc.created_local.isoformat() }}</published>',
        '      <updated>{{ doc.updated_local.isoformat() }}</updated>',

        '      <author>',
        '        <name>{{ doc.author }}</name>',
        '      </author>',

        '      <content type="html">',
        '        {{ doc.content | e }}',
        '      </content>',
        '    </entry>',
        '    {% endfor %}',
        '  </feed>',
    ]))

    # default template for index and tags pages
    index_pages_template = 'document-list.html'

    def __init__(self, *args, **kwargs):
        super(Blog, self).__init__(*args, **kwargs)

        # load template for rendering index and tag pages
        self._template = self.app.jinja_env.get_template(
            self.index_pages_template)

        # output path directory for feed, index page and tags directory
        self._output = self.app.conf['paths.output']

    def generate(self, documents):
        posts = self.extract_posts(documents)

        self.index(posts)
        self.tags(posts)
        self.feed(posts)

    def extract_posts(self, documents):
        """
        Picks out posts from the array of documents and returns them.
        The picking method is to analyze the path to the document and check
        whether it contains date or not. All the posts have a date in their
        path to source.

        :param documents: a list of Document objects, generated by Document
                          class from files in the content directory
        :returns:         a list of Convertible documents, which satisfy the
                          post pattern
        """
        posts = (doc for doc in documents if isinstance(doc, Post))
        posts = sorted(posts, key=lambda d: d.created, reverse=True)
        return posts

    def index(self, posts):
        """
        Generates an index page - page which lists all posts in a blog.
        """
        save_as = self.app.conf['generators.blog.index.save_as']
        save_as = os.path.join(self._output, save_as)

        with open(save_as, 'w', encoding='utf-8') as f:
            f.write(self._template.render(
                posts=posts,
                sitename=self.app.conf['sitename']))

    def tags(self, posts):
        """
        Generates tag pages.
        """
        # create a dictionnary of tags to corresponding posts
        tags = defaultdict(list)
        for post in posts:
            for tag in getattr(post, 'tags', []):
                tags[tag].append(post)

        for tag in tags:
            path = os.path.join(
                self._output,
                self.app.conf['generators.blog.tags.output'],
                tag)

            mkdir(path)

            save_as = self.app.conf['generators.blog.tags.save_as']
            save_as = os.path.join(path, save_as)

            with open(save_as, 'w', encoding='utf-8') as f:
                f.write(self._template.render(
                    posts=tags[tag],
                    sitename=self.app.conf['sitename']))

    def feed(self, posts):
        """
        The method is designed to generate a site feed - content distribution
        technology - in Atom format.

        The Atom specification: http://www.ietf.org/rfc/rfc4287.txt
        """
        posts_number = self.app.conf['generators.blog.feed.posts_number']
        save_as = self.app.conf['generators.blog.feed.save_as']

        credentials = {
            'siteurl_self': normalize_url(self.app.conf['siteurl']) + save_as,
            'siteurl_alt': normalize_url(self.app.conf['siteurl']),
            'sitename': self.app.conf['sitename'],
            'date': datetime.datetime.utcnow().replace(microsecond=0), }

        save_as = os.path.join(self._output, save_as)
        path = os.path.dirname(save_as)
        mkdir(path)

        with open(save_as, 'w', encoding='utf-8') as f:
            f.write(self.feed_template.render(
                documents=posts[:posts_number],
                credentials=credentials))
