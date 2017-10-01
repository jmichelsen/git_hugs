# filename: git_ci.py
""" A git webhook handler api """
import ipaddress
import json
import re
import subprocess

import hug
import requests

from constants import GITHUB_EVENT_HEADER, MESSAGES


class PullPostHandler(object):
    def __init__(self, request, response, body):
        self.request = request
        self.response = response
        self.body = body

        try:
            with open('repos.json', 'r') as repos_file:
                self.repos = json.loads(repos_file.read())
        except (IOError, Exception):
            self.repos = dict()

    def process_request(self):
        """ Gets and fires the request handler """
        event_handler = getattr(self, '_{}_event'.format(
            self.request.headers.get(GITHUB_EVENT_HEADER)), '_invalid_event')
        return event_handler()

    def _push_event(self):
        """ Takes a specified action for push events """
        meta = {
            'name': self.body['repository']['name'],
            'owner': self.body['repository']['owner']['name'],
        }

        try:
            match = re.match(r'refs/heads/(?P<branch>.*)', self.body['ref'])
            meta['branch'] = match.groupdict()['branch']
        except KeyError:
            self.response.status = hug.status_codes.HTTP_400
            return MESSAGES['no_match']

        try:
            repo = self.repos['{owner}/{name}/branch:{branch}'.format(**meta)]
        except KeyError:
            repo = self.repos['{owner}/{name}'.format(**meta)]

        try:
            [subprocess.Popen(action, cwd=repo['path'])
             for action in repo['action']]
        except Exception:
            self.response.status = hug.status_codes.HTTP_500
            return MESSAGES['exception']
        return MESSAGES['push']

    @staticmethod
    def _ping_event():
        """ Returns a nice message for pings """
        return MESSAGES['ping']

    def _invalid_event(self):
        """ Returns a 400 for any event that isn't ping or push """
        self.response.status = hug.status_codes.HTTP_400
        return MESSAGES['wrong_event_type']


@hug.post('/', output=hug.output_format.json)
def pull(request, response, body):
    """
    When a github repo webhook fires to this endpoint, the endpoint validates
    the request came from github, validates the incoming data, and fires the
    actions specified in repos.json
    """
    hook_blocks = requests.get('https://api.github.com/meta').json()['hooks']
    request_ip = ipaddress.ip_address(request.headers['X-FORWARDED-FOR'])
    is_allowed = [(ipaddress.ip_address(request_ip) in netblock)
                  for netblock in
                  [ipaddress.ip_network(block) for block in hook_blocks]]
    if True not in is_allowed:
        response.status = hug.status_codes.HTTP_403
        return MESSAGES['403']
    return PullPostHandler(request, response, body).process_request()
