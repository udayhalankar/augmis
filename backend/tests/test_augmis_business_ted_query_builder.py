from __future__ import annotations

import unittest
from datetime import datetime, timezone

from app.services.augmis_business_ted_query_builder import (
    build_ted_search_query,
    build_ted_search_query_specs,
    build_ted_search_query_variants,
    ted_country_scope_codes,
)


class TedQueryBuilderTest(unittest.TestCase):
    def test_query_specs_omit_country_clause_for_all_eu_eea_scope(self):
        specs = build_ted_search_query_specs(
            profile={
                "target_countries_json": [],
                "include_keywords_json": ["workflow", "analytics", "document management", "integration", "inspection"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "target_industries_json": [],
                "exclude_keywords_json": [],
            },
            configuration={
                "lookback_days": 30,
                "country_scope_mode": "eu_eea",
                "notice_type_mode": "all_supported",
                "cpv_scope": "broad_software_services",
            },
            now=datetime(2026, 8, 8, tzinfo=timezone.utc),
        )
        self.assertTrue(specs)
        for spec in specs:
            self.assertNotIn("buyer-country IN", spec.query)
            self.assertNotIn("place-of-performance IN", spec.query)
            self.assertNotIn("notice-type IN", spec.query)

    def test_selected_country_scope_uses_tenant_selection(self):
        codes = ted_country_scope_codes(
            profile={"target_countries_json": ["Germany"]},
            configuration={"country_scope_mode": "selected", "selected_countries_json": ["Spain", "Portugal"]},
        )
        self.assertEqual(codes, ["ESP", "PRT"])

    def test_multiple_business_terms_become_multiple_query_groups(self):
        specs = build_ted_search_query_specs(
            profile={
                "target_countries_json": [],
                "target_industries_json": [],
                "include_keywords_json": ["workflow", "analytics", "document management", "inspection"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "exclude_keywords_json": [],
            },
            configuration={
                "lookback_days": 30,
                "country_scope_mode": "eu_eea",
                "notice_type_mode": "all_supported",
                "cpv_scope": "broad_software_services",
            },
            now=datetime(2026, 8, 8, tzinfo=timezone.utc),
        )
        queries = [spec.query for spec in specs]
        self.assertGreaterEqual(len(queries), 4)
        self.assertTrue(any("FT ~ (workflow)" in query for query in queries))
        self.assertTrue(any("FT ~ (analytics)" in query for query in queries))
        self.assertTrue(any('FT ~ ("document management")' in query for query in queries))
        self.assertTrue(any("FT ~ (inspection)" in query for query in queries))

    def test_query_uses_valid_cpv_grouping(self):
        query = build_ted_search_query(
            profile={
                "target_countries_json": [],
                "target_industries_json": [],
                "include_keywords_json": ["workflow"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "exclude_keywords_json": [],
            },
            configuration={
                "lookback_days": 30,
                "country_scope_mode": "search_profile",
                "notice_type_mode": "competition_only",
                "cpv_scope": "broad_software_services",
            },
            now=datetime(2026, 8, 8, tzinfo=timezone.utc),
        )
        self.assertIn("classification-cpv IN (48810000 72222300 72230000 72262000 72513000)", query)
        self.assertIn("notice-type IN (cn-standard cn-social cn-desg subco pin-cfc-standard pin-cfc-social qu-sy)", query)

    def test_30_day_lookback_is_generated_correctly(self):
        query = build_ted_search_query(
            profile={
                "target_countries_json": [],
                "target_industries_json": [],
                "include_keywords_json": ["workflow"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "exclude_keywords_json": [],
            },
            configuration={
                "lookback_days": 30,
                "country_scope_mode": "search_profile",
                "notice_type_mode": "all_supported",
                "cpv_scope": "broad_software_services",
            },
            now=datetime(2026, 8, 8, tzinfo=timezone.utc),
        )
        self.assertIn("publication-date = (20260709 <> 20260808)", query)

    def test_90_day_lookback_is_generated_correctly(self):
        query = build_ted_search_query(
            profile={
                "target_countries_json": [],
                "target_industries_json": [],
                "include_keywords_json": ["workflow"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "exclude_keywords_json": [],
            },
            configuration={
                "lookback_days": 90,
                "country_scope_mode": "search_profile",
                "notice_type_mode": "all_supported",
                "cpv_scope": "broad_software_services",
            },
            now=datetime(2026, 8, 8, tzinfo=timezone.utc),
        )
        self.assertIn("publication-date = (20260510 <> 20260808)", query)

    def test_exclusion_terms_are_applied_separately(self):
        variants = build_ted_search_query_variants(
            profile={
                "target_countries_json": [],
                "target_industries_json": [],
                "include_keywords_json": ["workflow"],
                "include_technologies_json": [],
                "include_capabilities_json": [],
                "exclude_keywords_json": ["jobs", "recruitment"],
            },
            configuration={
                "lookback_days": 30,
                "country_scope_mode": "search_profile",
                "notice_type_mode": "all_supported",
                "cpv_scope": "broad_software_services",
            },
            now=datetime(2026, 8, 8, tzinfo=timezone.utc),
        )
        self.assertTrue(variants)
        self.assertTrue(all("FT !~ (jobs recruitment)" in query for query in variants))


if __name__ == "__main__":
    unittest.main()
