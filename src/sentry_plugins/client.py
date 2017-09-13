from __future__ import absolute_import

import logging
import json
import requests

from BeautifulSoup import BeautifulStoneSoup
from cached_property import cached_property
from django.utils.datastructures import SortedDict
from requests.exceptions import RequestException

from sentry.http import build_session

from .exceptions import ApiError, ApiUnauthorized


class BaseApiResponse(object):
    def __init__(self, headers=None, status_code=None):
        self.headers = headers
        self.status_code = status_code

    @cached_property
    def rel(self):
        if not self.headers:
            return {}
        link_header = self.headers.get('Link')
        if not link_header:
            return {}
        return {item['rel']: item['url'] for item in requests.utils.parse_header_links(link_header)}

    @classmethod
    def from_response(self, response):
        if response.text[:5] == '<?xml':
            return XmlApiResponse(response.text, response.headers, response.status_code)
        try:
            data = json.loads(response.text, object_pairs_hook=SortedDict)
        except (TypeError, ValueError):
            return TextApiResponse(response.text, response.headers, response.status_code)
        if isinstance(data, dict):
            return MappingApiResponse(data, response.headers, response.status_code)
        elif isinstance(data, (list, tuple)):
            return SequenceApiResponse(data, response.headers, response.status_code)
        else:
            raise NotImplementedError


class TextApiResponse(BaseApiResponse):
    def __init__(self, text, *args, **kwargs):
        self.text = text
        super(TextApiResponse, self).__init__(text, *args, **kwargs)


class XmlApiResponse(BaseApiResponse):
    def __init__(self, text, *args, **kwargs):
        self.xml = BeautifulStoneSoup(text)
        super(XmlApiResponse, self).__init__(text, *args, **kwargs)


class MappingApiResponse(dict, BaseApiResponse):
    def __init__(self, data, *args, **kwargs):
        dict.__init__(self, data)
        BaseApiResponse.__init__(self, *args, **kwargs)

    @property
    def json(self):
        return self


class SequenceApiResponse(list, BaseApiResponse):
    def __init__(self, data, *args, **kwargs):
        list.__init__(self, data)
        BaseApiResponse.__init__(self, *args, **kwargs)

    @property
    def json(self):
        return self


class ApiClient(object):
    base_url = None
    logger = logging.getLogger('sentry.plugins')

    def _request(self, method, path, headers=None, data=None, params=None):
        if path.startswith('/'):
            if not self.base_url:
                raise ValueError('Invalid URL: {}'.format(path))
            full_url = '{}{}'.format(self.base_url, path)
        else:
            full_url = path
        session = build_session()
        try:
            resp = getattr(session, method.lower())(
                url=full_url,
                headers=headers,
                json=data,
                params=params,
                allow_redirects=True,
            )
            resp.raise_for_status()
        except RequestException as e:
            resp = e.response
            if not resp:
                self.logger.exception('request.error', extra={
                    'url': full_url,
                })
                raise ApiError('Internal Error')
            if resp.status_code == 401:
                raise ApiUnauthorized.from_response(resp)
            raise ApiError.from_response(resp)

        if resp.status_code == 204:
            return {}

        return BaseApiResponse.from_response(resp)

    # subclasses should override ``request``
    def request(self, *args, **kwargs):
        return self._request(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return self.request('DELETE', *args, **kwargs)

    def get(self, *args, **kwargs):
        return self.request('GET', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self.request('PATCH', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request('POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self.request('PUT', *args, **kwargs)


class AuthApiClient(ApiClient):
    auth = None

    def __init__(self, auth=None):
        self.auth = auth

    def has_auth(self):
        return self.auth and 'access_token' in self.auth.tokens

    def _request(self, method, path, headers=None, data=None, params=None):
        if headers is None:
            headers = {}

        if 'Authorization' not in headers and self.has_auth():
            token = self.auth.tokens['access_token']
            headers['Authorization'] = 'Bearer {}'.format(token)

        try:
            return ApiClient._request(self, method, path, headers=headers, data=data, params=params)
        except ApiUnauthorized:
            if not self.auth:
                raise

        # refresh token
        self.auth.refresh_token()
        token = self.auth.tokens['access_token']
        headers['Authorization'] = 'Bearer %s' % token
        return ApiClient._request(self, method, path, headers=headers, data=data, params=params)
