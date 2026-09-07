"""Fail-closed Android release tooling; Python standard library only."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

PACKAGE = 'top.cyqi.hook.mihome'


def metadata(directory, tag):
    if not re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', tag):
        raise ValueError('Release tag must be vX.Y.Z without leading zeroes')
    directory = Path(directory)
    data = json.loads((directory / 'output-metadata.json').read_text(encoding='utf-8'))
    elements = data.get('elements', [])
    if data.get('applicationId') != PACKAGE or len(elements) != 1:
        raise ValueError('Expected production applicationId and exactly one output')
    item = elements[0]
    version, code, name = item.get('versionName'), item.get('versionCode'), item.get('outputFile')
    if version != tag[1:] or type(code) is not int or code <= 0:
        raise ValueError('Tag/version mismatch or invalid versionCode')
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.apk', name):
        raise ValueError('Unsafe APK filename')
    apk = directory / name
    if apk.is_symlink() or not apk.is_file() or list(directory.rglob('*.apk')) != [apk]:
        raise ValueError('Expected exactly one regular APK')
    return apk, version, code


def verify_identity(signature, badging, expected, version, code):
    expected = expected.strip().lower()
    digests = re.findall(r'^Signer #[0-9]+ certificate SHA-256 digest: ([0-9a-fA-F]{64})$', signature, re.MULTILINE)
    if not re.fullmatch(r'[0-9a-f]{64}', expected) or [d.lower() for d in digests] != [expected]:
        raise ValueError('APK signer does not match the pinned production certificate')
    package = re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'", badging, re.MULTILINE)
    if not package or package.groups() != (PACKAGE, str(code), version) or 'application-debuggable' in badging:
        raise ValueError('APK manifest identity/version/debuggable verification failed')


class CommandError(RuntimeError):
    def __init__(self, program, result):
        super().__init__(f'{Path(program).name} failed (exit {result.returncode}); output suppressed')
        self.stderr = result.stderr


def run(args):
    # Never echo argv/output on failure: external tools can include credential details.
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding='utf-8')
    if result.returncode:
        raise CommandError(args[0], result)
    return result.stdout


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sign(source, tag, output, tools, certificate, command=run):
    apk, version, code = metadata(source, tag)
    expected = Path(certificate).read_text(encoding='ascii').strip().lower()
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('Invalid production certificate pin')
    required = ('ANDROID_KEYSTORE_BASE64', 'ANDROID_KEYSTORE_PASSWORD', 'ANDROID_KEY_ALIAS', 'ANDROID_KEY_PASSWORD')
    if any(not os.environ.get(name) for name in required):
        raise ValueError('All four production signing secrets are required')
    try:
        key_bytes = base64.b64decode(os.environ['ANDROID_KEYSTORE_BASE64'], validate=True)
    except ValueError:
        raise ValueError('Invalid keystore base64') from None
    if not key_bytes:
        raise ValueError('Empty keystore')
    tools, output = Path(tools), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise ValueError('Output directory must be empty')
    signer = tools / ('apksigner.bat' if os.name == 'nt' else 'apksigner')
    aligner = tools / ('zipalign.exe' if os.name == 'nt' else 'zipalign')
    aapt = tools / ('aapt2.exe' if os.name == 'nt' else 'aapt2')
    final = output / f'{PACKAGE}-{version}.apk'
    # TemporaryDirectory's finally cleanup runs on both signer and verification failures.
    with tempfile.TemporaryDirectory(prefix='android-release-') as tmp:
        key = Path(tmp) / 'production.p12'
        fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(key_bytes)
        del key_bytes
        aligned = Path(tmp) / 'aligned.apk'
        command([aligner, '-P', '16', '-f', '4', apk, aligned])
        command([signer, 'sign', '--ks', key, '--ks-key-alias', os.environ['ANDROID_KEY_ALIAS'],
                 '--ks-pass', 'env:ANDROID_KEYSTORE_PASSWORD', '--key-pass', 'env:ANDROID_KEY_PASSWORD',
                 '--v4-signing-enabled', 'false', '--out', final, aligned])
        command([aligner, '-c', '-P', '16', '4', final])
        signature = command([signer, 'verify', '--verbose', '--print-certs', final])
        badging = command([aapt, 'dump', 'badging', final])
        verify_identity(signature, badging, expected, version, code)
    (output / 'SIGNING-CERTIFICATE.txt').write_text(
        f'Application ID: {PACKAGE}\nCertificate SHA-256: {expected}\n', encoding='utf-8')
    (output / 'release-notes.md').write_text(
        f'# QimiuihomeHook {version}\n\nProduction-signed APK; versionCode {code}.\n\n'
        'All launcher versions are eligible for interface checks; this is not a guarantee of compatibility. '
        'Android 14+ and a working legacy Xposed API 82 LSPosed environment are required. '
        'Scope: com.miui.home only. The module changes suspended-icon filtering, not suspension or launch restrictions.\n\n'
        'Automated JVM tests, lint, build, package, alignment and signature checks do not replace device validation. '
        'No real-device or multi-version compatibility validation is claimed for this release.\n\n'
        'Migration from a debug-signed or differently signed build requires uninstalling the old module first '
        '(its app data may be lost), then installing this APK and re-enabling it in LSPosed with the launcher scope. '
        'Do not clear launcher data. Future releases signed with this production key can update this build.\n', encoding='utf-8')
    assets = sorted(output.iterdir())
    (output / 'SHA256SUMS').write_text(''.join(f'{sha256(p)}  {p.name}\n' for p in assets), encoding='ascii')
    return final


def publish(output, tag, repository, command=run):
    if not re.fullmatch(r'v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', tag):
        raise ValueError('Invalid release tag')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('Invalid repository')
    output = Path(output)
    names = {f'{PACKAGE}-{tag[1:]}.apk', 'SHA256SUMS', 'SIGNING-CERTIFICATE.txt', 'release-notes.md'}
    if {p.name for p in output.iterdir()} != names or any(p.is_symlink() or not p.is_file() for p in output.iterdir()):
        raise ValueError('Unexpected release assets')
    endpoint = f'repos/{repository}/releases/tags/{tag}'
    try:
        state = json.loads(command(['gh', 'api', endpoint]))
    except CommandError as error:
        if '(HTTP 404)' not in error.stderr:
            raise
        command(['gh', 'release', 'create', tag, '--repo', repository, '--verify-tag', '--draft',
                 '--title', f'QimiuihomeHook {tag}', '--notes-file', output / 'release-notes.md'])
        state = json.loads(command(['gh', 'api', endpoint]))
    if state.get('draft') is not True or state.get('tag_name') != tag:
        raise ValueError('Refusing to overwrite an already published release or mismatched tag')
    # Only a draft is replaceable. Unexpected old assets fail closed rather than leak into publication.
    if any(a['name'] not in names for a in state.get('assets', [])):
        raise ValueError('Existing draft contains unexpected assets; remove them explicitly')
    command(['gh', 'release', 'edit', tag, '--repo', repository, '--draft=true',
             '--title', f'QimiuihomeHook {tag}', '--notes-file', output / 'release-notes.md'])
    command(['gh', 'release', 'upload', tag, '--repo', repository, '--clobber',
             *[output / name for name in sorted(names)]])
    state = json.loads(command(['gh', 'api', endpoint]))
    if state.get('draft') is not True or sorted(a['name'] for a in state.get('assets', [])) != sorted(names):
        raise ValueError('Draft upload readback failed')
    with tempfile.TemporaryDirectory(prefix='release-readback-') as tmp:
        command(['gh', 'release', 'download', tag, '--repo', repository, '--dir', tmp])
        if {p.name for p in Path(tmp).iterdir()} != names:
            raise ValueError('Downloaded asset set differs')
        for name in names:
            if sha256(output / name) != sha256(Path(tmp) / name):
                raise ValueError('Downloaded release asset checksum differs')
    release_endpoint = f'repos/{repository}/releases/{state["id"]}'
    command(['gh', 'api', release_endpoint, '--method', 'PATCH', '-F', 'draft=false', '-F', 'prerelease=false'])
    state = json.loads(command(['gh', 'api', release_endpoint]))
    if state.get('draft') is not False or state.get('tag_name') != tag:
        raise ValueError('Publication readback failed')
    print(f'Published and verified {repository} {tag}')


def integrity(root):
    pins = {
        'mihome-hook/libs/api-82.jar': 'f48c635f1c7469fdec0e00ad2ea0b7a6b2f5b55065784a35b7ca3a84615e8e25',
        'mihome-hook/gradle/wrapper/gradle-wrapper.jar': '497c8c2a7e5031f6aa847f88104aa80a93532ec32ee17bdb8d1d2f67a194a9c7',
    }
    for name, expected in pins.items():
        if sha256(Path(root) / name) != expected:
            raise ValueError(f'JAR integrity check failed: {name}')
    print('Verified 2 pinned JARs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['integrity', 'metadata', 'sign', 'publish'])
    parser.add_argument('--tag', default=os.environ.get('RELEASE_TAG', ''))
    parser.add_argument('--source', type=Path, default=Path('mihome-hook/app/build/outputs/apk/release'))
    parser.add_argument('--output', type=Path, default=Path('release-assets'))
    parser.add_argument('--tools', type=Path, default=Path(os.environ.get('ANDROID_HOME', '')) / 'build-tools/35.0.0')
    parser.add_argument('--certificate', type=Path, default=Path('ci/release-certificate.sha256'))
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', ''))
    args = parser.parse_args()
    if args.operation == 'integrity':
        integrity(Path(__file__).resolve().parent.parent)
    elif args.operation == 'metadata':
        print(metadata(args.source, args.tag))
    elif args.operation == 'sign':
        print(sign(args.source, args.tag, args.output, args.tools, args.certificate))
    else:
        publish(args.output, args.tag, args.repository)


if __name__ == '__main__':
    main()
