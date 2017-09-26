# filename: git_ci.py
""" A git webhook handler api """

import hug


@hug.get('/')
def pull():
    """ Accepts a hit from git webhooks and pulls the configured repo/branch """
    return "Happy {age} Birthday {name}!".format(**locals())
