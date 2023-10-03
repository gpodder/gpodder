#!/usr/bin/env python3
"""
Prepare release and upload Windows and macOS artifacts
"""
import argparse
import hashlib
import os
import re
import sys

import magic  # use python-magic (not compatible with filemagic)
import requests
from github3 import login
from jinja2 import Template


def debug_requests():
    """ turn requests debug on """
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    import http.client as http_client
    import logging
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def error_exit(msg, code=1):
    """ print msg and exit with code """
    print(msg, file=sys.stderr)
    sys.exit(code)


def download_items(urls, prefix):
    print("D: downloading %s" % urls)
    for url in urls:
        print("I: downloading %s" % url)
        filename = url.split('/')[-1]
        output = os.path.join("_build", "{}-{}".format(prefix, filename))
        with requests.get(url, stream=True) as r:
            with open(output, "wb") as f:
                for chunk in r.iter_content(chunk_size=1000000):
                    f.write(chunk)


def download_circleci(circleci, prefix):
    """ download build artifacts from circleCI and exit """
    print("I: downloading release artifacts from Circle.ci")
    artifacts = requests.get("https://circleci.com/api/v1.1/project/github/gpodder/gpodder/%s/artifacts" % circleci).json()
    items = set([u["url"] for u in artifacts if re.match(".+/gPodder-.+\.zip$", u["path"])])
    if len(items) == 0:
        error_exit("Nothing found to download")
    download_items(items, prefix)


def download_appveyor(appveyor_build, prefix):
    """ download build artifacts from appveyor and exit """
    print("I: downloading release artifacts from appveyor")
    build = requests.get("https://ci.appveyor.com/api/projects/elelay/gpodder/build/%s" % appveyor_build).json()
    job_id = build.get("build", {}).get("jobs", [{}])[0].get("jobId")
    if job_id:
        job_url = "https://ci.appveyor.com/api/buildjobs/{}/artifacts".format(job_id)
        artifacts = requests.get(job_url).json()
        items = ["{}/{}".format(job_url, f["fileName"]) for f in artifacts if f["type"] == "File"]
        if len(items) == 0:
            error_exit("Nothing found to download")
        download_items(items, prefix)
    else:
        error_exit("no jobId in {}".format(build))


def checksums():
    """ compute artifact checksums """
    ret = {}
    for f in os.listdir("_build"):
        archive = os.path.join("_build", f)
        m = hashlib.md5()
        s = hashlib.sha256()
        with open(archive, "rb") as f:
            block = f.read(4096)
            while block:
                m.update(block)
                s.update(block)
                block = f.read(4096)
        ret[os.path.basename(archive)] = dict(md5=m.hexdigest(), sha256=s.hexdigest())
    return ret


def get_contributors(tag, previous_tag):
    """
    list contributor logins '@...' for every commit in range
    """
    cmp = repo.compare_commits(previous_tag, tag)
    logins = [c.author.login for c in cmp.commits() if c.author] + [c.committer.login for c in cmp.commits()]
    return sorted(set("@{}".format(n) for n in logins))


def get_previous_tag():
    latest_release = repo.latest_release()
    return latest_release.tag_name


def release_text(tag, previous_tag, circleci=None, appveyor=None):
    t = Template("""
Linux, macOS and Windows are supported.

Thanks to {{contributors[0]}}{% for c in contributors[1:-1] %}, {{c}}{% endfor %} and {{contributors[-1]}} for contributing to this release!

[Changes](https://github.com/gpodder/gpodder/compare/{{previous_tag}}...{{tag}}) since **{{previous_tag}}**:


## New features
 - ...

## Improvements
 - ...

## Bug fixes
 - ...

## Translations
 - ...

## CI references
 - macOS CircleCI build [{{circleci}}](https://circleci.com/gh/gpodder/gpodder/{{circleci}})
 - Windows Appveyor build [{{appveyor}}](https://ci.appveyor.com/project/elelay/gpodder/build/{{appveyor}})

## Checksums
{% for f, c in checksums.items() %}
 - {{f}} md5:<i>{{c.md5}}</i> sha256:<i>{{c.sha256}}</i>
{% endfor %}
""")
    args = {
            'contributors': get_contributors(tag, previous_tag),
            'tag': tag,
            'previous_tag': previous_tag,
            'circleci': circleci,
            'appveyor': appveyor,
            'checksums': checksums()
    }
    return t.render(args)


def upload(repo, tag, previous_tag, circleci, appveyor):
    """ create github release (draft) and upload assets """
    print("I: creating release %s" % tag)
    items = os.listdir('_build')
    if len(items) == 0:
        error_exit("Nothing found to upload")
    try:
        release = repo.create_release(tag, name=tag, draft=True)
    except Exception as e:
        error_exit("Error creating release '%s' (%r)" % (tag, e))
    print("I: updating release description from template")
    text = release_text(tag, previous_tag, circleci=circleci, appveyor=appveyor)
    print(text)
    if release.edit(body=text):
        print("I: updated release description")
    else:
        error_exit("E: updating release description")
    print("D: uploading items\n - %s" % "\n - ".join(items))
    m = magic.Magic(mime=True)
    for itm in items:
        filename = os.path.join("_build", itm)
        content_type = m.from_file(filename)
        print("I: uploading %s..." % itm)
        with open(filename, "rb") as f:
            try:
                asset = release.upload_asset(content_type, itm, f)
            except Exception as e:
                error_exit("Error uploading asset '%s' (%r)" % (itm, e))
    print("I: upload success")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='upload gpodder-osx-bundle artifacts to a github release\n'
        'Example usage: \n'
        '    GITHUB_TOKEN=xxx python github_release.py --download --circleci 171 --appveyor 1.0.104 3.10.4\n'
        '    GITHUB_TOKEN=xxx python github_release.py --circleci 171 --appveyor 1.0.104 3.10.4\n',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('tag', type=str,
                        help='gPodder git tag to create a release from')
    parser.add_argument('--download', action='store_true',
                        help='download artifacts from given circle.ci and appveyor build numbers')
    parser.add_argument('--circleci', type=str, help='circleCI build number')
    parser.add_argument('--appveyor', type=str, help='appveyor build number')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='debug requests')

    args = parser.parse_args()

    if args.debug:
        debug_requests()

    github_token = os.environ.get("GITHUB_TOKEN")
    if not github_token:
        error_exit("E: set GITHUB_TOKEN environment", -1)

    gh = login(token=github_token)
    repo = gh.repository('gpodder', 'gpodder')

    if args.download:
        if not args.circleci:
            error_exit("E: --download requires --circleci number")
        elif not args.appveyor:
            error_exit("E: --download requires --appveyor number")
        if os.path.isdir("_build"):
            error_exit("E: _build directory exists", -1)
        os.mkdir("_build")
        download_circleci(args.circleci, "macOS")
        download_appveyor(args.appveyor, "windows")
        print("I: download success.")
    else:
        if not os.path.exists("_build"):
            error_exit("E: _build directory doesn't exist. You need to download build artifacts (see Usage)", -1)

    previous_tag = get_previous_tag()
    upload(repo, args.tag, previous_tag, args.circleci, args.appveyor)
