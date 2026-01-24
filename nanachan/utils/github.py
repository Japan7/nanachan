"""GitHub GraphQL utilities for issue creation and Copilot assignment.

Follows the workflow from:
https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/create-a-pr#assigning-an-existing-issue
"""

import hashlib
import logging
import traceback
from typing import Any

from aiohttp import (
    ClientOSError,
    ClientResponseError,
    ClientSession,
    ServerDisconnectedError,
)
from discord.errors import IHateThe3SecondsTimeout
from discord.ext import commands
from valkey.exceptions import ConnectionError as ValkeyConnectionError

from nanachan.settings import GITHUB_REPO_SLUG, GITHUB_TOKEN
from nanachan.utils.misc import get_session

logger = logging.getLogger(__name__)

# Exceptions that should not be reported to GitHub
FILTERED_EXCEPTIONS = (
    ClientOSError,
    ClientResponseError,
    ConnectionRefusedError,
    ConnectionResetError,
    IHateThe3SecondsTimeout,
    ServerDisconnectedError,
    TimeoutError,
    ValkeyConnectionError,
)

GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'
cached_ids = None


def compute_error_signature(error_msg: str) -> str:
    """Compute a signature from the top frame of the traceback.

    Format: <exception_type>|<file>|<line>|<function>
    """
    lines = error_msg.strip().split('\n')
    # Find the last "File" line in the traceback
    file_line = None
    for line in reversed(lines):
        if line.strip().startswith('File "'):
            file_line = line.strip()
            break

    if not file_line:
        # Fallback to hashing the first line
        return hashlib.sha256(lines[0].encode()).hexdigest()[:16]

    # Extract exception type from the last line
    exception_type = lines[-1].split(':')[0].strip() if lines else 'UnknownError'

    # Parse file line: File "/path/to/file.py", line 123, in function_name
    try:
        parts = file_line.split(', ')
        file_part = parts[0].split('"')[1] if '"' in parts[0] else 'unknown'
        line_part = parts[1].split()[1] if len(parts) > 1 else '0'
        func_part = parts[2].split()[-1] if len(parts) > 2 else 'unknown'
        signature = f'{exception_type}|{file_part}|{line_part}|{func_part}'
    except Exception:
        signature = f'{exception_type}|{file_line}'

    return signature


