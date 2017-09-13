from __future__ import absolute_import

from sentry_plugins.client import AuthApiClient


class VstsClient(AuthApiClient):
    api_version = '3.0'

    def request(self, method, path, data=None, params=None):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json-patch+json'
        }
        return self._request(method, path, headers=headers, data=data, params=params)

    def create_work_item(self, account, project, title, description, link):
        data = [
            {
                'op': 'add',
                'path': '/fields/System.Title',
                'value': title,
            },
            {
                'op': 'add',
                'path': '/fields/System.Description',
                'value': description
            },
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "Hyperlink",
                    "url": link,
                }
            }
        ]

        return self.patch(
            'https://{}.visualstudio.com/{}/_apis/{}/{}/${}?api-version={}'.format(
                account,
                project,
                'wit',
                'workitems',
                'Bug',
                self.api_version
            ),
            data=data,
        )
