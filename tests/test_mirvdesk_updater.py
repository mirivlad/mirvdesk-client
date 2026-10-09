"""Offline regression tests for GitHub-release Debian auto-updater."""
import importlib.util
import pathlib
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "res/mirvdesk-update.py"
spec = importlib.util.spec_from_file_location("mirvdesk_update", SCRIPT)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def release(tag, prerelease=False, digest=None, name=None, url=None):
    if digest is None:
        digest = "sha256:" + "a" * 64
    name = name or f"mirvdesk-{tag.removeprefix('v')}-x86_64.deb"
    url = url or f"https://github.com/mirivlad/mirvdesk-client/releases/download/{tag}/{name}"
    return {
        "tag_name": tag, "draft": False, "prerelease": prerelease,
        "assets": [{"name": name, "browser_download_url": url,
                    "digest": digest, "size": 30000000}],
    }


class UpdateTests(unittest.TestCase):
    def test_stable_never_installs_preview(self):
        releases = [release("v1.7.0-3", True), release("v1.7.0")]
        self.assertEqual(updater.choose_release(releases, "1.6.2", "x86_64")[0], "v1.7.0")
        self.assertIsNone(updater.choose_release([releases[0]], "1.6.2", "x86_64"))

    def test_preview_receives_next_preview_and_stable(self):
        releases = [release("v1.7.0-3", True), release("v1.7.0-2", True)]
        self.assertEqual(updater.choose_release(releases, "1.7.0-1", "x86_64")[0], "v1.7.0-3")
        self.assertIsNone(updater.choose_release(releases, "1.7.0-4", "x86_64"))

    def test_rejects_bad_asset_provenance_and_missing_digest(self):
        valid = release("v1.7.0")
        for modification in [
            {"digest": None},
            {"browser_download_url": "https://rustdesk.com/rustdesk.deb"},
            {"size": updater.MAX_SIZE + 1},
            {"name": "../../mirvdesk.deb"},
        ]:
            data = release("v1.7.0")
            data["assets"][0].update(modification)
            self.assertIsNone(updater.choose_release([data], "1.6.2", "x86_64"))
        self.assertIsNotNone(updater.choose_release([valid], "1.6.2", "x86_64"))

    def test_untrusted_tag_and_unknown_arch(self):
        self.assertIsNone(updater.version_key("v1.7.0+bad"))
        self.assertIsNone(updater.choose_release([release("v1.7.0")], "1.6.2", "armv7"))

    def test_bad_download_hash_cannot_run_dpkg(self):
        import io
        with mock.patch.object(updater, "host_idle", return_value=True):
            with mock.patch.object(updater, "open_https", return_value=io.BytesIO(b"sample")):
                with mock.patch.object(updater.subprocess, "run") as runner:
                    with self.assertRaises(ValueError):
                        updater.apply_update(("v1.7.0-2", "https://github.com/...", "0" * 64, 6))
                    runner.assert_not_called()

    def test_busy_host_defers_without_downloading(self):
        with mock.patch.object(updater, "host_idle", return_value=False):
            with mock.patch.object(updater, "open_https") as getter:
                updater.apply_update(("v1.7.0", "https://github.com/...", "a" * 64, 12))
                getter.assert_not_called()


if __name__ == "__main__":
    unittest.main()
