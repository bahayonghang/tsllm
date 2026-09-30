"""Validate independent accounting with known repeated URLs and late FCP."""

import unittest

from audit_measurements import Audit, aggregate, stats


class AccountingTests(unittest.TestCase):
    def test_full_urls_keep_queries_and_repeated_transfer(self):
        entries = [
            {
                "name": "http://127.0.0.1:9000/api/x?p=1",
                "encodedBodySize": 20,
                "decodedBodySize": 20,
                "transferSize": 320,
            },
            {
                "name": "http://127.0.0.1:9000/api/x?p=1",
                "encodedBodySize": 25,
                "decodedBodySize": 25,
                "transferSize": 325,
            },
            {
                "name": "http://127.0.0.1:9000/api/x?p=2",
                "encodedBodySize": 10,
                "decodedBodySize": 10,
                "transferSize": 310,
            },
        ]
        result = aggregate(entries)["api"]
        self.assertEqual(result["encoded_body_union"], 35)
        self.assertEqual(result["transfer_bytes"], 955)
        self.assertEqual(result["unique_urls"], 2)
        self.assertEqual(result["request_entries"], 3)

    def test_stats_retain_high_values(self):
        result = stats([1, 4, 3, 2, 900])
        self.assertEqual((result["median"], result["min"], result["max"]), (3, 1, 900))
        self.assertEqual(result["values"], [1, 4, 3, 2, 900])

    def test_late_fcp_does_not_change_ready_duration(self):
        stage = {
            "start": 10,
            "end": 100,
            "duration": 90,
            "timeOrigin": 1,
            "paint": [{"name": "first-contentful-paint", "startTime": 120}],
            "paintAtReady": [],
            "navigation": [],
            "resources": [],
            "paintCollection": {
                "readyEndpoint": 100,
                "timeoutMs": 1000,
                "scope": "document",
                "startedAt": 101,
                "collectedAt": 124,
                "waitMs": 23,
                "status": "observed",
            },
        }
        audit = Audit()
        audit.snapshot(stage, "late-fcp")
        self.assertEqual(audit.failures, [])
        self.assertTrue(audit.paint[0]["fcp_after_ready"])
        stage["duration"] = 113
        audit.snapshot(stage, "invalid-endpoint")
        self.assertIn("invalid-endpoint duration", audit.failures)


if __name__ == "__main__":
    unittest.main()
