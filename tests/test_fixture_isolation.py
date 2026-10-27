import unittest
import shutil
import tempfile
from pathlib import Path
from build_site import build_site, SITE_DIR, PREVIEW_DIR, FIXTURES_DIR


class TestFixtureIsolation(unittest.TestCase):
    def setUp(self):
        # Ensure a clean production build of site/
        build_site(use_fixtures=False)

    def test_production_build_excludes_fixtures(self):
        build_site(use_fixtures=False)
        for html_file in SITE_DIR.rglob("*.html"):
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertNotIn("SAMPLE – NOT REAL", content)
                self.assertNotIn("Sample Bangalore Chai Co", content)

    def test_no_sample_not_real_in_production_site(self):
        """
        Guarantees that 'SAMPLE – NOT REAL' never appears in any .html, .json, or .xml
        file under site/. Ignores .css files.
        """
        build_site(use_fixtures=False)
        target_extensions = {".html", ".json", ".xml"}
        found_violations = []

        for p in SITE_DIR.rglob("*"):
            if p.is_file() and p.suffix.lower() in target_extensions:
                try:
                    text = p.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if "SAMPLE – NOT REAL" in text:
                    found_violations.append(str(p))

        self.assertEqual(
            found_violations,
            [],
            f"Found 'SAMPLE – NOT REAL' in production site files: {found_violations}"
        )

    def test_fixture_flag_writes_only_to_preview_or_temp_dir(self):
        # 1. Test writing to preview/ by default with --use-fixtures
        if PREVIEW_DIR.exists():
            shutil.rmtree(PREVIEW_DIR)

        build_site(use_fixtures=True)

        self.assertTrue(PREVIEW_DIR.exists())
        preview_index = PREVIEW_DIR / "index.html"
        self.assertTrue(preview_index.exists())
        preview_content = preview_index.read_text(encoding="utf-8")
        self.assertIn("SAMPLE – NOT REAL", preview_content)
        self.assertIn("Sample Bangalore Chai Co", preview_content)

        # Confirm production site/ was NOT touched or polluted with fixtures
        for p in SITE_DIR.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".html", ".json", ".xml"}:
                text = p.read_text(encoding="utf-8")
                self.assertNotIn("SAMPLE – NOT REAL", text)
                self.assertNotIn("Sample Bangalore Chai Co", text)

        # 2. Test writing to a custom temporary directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            build_site(use_fixtures=True, output_dir=tmp_path)
            tmp_index = tmp_path / "index.html"
            self.assertTrue(tmp_index.exists())
            tmp_content = tmp_index.read_text(encoding="utf-8")
            self.assertIn("SAMPLE – NOT REAL", tmp_content)


if __name__ == "__main__":
    unittest.main()