async def graphql_request(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Execute a GraphQL request to GitHub API."""
    if not GITHUB_TOKEN:
        raise ValueError('GITHUB_TOKEN not configured')

    session: ClientSession = get_session()
    headers = {
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
        'GraphQL-Features': 'issues_copilot_assignment_api_support,coding_agent_model_selection',
    }

    async with session.post(
        GITHUB_GRAPHQL_URL, json={'query': query, 'variables': variables}, headers=headers
    ) as resp:
        resp.raise_for_status()
        result = await resp.json()

        if 'errors' in result:
            raise Exception(f'GraphQL errors: {result["errors"]}')

        return result.get('data', {})


async def get_repository_id(owner: str, name: str) -> str:
    """Fetch the repository node ID."""
    query = r"""
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
      }
    }
    """
    data = await graphql_request(query, {'owner': owner, 'name': name})
    return data['repository']['id']


async def get_copilot_actor_id(owner: str, name: str) -> str:
    """Fetch the Copilot actor ID from suggested actors.

    Following the documentation, we query suggestedActors with CAN_BE_ASSIGNED capability
    and look for 'copilot-swe-agent'.
    """
    query = r"""
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
          nodes {
            login
            __typename
            ... on Bot {
              id
            }
            ... on User {
              id
            }
          }
        }
      }
    }
    """
    data = await graphql_request(query, {'owner': owner, 'name': name})
    actors = data.get('repository', {}).get('suggestedActors', {}).get('nodes', [])

    for actor in actors:
        if actor.get('login') == 'copilot-swe-agent':
            return actor['id']
    else:
        raise RuntimeError('copilot-swe-agent not found in suggested actors')


async def fetch_ids(owner: str, name: str) -> tuple[str, str]:
    """Fetch repository ID and Copilot actor ID."""
    global cached_ids
    if cached_ids is None:
        repo_id = await get_repository_id(owner, name)
        copilot_id = await get_copilot_actor_id(owner, name)
        cached_ids = (repo_id, copilot_id)
    return cached_ids


async def find_existing_issue(owner: str, name: str, signature: str) -> dict[str, Any] | None:
    """Search for an existing open issue matching the signature."""
    query = r"""
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        issues(
          first: 100,
          states: OPEN,
          orderBy: {field: CREATED_AT, direction: DESC}
        ) {
          nodes {
            id
            number
            title
            body
            url
          }
        }
      }
    }
    """
    data = await graphql_request(query, {'owner': owner, 'name': name})
    issues = data.get('repository', {}).get('issues', {}).get('nodes', [])

    for issue in issues:
        body = issue.get('body', '')
        if f'<!-- signature: {signature} -->' in body:
            return issue

    return None


async def create_issue(
    repo_id: str,
    title: str,
    body: str,
    assignee_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new issue in the repository."""
    mutation = r"""
    mutation(
      $repoId: ID!
      $title: String!
      $body: String!
      $assigneeIds: [ID!]
    ) {
      createIssue(
        input: {
          repositoryId: $repoId
          title: $title
          body: $body
          assigneeIds: $assigneeIds
          agentAssignment: {
            model: "claude-opus-4.5"
          }
        }
      ) {
        issue {
          id
          number
          url
          assignees(first: 10) {
            nodes {
              login
            }
          }
        }
      }
    }
    """
    variables = {
        'repoId': repo_id,
        'title': title,
        'body': body,
        'assigneeIds': assignee_ids or [],
    }
    data = await graphql_request(mutation, variables)
    return data['createIssue']['issue']


async def report_error_to_github(error: BaseException, source: Any) -> str | None:
    """Report the current error to GitHub, creating an issue if needed and assigning Copilot.

    Returns the issue URL if successful, None otherwise.

    Note: GITHUB_ISSUE_ENABLE and RequiresGitHub checks are performed by caller.
    """
    # Filter out exceptions we don't want to report
    if isinstance(
        error.original if isinstance(error, commands.CommandInvokeError) else error,
        FILTERED_EXCEPTIONS,
    ):
        logger.debug(f'Skipping GitHub report for filtered exception: {type(error).__name__}')
        return None

    try:
        owner, name = GITHUB_REPO_SLUG.split('/')
    except ValueError:
        logger.error(f'Invalid GITHUB_REPO_SLUG format: {GITHUB_REPO_SLUG}')
        return None

    try:
        # Format the exception as a traceback string
        error_msg = ''.join(traceback.format_exception(type(error), error, error.__traceback__))

        signature = compute_error_signature(error_msg)
        logger.debug(f'Error signature: {signature}')

        # Check for existing issue
        existing = await find_existing_issue(owner, name, signature)
        if existing:
            logger.info(f'Found existing issue #{existing["number"]}: {existing["url"]}')
            return existing['url']

        # Get repository and Copilot actor IDs
        repo_id, copilot_id = await fetch_ids(owner, name)

        # Create issue with Copilot assigned
        lines = error_msg.strip().split('\n')
        exception_line = lines[-1] if lines else 'Unknown error'
        title = f'[autoreport] {exception_line[:80]}'
        body = f"""
## Traceback

```
{error_msg.strip()}
```

## Initial user interaction

```
{source!r}
```

<!-- signature: {signature} -->
"""

        issue = await create_issue(repo_id, title, body.strip(), [copilot_id])
        logger.info(f'Created issue #{issue["number"]}: {issue["url"]}')

        return issue['url']

    except Exception as e:
        logger.error(f'Failed to report error to GitHub: {e}')
        logger.debug(traceback.format_exc())
        return None
