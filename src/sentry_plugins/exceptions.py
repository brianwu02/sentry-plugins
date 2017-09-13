from __future__ import absolute_import

from BeautifulSoup import BeautifulStoneSoup
from collections import OrderedDict
from simplejson.decoder import JSONDecodeError
from sentry.utils import json


class ApiError(Exception):
    code = None
    json = None
    xml = None

    def __init__(self, text, code=None):
        if code is not None:
            self.code = code
        self.text = text
        self.xml = None
        # TODO(dcramer): pull in XML support from Jira
        if text:
            try:
                self.json = json.loads(text, object_pairs_hook=OrderedDict)
            except (JSONDecodeError, ValueError):
                if self.text[:5] == "<?xml":
                    # perhaps it's XML?
                    self.xml = BeautifulStoneSoup(self.text)
                # must be an awful code.
                self.json = None
        else:
            self.json = None
        super(ApiError, self).__init__(text[:128])

    @classmethod
    def from_response(cls, response):
        if response.status_code == 401:
            return ApiUnauthorized(response.text)
        return cls(response.text, response.status_code)


class ApiUnauthorized(ApiError):
    code = 401
