from __future__ import annotations

import unittest

from app.services.augmis_business_source_content_service import normalize_source_content


class AugmisBusinessSourceContentServiceTest(unittest.TestCase):
    def test_html_source_is_sanitized(self):
        result = normalize_source_content("<p><strong>Hello</strong> world</p>")
        self.assertEqual(result["detected_format"], "html")
        self.assertIn("<p>", result["safe_html"])
        self.assertIn("<strong>", result["safe_html"])
        self.assertEqual(result["plain_text"], "Hello world")

    def test_script_removed(self):
        result = normalize_source_content("<p>Alpha</p><script>alert(1)</script><p>Beta</p>")
        self.assertNotIn("script", result["safe_html"])
        self.assertEqual(result["plain_text"], "Alpha\n\nBeta")

    def test_event_handler_removed(self):
        result = normalize_source_content('<p onclick="alert(1)">Alpha</p><img src=x onerror=alert(1)>')
        self.assertNotIn("onclick", result["safe_html"])
        self.assertNotIn("onerror", result["safe_html"])
        self.assertEqual(result["plain_text"], "Alpha")

    def test_javascript_url_removed(self):
        result = normalize_source_content('<a href="javascript:alert(1)">Click</a>')
        self.assertNotIn("javascript:", result["safe_html"])
        self.assertNotIn("<a ", result["safe_html"])
        self.assertEqual(result["plain_text"], "Click")

    def test_safe_paragraphs_preserved(self):
        result = normalize_source_content("<p>First</p><p>Second</p>")
        self.assertEqual(result["plain_text"], "First\n\nSecond")
        self.assertIn("<p>", result["safe_html"])

    def test_lists_preserved(self):
        result = normalize_source_content(
            "<p><strong>Responsibilities</strong></p><ul><li>Develop APIs</li><li>Build dashboards</li></ul>"
        )
        self.assertIn("Responsibilities", result["plain_text"])
        self.assertIn("• Develop APIs", result["plain_text"])
        self.assertIn("<ul>", result["safe_html"])
        self.assertIn("<li>", result["safe_html"])

    def test_plain_text_generated(self):
        result = normalize_source_content("Line one\n\nLine two")
        self.assertEqual(result["detected_format"], "text")
        self.assertEqual(result["plain_text"], "Line one\n\nLine two")
        self.assertEqual(result["safe_html"], "<p>Line one</p><p>Line two</p>")

    def test_html_entities_decoded(self):
        result = normalize_source_content("<p>Fish &amp; Chips&nbsp;&lt;test&gt;</p>")
        self.assertEqual(result["plain_text"], "Fish & Chips <test>")
        self.assertIn("Fish &amp; Chips &lt;test&gt;", result["safe_html"])


if __name__ == "__main__":
    unittest.main()
