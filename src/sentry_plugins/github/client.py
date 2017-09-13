from __future__ import absolute_import

from django.conf import settings

from sentry_plugins.client import ApiClient


class GitHubClient(ApiClient):
    base_url = 'https://api.github.com'

    def __init__(self, url=None, token=None):
        if url is not None:
            self.base_url = url.rstrip('/')
        self.token = token

    def request(self, method, path, data=None, params=None):
        headers = {
            'Authorization': 'token %s' % self.token,
        }

        return self._request(method, path, headers=headers, data=data, params=params)

    def request_no_auth(self, method, path, data=None, params=None):
        if params is None:
            params = {}

        params.update(
            {
                'client_id': settings.GITHUB_APP_ID,
                'client_secret': settings.GITHUB_API_SECRET,
            }
        )

        return self._request(method, path, data=data, params=params)

    def get_repo(self, repo):
        return self.get('/repos/{}'.format(repo))

    def get_issue(self, repo, issue_id):
        return self.get('/repos/{}/issues/{}'.format(repo, issue_id))

    def create_issue(self, repo, data):
        return self.post(
            '/repos/{}/issues'.format(repo),
            data=data,
        )

    def create_comment(self, repo, issue_id, data):
        return self.post(
            '/repos/{}/issues/{}/comments'.format(
                repo,
                issue_id,
            ),
            data=data,
        )

    def list_assignees(self, repo):
        return self.get('/repos/{}/assignees?per_page=100'.format(repo))

    def search_issues(self, query):
        return self.get(
            '/search/issues',
            params={'q': query},
        )

    def create_hook(self, repo, data):
        return self.post(
            '/repos/{}/hooks'.format(
                repo,
            ),
            data=data,
        )

    def delete_hook(self, repo, id):
        return self.delete('/repos/{}/hooks/{}'.format(repo, id))

    def get_last_commits(self, repo, end_sha):
        # return api request that fetches last ~30 commits
        # see https://developer.github.com/v3/repos/commits/#list-commits-on-a-repository
        # using end_sha as parameter
        return self.get(
            '/repos/{}/commits'.format(
                repo,
            ),
            params={'sha': end_sha},
        )

    def compare_commits(self, repo, start_sha, end_sha):
        # see https://developer.github.com/v3/repos/commits/#compare-two-commits
        # where start sha is oldest and end is most recent
        return self.get('/repos/{}/compare/{}...{}'.format(
            repo,
            start_sha,
            end_sha,
        ))
