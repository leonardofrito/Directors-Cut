"""Packaging must not silently accept missing or failed signing identities."""
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from tools import build_release


class WindowsSigningTests(unittest.TestCase):
    def test_required_identity_missing_fails_before_signer(self):
        with patch.dict(os.environ,{},clear=True),patch.object(build_release.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'signing identity'):
                build_release.sign_windows(Path('candidate.exe'),required=True)
            run.assert_not_called()

    def test_signing_failure_propagates_to_packager(self):
        with patch.dict(os.environ,{'DIRECTORSCUT_SIGNING_THUMBPRINT':'A'*40},clear=True),patch.object(build_release.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'signer')):
            with self.assertRaises(subprocess.CalledProcessError):
                build_release.sign_windows(Path('candidate.exe'),required=True)

    def test_verify_existing_cloud_signed_file_needs_no_local_key(self):
        with patch.dict(os.environ,{},clear=True),patch.object(build_release.subprocess,'run') as run:
            build_release.sign_windows(Path('candidate.exe'),required=True,verify_only=True)
            command=run.call_args.args[0]
            self.assertIn('-VerifyOnly',command)
            self.assertNotIn('-CertificateThumbprint',command)
            self.assertTrue(run.call_args.kwargs['check'])


if __name__=='__main__':unittest.main()
