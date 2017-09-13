from __future__ import absolute_import

import responses

from exam import fixture
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from sentry.exceptions import PluginError
from sentry.testutils import PluginTestCase
from sentry.utils import json
from social_auth.models import UserSocialAuth

from sentry_plugins.vsts.plugin import VstsPlugin


class VstsPluginTest(PluginTestCase):
    @fixture
    def plugin(self):
        return VstsPlugin()

    @fixture
    def request(self):
        return RequestFactory()

    def test_conf_key(self):
        assert self.plugin.conf_key == 'vsts'

    def test_entry_point(self):
        self.assertAppInstalled('vsts', 'sentry_plugins.vsts')
        self.assertPluginInstalled('vsts', self.plugin)

    def test_get_issue_label(self):
        group = self.create_group(message='Hello world', culprit='foo.bar')
        assert self.plugin.get_issue_label(group, 1) == 'Bug 1'

    def test_get_issue_url(self):
        self.plugin.set_option('account', 'getsentry', self.project)
        self.plugin.set_option('project', 'sentry', self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')
        assert self.plugin.get_issue_url(
            group, 1) == 'https://getsentry.visualstudio.com/sentry/_workitems?id=1'

    def test_is_configured(self):
        assert self.plugin.is_configured(None, self.project) is False
        self.plugin.set_option('account', 'getsentry', self.project)
        self.plugin.set_option('project', 'sentry', self.project)
        assert self.plugin.is_configured(None, self.project) is True

    @responses.activate
    def test_create_issue(self):
        responses.add(
            responses.PATCH,
            'https://getsentry.visualstudio.com/sentry/_apis/wit/workitems/$Bug?api-version=3.0',
            body='{"id": 1}'
        )

        self.plugin.set_option('account', 'getsentry', self.project)
        self.plugin.set_option('project', 'sentry', self.project)
        group = self.create_group(message='Hello world', culprit='foo.bar')

        request = self.request.get('/')
        request.user = AnonymousUser()
        form_data = {
            'title': 'Hello',
            'description': 'Fix this.',
        }
        with self.assertRaises(PluginError):
            self.plugin.create_issue(request, group, form_data)

        request.user = self.user
        self.login_as(self.user)
        UserSocialAuth.objects.create(
            user=self.user,
            provider=self.plugin.auth_provider,
            uid='a89e7204-9ca0-4680-ba7a-cfcf6b3c7445',
            extra_data={
                'access_token': 'foo',
                'refresh_token': 'bar',
            }
        )

        assert self.plugin.create_issue(request, group, form_data) == 1
        request = responses.calls[-1].request
        payload = json.loads(request.body)
        assert payload == [
            {
                'op': 'add',
                'path': '/fields/System.Title',
                'value': 'Hello',
            },
            {
                'op': 'add',
                'path': '/fields/System.Description',
                'value': 'Fix this.',
            },
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "Hyperlink",
                    "url": 'http://testserver/baz/bar/issues/1/',
                }
            }
        ]
