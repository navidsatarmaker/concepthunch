import unittest
from pathlib import Path
from build_site import build_site, SITE_DIR, FIXTURES_DIR


class TestFixtureIsolation(unittest.TestCase):
    def test_production_build_excludes_fixtures(self):
        build_site(use_fixtures=False)
        for html_file in SITE_DIR.rglob("*.html"):
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertNotIn("SAMPLE – NOT REAL", content)
                self.assertNotIn("Sample Bangalore Chai Co", content)

    def test_fixture_flag_includes_fixtures_with_banner(self):
        build_site(use_fixtures=True)
        index_html = SITE_DIR / "index.html"
        self.assertTrue(index_html.exists())
        with open(index_html, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("SAMPLE – NOT REAL", content)
            self.assertIn("Sample Bangalore Chai Co", content)

        # Reset back to clean state
        build_site(use_fixtures=False)


if __name__ == "__main__":
    unittest.main()
