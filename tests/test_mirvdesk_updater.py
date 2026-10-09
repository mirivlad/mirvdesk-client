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


import importlib.util
PREPROCESS = pathlib.Path(__file__).resolve().parents[1] / "res/msi/preprocess.py"
msi_spec = importlib.util.spec_from_file_location("mirvdesk_msi_preprocess", PREPROCESS)
msi = importlib.util.module_from_spec(msi_spec)
msi_spec.loader.exec_module(msi)


class MSIVersionTests(unittest.TestCase):
    def test_preview_and_stable_msi_versions_increase(self):
        previews = ["1.7.0-1", "1.7.0-2", "1.7.0-3", "1.7.0", "1.7.1-1", "1.7.1"]
        converted = [tuple(map(int, msi.mirvdesk_msi_version(v).split("."))) for v in previews]
        self.assertEqual(converted, sorted(converted))
        self.assertEqual(msi.mirvdesk_msi_version("1.7.0-3"), "1.7.3")
        self.assertEqual(msi.mirvdesk_msi_version("1.7.0"), "1.7.99")
        self.assertEqual(msi.mirvdesk_msi_version("1.6.2"), "1.6.2")

    def test_msi_versions_are_three_numeric_components(self):
        for bad in ["1.7.0-99", "1.7.0-pre", "1.7.0-3.98767", "1.7.999-1"]:
            with self.assertRaises(ValueError):
                msi.mirvdesk_msi_version(bad)


if __name__ == "__main__":
    unittest.main()
