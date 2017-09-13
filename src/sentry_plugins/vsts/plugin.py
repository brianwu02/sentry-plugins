
""" A plugin to incorporate work-item creation in VSTS
easily out of issues detected from Sentry.io """

from __future__ import absolute_import

from six.moves.urllib.parse import quote, urlencode

from sentry.exceptions import PluginError
from sentry.utils.http import absolute_uri

from sentry.plugins.bases.issue2 import IssuePlugin2
from sentry_plugins.base import CorePluginMixin
from sentry_plugins.constants import ERR_UNAUTHORIZED

from .client import VstsClient


class VstsPlugin(CorePluginMixin, IssuePlugin2):
    allowed_actions = ['create', 'unlink']

    description = 'Integrate Visual Studio Team Services work items by linking a project.'
    slug = 'vsts'
    title = 'Visual Studio'
    conf_key = slug
    auth_provider = 'visualstudio'

    def get_client(self, user):
        auth = self.get_auth(user=user)
        if auth is None:
            raise PluginError(ERR_UNAUTHORIZED)
        return VstsClient(auth=auth)

    def get_configure_plugin_fields(self, request, project, **kwargs):
        # TODO(dcramer): Both Account and Project can query the API an access
        # token, and could likely be moved to the 'Create Issue' form
        return [
            {
                'name': 'account',
                'label': 'Account Name',
                'type': 'text',
                'placeholder': 'VSTS account name',
                'required': True,
                'help': 'Enter the account name of your VSTS instance. This will be the \
                same name appearing in your VSTS url: i.e. [name].visualstudio.com'
            },
            {
                'name': 'project',
                'label': 'Project Name',
                'type': 'text',
                'placeholder': 'VSTS project name',
                'required': True,
                'help': 'Enter the Visual Studio Team Services project name that you wish \
                new work items to be added to when they are created from Sentry. This must \
                be a valid project name within the VSTS account specified above.'
            },
        ]

    def is_configured(self, request, project, **kwargs):
        for o in ('account', 'project'):
            if not bool(self.get_option(o, project)):
                return False
        return True

    def get_issue_label(self, group, issue_id, **kwargs):
        return 'Bug %s' % issue_id

    def get_issue_url(self, group, issue_id, **kwargs):
        """
        Given an issue_id (string) return an absolute URL to the issue's
        details page.
        """
        account = self.get_option('account', group.project)
        project = quote(self.get_option('project', group.project))
        if not (account and project):
            return
        queryparams = urlencode({'id': issue_id})
        template = "https://{0}.visualstudio.com/{1}/_workitems?{2}"
        return template.format(account, project, queryparams)

    def create_issue(self, request, group, form_data, **kwargs):
        """
        Creates the issue on the remote service and returns an issue ID.
        """
        account = self.get_option('account', group.project)
        project = self.get_option('project', group.project)

        client = self.get_client(request.user)

        title = form_data['title']
        description = form_data['description']
        link = absolute_uri(group.get_absolute_url())
        created_item = client.create_work_item(account, project, title, description, link)
        return created_item['id']

    def get_group_description(self, request, group, event):
        return self.get_group_body(request, group, event)
