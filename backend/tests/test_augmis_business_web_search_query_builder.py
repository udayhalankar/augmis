from __future__ import annotations

import unittest

from app.services.augmis_business_web_search_query_builder import build_web_search_queries


class AugmisBusinessWebSearchQueryBuilderTest(unittest.TestCase):
    def test_builds_bounded_queries_from_profile(self):
        queries = build_web_search_queries(
            profile={
                "include_keywords_json": ["workflow automation", "dashboard"],
                "include_technologies_json": ["React", "FastAPI"],
                "include_capabilities_json": ["records management"],
                "target_countries_json": ["Kenya", "Germany"],
                "target_regions_json": [],
            },
            maximum_queries=6,
        )
        self.assertLessEqual(len(queries), 6)
        self.assertTrue(any("workflow" in query.lower() for query in queries))
        self.assertTrue(any("kenya" in query.lower() or "germany" in query.lower() for query in queries))

    def test_global_profile_works_without_geography(self):
        queries = build_web_search_queries(
            profile={
                "include_keywords_json": ["custom software"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "target_countries_json": [],
                "target_regions_json": [],
            },
            maximum_queries=5,
        )
        self.assertGreaterEqual(len(queries), 1)
        self.assertFalse(any("kenya" in query.lower() for query in queries))

    def test_near_duplicate_queries_are_removed(self):
        queries = build_web_search_queries(
            profile={
                "include_keywords_json": ["workflow automation", "workflow automation", "workflow   automation"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "target_countries_json": [],
                "target_regions_json": [],
            },
            maximum_queries=10,
        )
        self.assertEqual(len(queries), len(set(queries)))


if __name__ == "__main__":
    unittest.main()
