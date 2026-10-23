"""只发布已有完整构建的同一签名产物；不构建、不签名、不修改已有附件。"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = 'https://api.github.com/repos/poteeto/workspace1'
HEADERS = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
           'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
           'User-Agent': 'DSHA-verified-release'}


def api(path, value=None, method='GET'):
    request = urllib.request.Request(API + path, method=method, headers=HEADERS,
                                     data=None if value is None else json.dumps(value).encode())
    if value is not None:
        request.add_header('Content-Type', 'application/json')
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
                return json.loads(data) if data else None
        except urllib.error.HTTPError as error:
            if method != 'GET' or error.code < 500 or attempt == 3:
                raise
        except urllib.error.URLError:
            if method != 'GET' or attempt == 3:
                raise
        time.sleep(2 * (attempt + 1))


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


record = json.loads((ROOT / 'ci/verified-release.json').read_text(encoding='utf-8'))
version = record['versionName'].split('-')[0]
assert re.fullmatch(r'\d+\.\d+\.\d+', version), 'INVALID_VERSION'
assert re.fullmatch(r'[0-9a-f]{40}', record['applicationSource']), 'INVALID_SOURCE'
tag, apk_name = 'v' + version, 'dsha-' + version + '.apk'
run_id = int(record['fullPipelineRun'])
run = api('/actions/runs/' + str(run_id))
assert run['conclusion'] == 'success' and run['head_sha'] == record['applicationSource'], 'BUILD_NOT_VERIFIED'
assert run['path'] == '.github/workflows/build-dsha-rc2-test-apk.yml', 'WRONG_BUILD_WORKFLOW'
jobs = api('/actions/runs/' + str(run_id) + '/jobs?per_page=100')['jobs']
required = {'test-apk', 'android-kvm-native-v2',
            'GitHub-native permanent key signing and signed ZIP artifact'}
assert required <= {job['name'] for job in jobs}, 'REQUIRED_JOB_MISSING'
assert all(job['conclusion'] == 'success' for job in jobs), 'REQUIRED_JOB_FAILED'
artifact_name = 'DSHA-v' + str(int(record['versionCode'])) + '-GITHUB-KEY-SIGNED-STANDARD-APK'
artifact = api('/actions/artifacts/' + str(int(record['artifactId'])))
assert not artifact['expired'] and artifact['name'] == artifact_name, 'WRONG_SIGNED_ARTIFACT'
assert artifact['workflow_run']['id'] == run_id, 'ARTIFACT_FROM_OTHER_RUN'
assert artifact['digest'] == 'sha256:' + record['signedArtifactSha256'], 'ARTIFACT_CHANGED'
identity = json.loads((ROOT / 'ci/release-identity.json').read_text())
assert identity['githubSigningState'] == 'active', 'PERMANENT_IDENTITY_NOT_ACTIVE'
assert record['certificateSha256'] == identity['certificateSha256'], 'CERTIFICATE_CHANGED'

if '--preflight' in sys.argv:
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write('run_id=' + str(run_id) + '\nartifact_name=' + artifact_name + '\n')
    print('VERIFIED_BUILD_AND_SIGNED_ARTIFACT', run_id, record['applicationSource'])
    raise SystemExit(0)

folder = ROOT / 'release-candidate'
apk, checksum = folder / apk_name, folder / (apk_name + '.sha256')
assert apk.stat().st_size == record['bytes'] and sha256(apk) == record['sha256'], 'APK_BYTES_CHANGED'
assert checksum.read_text().split() == [record['sha256'], apk_name], 'CHECKSUM_CHANGED'
(folder / 'verification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
notes = (ROOT / 'ci/verified-release-notes.md').read_text(encoding='utf-8')
try:
    ref = api('/git/ref/tags/' + tag)
except urllib.error.HTTPError as error:
    if error.code != 404:
        raise
else:
    assert ref['object']['sha'] == run['head_sha'], 'TAG_POINTS_TO_OTHER_SOURCE'
try:
    release = api('/releases/tags/' + tag)
except urllib.error.HTTPError as error:
    if error.code != 404:
        raise
    release = api('/releases', {'tag_name': tag, 'target_commitish': run['head_sha'],
                  'name': 'DSHA v' + str(record['versionCode']) + ' / ' + version,
                  'body': notes, 'draft': True, 'prerelease': True, 'make_latest': 'false'}, 'POST')
assert release['target_commitish'] == run['head_sha'], 'RELEASE_FROM_OTHER_SOURCE'
existing = {asset['name']: asset for asset in api('/releases/' + str(release['id']) + '/assets')}
names = [apk_name, apk_name + '.sha256', 'verification.json']
for name in names:
    path = folder / name
    if name in existing:
        assert existing[name]['digest'] == 'sha256:' + sha256(path), 'EXISTING_ASSET_BYTES_DIFFER'
        continue
    url = urllib.parse.urlsplit(release['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(name))
    connection = http.client.HTTPSConnection(url.netloc, timeout=180)
    connection.putrequest('POST', url.path + '?' + url.query)
    for key, value in HEADERS.items():
        connection.putheader(key, value)
    connection.putheader('Content-Type', 'application/octet-stream')
    connection.putheader('Content-Length', str(path.stat().st_size))
    connection.endheaders()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            connection.send(chunk)
    response = connection.getresponse()
    data = response.read()
    assert response.status == 201, 'UPLOAD_FAILED_' + str(response.status)
    asset = json.loads(data)
    connection.close()
    assert asset['digest'] == 'sha256:' + sha256(path) and asset['size'] == path.stat().st_size, 'UPLOADED_BYTES_DIFFER'
    print('UPLOADED_AND_VERIFIED', name)
remote = {asset['name']: asset for asset in api('/releases/' + str(release['id']) + '/assets')}
for name in names:
    assert remote[name]['digest'] == 'sha256:' + sha256(folder / name), 'PUBLISHED_BYTES_DIFFER'
release = api('/releases/' + str(release['id']),
              {'draft': False, 'prerelease': True, 'make_latest': 'false', 'body': notes}, 'PATCH')
print('PUBLISHED', release['html_url'])
with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
    output.write('[Download DSHA v' + str(record['versionCode']) + '](' + release['html_url'] + ')\n')
