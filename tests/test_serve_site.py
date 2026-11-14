from pathlib import Path
import unittest

from scripts.serve_site import Handler, ROOT


class PublicPreviewTests(unittest.TestCase):
    @staticmethod
    def public_path(request_path):
        # Exercise the same allowlist used by both GET and HEAD without binding a port.
        handler = object.__new__(Handler)
        handler.path = request_path
        return handler.public_path()

    def test_nfl_assurance_subsite_pages_and_assets_are_previewable(self):
        paths = (
            "nfl-assurance-9580ac3f/site/index.html",
            "nfl-assurance-9580ac3f/site/style.css",
            "nfl-assurance-9580ac3f/site/app.js",
            "nfl-assurance-9580ac3f/site/manifest.json",
        )
        for relative in paths:
            with self.subTest(path=relative):
                self.assertEqual(
                    self.public_path("/" + relative),
                    (ROOT / relative).resolve(),
                )

    def test_nonpublic_paths_and_unsupported_extensions_stay_blocked(self):
        for request_path in ("/.git/config", "/nfl-assurance-9580ac3f/site/missing.html"):
            with self.subTest(path=request_path):
                self.assertIsNone(self.public_path(request_path))

        # The directory itself may be public, but only the preview's static types are served.
        self.assertIsNone(
            self.public_path("/nfl-assurance-9580ac3f/site/index.html.exe")
        )


if __name__ == "__main__":
    unittest.main()
