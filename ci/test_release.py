import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('release', Path(__file__).with_name('release.py'))
r = importlib.util.module_from_spec(SPEC)
if Path(SPEC.origin).exists():
    SPEC.loader.exec_module(r)


class PolicyTests(unittest.TestCase):
    def test_metadata_strict_identity_and_single_safe_apk(self):
        self.assertTrue(hasattr(r, 'metadata'), 'metadata policy is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'app.apk').write_bytes(b'apk')
            data = {'applicationId': 'top.cyqi.hook.mihome', 'elements': [
                {'versionName': '1.1.0', 'versionCode': 2, 'outputFile': 'app.apk'}]}
            def check(tag='v1.1.0'):
                (root / 'output-metadata.json').write_text(json.dumps(data))
                return r.metadata(root, tag)
            self.assertEqual(check(), (root / 'app.apk', '1.1.0', 2))
            for tag in ['v1.1', 'v01.1.0', 'v1.1.0\n', 'v1.1.0;id', 'v1.2.0']:
                with self.subTest(tag=tag), self.assertRaises(ValueError):
                    check(tag)
            for field, values in {'versionCode': [0, -1, True, '2'], 'outputFile': ['../app.apk', '/tmp/app.apk', 'x\\app.apk'], 'versionName': ['1.2.0']}.items():
                original = data['elements'][0][field]
                for value in values:
                    data['elements'][0][field] = value
                    with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                        check()
                data['elements'][0][field] = original
            data['applicationId'] = 'other'
            with self.assertRaises(ValueError):
                check()
            data['applicationId'] = 'top.cyqi.hook.mihome'
            (root / 'extra.apk').write_bytes(b'bad')
            with self.assertRaises(ValueError):
                check()

    def test_signer_and_manifest_fail_closed(self):
        self.assertTrue(hasattr(r, 'verify_identity'), 'signature policy is not implemented')
        digest = 'ab' * 32
        signature = 'Signer #1 certificate SHA-256 digest: ' + digest + '\n'
        manifest = "package: name='top.cyqi.hook.mihome' versionCode='2' versionName='1.1.0'\n"
        r.verify_identity(signature, manifest, digest.upper(), '1.1.0', 2)
        for sig, badging, expected in [
            ('', manifest, digest), (signature + signature, manifest, digest),
            (signature, manifest, 'cd' * 32), (signature, manifest, ''),
            (signature, manifest + 'application-debuggable\n', digest),
            (signature, manifest.replace("'2'", "'3'"), digest),
            (signature, manifest.replace('top.cyqi.hook.mihome', 'other'), digest),
            (signature, manifest.replace('1.1.0', '1.2.0'), digest)]:
            with self.subTest(sig=sig, badging=badging), self.assertRaises(ValueError):
                r.verify_identity(sig, badging, expected, '1.1.0', 2)

    def test_signing_cleans_key_on_failure_and_passes_passwords_by_env(self):
        self.assertTrue(hasattr(r, 'sign'), 'signing is not implemented')
        from unittest.mock import patch
        import base64
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input'
            source.mkdir()
            (source / 'app.apk').write_bytes(b'apk')
            (source / 'output-metadata.json').write_text(json.dumps({'applicationId': r.PACKAGE, 'elements': [{'versionName': '1.1.0', 'versionCode': 2, 'outputFile': 'app.apk'}]}))
            cert = root / 'cert'
            cert.write_text('ab' * 32)
            env = {'ANDROID_KEYSTORE_BASE64': base64.b64encode(b'private-key').decode(), 'ANDROID_KEYSTORE_PASSWORD': 'secret1', 'ANDROID_KEY_ALIAS': 'production', 'ANDROID_KEY_PASSWORD': 'secret2'}
            seen = []
            def command(args):
                if 'sign' in args:
                    key = Path(args[args.index('--ks') + 1])
                    seen.append(key)
                    self.assertEqual(key.read_bytes(), b'private-key')
                    if os.name != 'nt':
                        self.assertEqual(key.stat().st_mode & 0o777, 0o600)
                    self.assertIn('env:ANDROID_KEYSTORE_PASSWORD', args)
                    self.assertNotIn('secret1', args)
                    raise RuntimeError('signer failed')
                return ''
            with patch.dict(os.environ, env), self.assertRaises(RuntimeError):
                r.sign(source, 'v1.1.0', root / 'out', root / 'tools', cert, command=command)
            self.assertEqual(len(seen), 1)
            self.assertFalse(seen[0].exists())
            def successful_command(args):
                if 'sign' in args:
                    Path(args[args.index('--out') + 1]).write_bytes(b'test-signed-artifact')
                if 'verify' in args:
                    return 'Signer #1 certificate SHA-256 digest: ' + 'ab' * 32 + '\n'
                if 'badging' in args:
                    return "package: name='top.cyqi.hook.mihome' versionCode='2' versionName='1.1.0'\n"
                return ''
            with patch.dict(os.environ, env):
                final = r.sign(source, 'v1.1.0', root / 'success', root / 'tools', cert, command=successful_command)
            self.assertEqual(final.name, 'top.cyqi.hook.mihome-1.1.0.apk')
            for line in (final.parent / 'SHA256SUMS').read_text().splitlines():
                digest, name = line.split('  ')
                self.assertEqual(digest, r.sha256(final.parent / name))
            self.assertEqual(len(list(final.parent.iterdir())), 4)
            env['ANDROID_KEYSTORE_BASE64'] = 'not-base64!'
            with patch.dict(os.environ, env), self.assertRaises(ValueError):
                r.sign(source, 'v1.1.0', root / 'out2', root / 'tools', cert, command=command)

    def test_existing_draft_is_found_when_tag_endpoint_returns_404(self):
        # GitHub's /releases/tags endpoint only exposes published releases.
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['top.cyqi.hook.mihome-1.1.0.apk', 'SHA256SUMS', 'SIGNING-CERTIFICATE.txt', 'release-notes.md']
            for name in names:
                (root / name).write_text(name)
            state = {'id': 12, 'draft': True, 'prerelease': False, 'tag_name': 'v1.1.0', 'assets': []}
            def command(args):
                if args[1] == 'api':
                    endpoint = args[2]
                    if '/releases/tags/' in endpoint:
                        raise r.CommandError('gh', subprocess.CompletedProcess(args, 1, '', 'gh: Not Found (HTTP 404)'))
                    if '/releases?' in endpoint:
                        self.assertIn('--paginate', args)
                        self.assertIn('--slurp', args)
                        return json.dumps([[{'id': 1, 'tag_name': 'v0.1.0'}], [state]])
                    self.assertEqual(endpoint, 'repos/owner/repo/releases/12')
                    if '--method' in args:
                        state['draft'] = False
                        state['prerelease'] = False
                    return json.dumps(state)
                if args[1:3] == ['release', 'create']:
                    self.fail('Existing draft must not be recreated after a tag-endpoint 404')
                if args[1:3] == ['release', 'upload']:
                    state['assets'] = [{'name': n} for n in names]
                if args[1:3] == ['release', 'download']:
                    dest = Path(args[args.index('--dir') + 1])
                    for file in root.iterdir():
                        (dest / file.name).write_bytes(file.read_bytes())
                return ''
            r.publish(root, 'v1.1.0', 'owner/repo', command=command)
            self.assertFalse(state['draft'])

    def test_publish_refuses_published_and_verifies_downloads_before_publish(self):
        self.assertTrue(hasattr(r, 'publish'), 'draft publishing is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['top.cyqi.hook.mihome-1.1.0.apk', 'SHA256SUMS', 'SIGNING-CERTIFICATE.txt', 'release-notes.md']:
                (root / name).write_text(name)
            calls = []
            state = {'id': 12, 'draft': False, 'tag_name': 'v1.1.0', 'assets': []}
            def command(args):
                calls.append(args)
                if args[1] == 'api':
                    if '/releases?' in args[2]:
                        return json.dumps([[state]])
                    if '--method' in args:
                        state['draft'] = False
                    return json.dumps(state)
                if args[1:3] == ['release', 'download']:
                    dest = Path(args[args.index('--dir') + 1])
                    for p in root.iterdir():
                        (dest / p.name).write_bytes(p.read_bytes())
                return ''
            with self.assertRaises(ValueError):
                r.publish(root, 'v1.1.0', 'owner/repo', command=command)
            self.assertEqual(len(calls), 1)
            state['draft'] = True
            state['assets'] = [{'name': p.name} for p in root.iterdir()]
            r.publish(root, 'v1.1.0', 'owner/repo', command=command)
            download = next(i for i, a in enumerate(calls) if a[1:3] == ['release', 'download'])
            publication = next(i for i, a in enumerate(calls) if '--method' in a)
            self.assertLess(download, publication)
            self.assertFalse(state['draft'])
            state['draft'] = True
            calls.clear()
            def corrupt(args):
                result = command(args)
                if args[1:3] == ['release', 'download']:
                    (Path(args[args.index('--dir') + 1]) / 'SHA256SUMS').write_text('tampered')
                return result
            with self.assertRaises(ValueError):
                r.publish(root, 'v1.1.0', 'owner/repo', command=corrupt)
            self.assertTrue(state['draft'])
            self.assertFalse(any('--method' in a for a in calls))

    def test_new_draft_is_created_only_after_successful_empty_list(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['top.cyqi.hook.mihome-1.1.0.apk', 'SHA256SUMS', 'SIGNING-CERTIFICATE.txt', 'release-notes.md']
            for name in names:
                (root / name).write_text(name)
            for status in [None, 403, 404, 500]:
                calls = []
                exists = [False]
                state = {'id': 12, 'draft': True, 'tag_name': 'v1.1.0', 'assets': []}
                def command(args):
                    calls.append(args)
                    if args[1] == 'api' and '/releases?' in args[2]:
                        if status is not None:
                            raise r.CommandError('gh', subprocess.CompletedProcess(args, 1, '', f'gh: error (HTTP {status})'))
                        return json.dumps([[state]] if exists[0] else [[]])
                    if args[1:3] == ['release', 'create']:
                        exists[0] = True
                    if args[1:3] == ['release', 'upload']:
                        state['assets'] = [{'name': n} for n in names]
                    if args[1:3] == ['release', 'download']:
                        dest = Path(args[args.index('--dir') + 1])
                        for p in root.iterdir():
                            (dest / p.name).write_bytes(p.read_bytes())
                    if '--method' in args:
                        state['draft'] = False
                    return json.dumps(state)
                with self.subTest(status=status):
                    if status is None:
                        r.publish(root, 'v1.1.0', 'owner/repo', command=command)
                        self.assertIn('--draft', calls[1])
                        self.assertIn('--verify-tag', calls[1])
                    else:
                        with self.assertRaises(r.CommandError):
                            r.publish(root, 'v1.1.0', 'owner/repo', command=command)
                        self.assertEqual(len(calls), 1)

    def test_new_draft_visibility_delay_does_not_recreate_draft(self):
        from unittest.mock import patch, call
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['top.cyqi.hook.mihome-1.1.0.apk', 'SHA256SUMS', 'SIGNING-CERTIFICATE.txt', 'release-notes.md']
            for name in names:
                (root / name).write_text(name)
            state = {'id': 12, 'draft': True, 'tag_name': 'v1.1.0', 'assets': []}
            creates, reads = [], []
            def command(args):
                if args[1] == 'api' and '/releases?' in args[2]:
                    if not creates:
                        return '[[]]'
                    reads.append(True)
                    return json.dumps([[]] if len(reads) <= 2 else [[state]])
                if args[1:3] == ['release', 'create']:
                    creates.append(True)
                if args[1:3] == ['release', 'upload']:
                    state['assets'] = [{'name': name} for name in names]
                if args[1:3] == ['release', 'download']:
                    dest = Path(args[args.index('--dir') + 1])
                    for file in root.iterdir():
                        (dest / file.name).write_bytes(file.read_bytes())
                if '--method' in args:
                    state['draft'] = False
                return json.dumps(state)
            with patch('time.sleep') as sleep:
                r.publish(root, 'v1.1.0', 'owner/repo', command=command)
            self.assertEqual(len(creates), 1)
            self.assertEqual(sleep.call_args_list, [call(1), call(2)])
            self.assertFalse(state['draft'])

    def test_release_list_ambiguity_and_wrong_shapes_fail_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['top.cyqi.hook.mihome-1.1.0.apk', 'SHA256SUMS', 'SIGNING-CERTIFICATE.txt', 'release-notes.md']:
                (root / name).write_text(name)
            state = {'id': 12, 'draft': True, 'tag_name': 'v1.1.0', 'assets': []}
            for payload in [[state], {'items': []}, [[state, state]]]:
                calls = []
                def command(args):
                    calls.append(args)
                    return json.dumps(payload)
                with self.subTest(payload=payload), self.assertRaises(ValueError):
                    r.publish(root, 'v1.1.0', 'owner/repo', command=command)
                self.assertEqual(len(calls), 1)

    def test_command_errors_are_redacted_and_404_is_distinguishable(self):
        self.assertTrue(hasattr(r, 'CommandError'), 'safe command errors are not implemented')
        import sys
        with self.assertRaises(r.CommandError) as caught:
            r.run([sys.executable, '-c', 'import sys;sys.stderr.write("private (HTTP 404)");sys.exit(1)'])
        self.assertNotIn('private', str(caught.exception))
        self.assertIn('(HTTP 404)', caught.exception.stderr)
        self.assertEqual(r.run([sys.executable, '-c', 'print("success")']).strip(), 'success')

    def test_cli_integrity_and_metadata_and_tampered_jar(self):
        import subprocess
        import sys
        cli = Path(r.__file__)
        result = subprocess.run([sys.executable, str(cli), 'integrity'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Verified 2 pinned JARs', result.stdout)
        self.assertTrue(hasattr(r, 'integrity'))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((ValueError, FileNotFoundError)):
                r.integrity(Path(tmp))
            import shutil
            repo = Path(__file__).resolve().parent.parent
            for name in ['mihome-hook/libs/api-82.jar', 'mihome-hook/gradle/wrapper/gradle-wrapper.jar']:
                target = Path(tmp) / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(repo / name, target)
            r.integrity(Path(tmp))
            (Path(tmp) / 'mihome-hook/libs/api-82.jar').write_bytes(b'tampered')
            with self.assertRaises(ValueError):
                r.integrity(Path(tmp))


if __name__ == '__main__':
    unittest.main()
