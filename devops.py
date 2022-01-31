#!/usr/bin/env python3

"""
Devops functions for this package. Includes functions for automated
package deployment, changelog generation, and changelog checking.

This script is generated by the template at
https://github.com/Opus10/public-python-library-template

Do not change this script! Any fixes or updates to this script should be made
to https://github.com/Opus10/public-python-library-template
"""
import os
import subprocess
import sys
import tempfile

from packaging import version


CIRCLECI_ENV_VAR = 'CIRCLECI'


class Error(Exception):
    """Base exception for this script"""


class NotOnCircleCIError(Error):
    """Thrown when not running on CircleCI"""


def _check_git_version():
    """Verify git version"""
    git_version = _shell_stdout("git --version | rev | cut -f 1 -d' ' | rev")
    if version.parse(git_version) < version.parse('2.22.0'):
        raise RuntimeError(
            f'Must have git version >= 2.22.0 (version = {git_version})'
        )


def _shell(
    cmd, check=True, stdin=None, stdout=None, stderr=None
):  # pragma: no cover
    """Runs a subprocess shell with check=True by default"""
    return subprocess.run(
        cmd, shell=True, check=check, stdin=stdin, stdout=stdout, stderr=stderr
    )


def _shell_stdout(cmd, check=True):
    """Runs a shell command and returns stdout"""
    ret = _shell(cmd, stdout=subprocess.PIPE, check=check)
    return ret.stdout.decode('utf-8').strip() if ret.stdout else ''


def _configure_git():
    """Configure git name/email and verify git version"""
    _check_git_version()

    _shell('git config --local user.email "wesleykendall@protonmail.com"')
    _shell('git config --local user.name "Opus 10 Devops"')
    _shell('git config push.default current')


def _find_latest_tag():
    return _shell_stdout('git describe --tags --abbrev=0', check=False)


def _find_sem_ver_update():
    """
    Find the semantic version string based on the commit log.
    Defaults to returning "patch"
    """
    sem_ver = 'patch'
    latest_tag = _find_latest_tag()
    log_section = f'{latest_tag}..HEAD' if latest_tag else ''

    cmd = (
        f"git log {log_section} --pretty='%(trailers:key=type,valueonly)'"
        " | grep -q {sem_ver_type}"
    )
    change_types_found = {
        change_type: _shell(
            cmd.format(sem_ver_type=change_type), check=False
        ).returncode
        == 0
        for change_type in ['bug', 'feature', 'api-break']
    }

    if change_types_found['api-break']:
        sem_ver = 'major'
    elif change_types_found['bug'] or change_types_found['feature']:
        sem_ver = 'minor'

    return sem_ver


def _update_package_version():
    """Apply semantic versioning to package based on git commit messages"""
    # Obtain the current version
    old_version = _shell_stdout("poetry version | rev | cut -f 1 -d' ' | rev")
    if old_version == '0.0.0':
        old_version = ''
    latest_tag = _find_latest_tag()

    if old_version and version.parse(old_version) != version.parse(latest_tag):
        raise RuntimeError(
            f'The latest tag "{latest_tag}" and the current version'
            f' "{old_version}" do not match.'
        )

    # Find out the sem-ver tag to apply
    sem_ver = _find_sem_ver_update()
    _shell(f'poetry version {sem_ver}')

    # Get the new version
    new_version = _shell_stdout("poetry version | rev | cut -f 1 -d' ' | rev")

    if new_version == old_version:
        raise RuntimeError(
            f'Version update could not be applied (version = "{old_version}")'
        )

    return old_version, new_version


def _generate_changelog_and_tag(old_version, new_version):
    """Generates a change log using git-tidy and tags repo"""
    # Tag the version temporarily so that changelog generation
    # renders properly
    _shell(f'git tag -f -a {new_version} -m "Version {new_version}"')

    # Generate the full changelog
    _shell('git tidy-log > CHANGELOG.md')

    # Generate a requirements.txt for readthedocs.org
    _shell('echo "poetry" > docs/requirements.txt')
    _shell('echo "." >> docs/requirements.txt')
    _shell(
        'poetry export --dev --without-hashes -f requirements.txt '
        '>> docs/requirements.txt'
    )

    # Add all updated files
    _shell('git add pyproject.toml CHANGELOG.md docs/requirements.txt')

    # Use [skip ci] to ensure CircleCI doesnt recursively deploy
    _shell(
        'git commit --no-verify -m "Release version'
        f' {new_version} [skip ci]" -m "Type: trivial"'
    )

    # Create release notes just for this release so that we can use them in
    # the commit message
    with tempfile.NamedTemporaryFile() as commit_msg_file:
        _shell(f'echo "{new_version}\n" > {commit_msg_file.name}')
        tidy_log_args = f'^{old_version} HEAD' if old_version else 'HEAD'
        _shell(f'git tidy-log {tidy_log_args} >> {commit_msg_file.name}')

        # Update the tag so that it includes the latest release messages and
        # the automated commit
        _shell(f'git tag -d {new_version}')
        _shell(
            f'git tag -f -a {new_version} -F {commit_msg_file.name}'
            ' --cleanup=whitespace'
        )


def _publish_to_pypi():
    """
    Uses poetry to publish to pypi
    """
    if 'PYPI_USERNAME' not in os.environ or 'PYPI_PASSWORD' not in os.environ:
        raise RuntimeError('Must set PYPI_USERNAME and PYPI_PASSWORD env vars')

    _shell('poetry config http-basic.pypi ${PYPI_USERNAME} ${PYPI_PASSWORD}')
    _shell('poetry build')
    _shell('poetry publish -vvv -n')


def _build_and_push_distribution():
    """
    Builds and pushes distribution to PyPI, along with pushing the
    tags back to the repo
    """
    _publish_to_pypi()

    # Push the code changes after succcessful pypi deploy
    _shell('git push --follow-tags')


def deploy():
    """Deploys the package and uploads documentation."""
    # Ensure proper environment
    if not os.environ.get(CIRCLECI_ENV_VAR):  # pragma: no cover
        raise NotOnCircleCIError('Must be on CircleCI to run this script')

    _configure_git()

    old_version, new_version = _update_package_version()

    _generate_changelog_and_tag(old_version, new_version)

    _build_and_push_distribution()

    print(f'Deployment complete. Latest version is {new_version}')


if __name__ == '__main__':
    if sys.argv[-1] == 'deploy':
        deploy()
    else:
        raise RuntimeError(f'Invalid subcommand "{sys.argv[-1]}"')
