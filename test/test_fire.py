"""Small fire fixtures for report dates, area indicators, and CSV schemas."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, data_fire


class FireTests(unittest.TestCase):
    def test_configured_cell_exclusions_preserve_other_and_unknown_locations(self):
        from src.preprocessing import cell_ids
        identifier = int(cell_ids([50.2], [-99.8])[0])
        records = pd.DataFrame({
            "fire_id": ["excluded", "retained", "unknown"],
            "latitude": [50.2, 51.2, None], "longitude": [-99.8, -98.8, None],
            "report_date": [config.TEST_END_DATE] * 3, "size_ha": [1000] * 3,
        })
        with patch.object(config, "EXCLUDED_CELL_IDS", (identifier,)):
            result = data_fire.standardize_records(records)
        self.assertEqual(result.fire_id.tolist(), ["retained", "unknown"])
        self.assertTrue(pd.isna(result.latitude.iloc[-1]))

    def test_threshold_is_inclusive_and_missing_area_stays_unknown(self):
        records = pd.DataFrame({
            "fire_id": ["001", "NA", "003", "004", "005", "006", "007"],
            "latitude": [50] * 7, "longitude": [-100] * 7,
            "report_date": [config.TIME_WINDOWS["testing"][1] + "T12:30:00"] * 7,
            "size_ha": ["999.9", "1000", "1000.1", "0", "-1", "", "inf"],
        })
        actual = data_fire.standardize_records(records)
        self.assertEqual(list(actual.columns), list(config.FIRE_OUTPUT_COLUMNS))
        self.assertEqual(actual.is_large_fire.iloc[:4].tolist(), [0, 1, 1, 0])
        self.assertTrue(actual.is_large_fire.iloc[4:].isna().all())
        self.assertTrue(actual.size_ha.iloc[4:].isna().all())
        self.assertEqual(actual.fire_id.iloc[:2].tolist(), ["001", "NA"])

    def test_inclusive_date_filter_uses_report_dates_without_status_substitution(self):
        records = pd.DataFrame({
            "fire_id": ["same"] * 7, "latitude": [50] * 7, "longitude": [-100] * 7,
            "report_date": ["2020-08-31T22:32:00", "2020-09-01T00:00:00", "2023-05-25T18:20:00",
                            "2026-08-31T23:30:00-07:00", "2026-09-01T00:00:00", "", "2026-02-30T01:00:00"],
            "status_date": ["2026-05-27T18:50:00"] * 7, "size_ha": [1000] * 7,
        })
        original = records.copy(deep=True)
        actual = data_fire.standardize_records(records)
        self.assertEqual(actual.report_date.tolist(), ["2020-09-01", "2023-05-25", "2026-08-31"])
        self.assertNotIn("status_date", actual)
        self.assertEqual(actual.fire_id.tolist(), ["same"] * 3)
        pd.testing.assert_frame_equal(records, original)

    def test_invalid_coordinates_are_missing_without_guessing_locations(self):
        records = pd.DataFrame({"fire_id": ["1", "2"], "latitude": ["-115.667", "50"],
                                "longitude": ["-5617700", "-100"], "report_date": ["2026-08-31"] * 2,
                                "size_ha": [1000, 1000]})
        actual = data_fire.standardize_records(records)
        self.assertTrue(pd.isna(actual.latitude.iloc[0]))
        self.assertTrue(pd.isna(actual.longitude.iloc[0]))
        self.assertEqual(actual.latitude.iloc[1], 50)

    def test_ciffc_round_trip_filters_dates_preserves_ids_and_does_not_process_nfdb(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            nfdb = raw / "Canadian National Fire Database" / "NFDB_point_fixture.csv"
            ciffc = raw / "CIFFC" / "ciffc.csv"
            nfdb.parent.mkdir(parents=True)
            ciffc.parent.mkdir(parents=True)
            nfdb.write_text("NFDBFIREID,LATITUDE,LONGITUDE,REP_DATE,SIZE_HA,OUT_DATE\n"
                            "QC-2020-001,50,-100,2020-05-26 0:00:00,1000,2026-10-09\n", encoding="utf-8")
            ciffc.write_text('"001","QC","2020-09-01T22:32:00","2026-05-27T18:50:00",'
                             '"under_control","human","full_response","999.9","50","-100"\n'
                             '"NA","ON","2026-08-31T00:00:00","2026-10-09T18:50:00",'
                             '"extinguished","natural","full_response","-1","51","-101"\n'
                             '"before","QC","2020-08-31T00:00:00","2026-05-27T18:50:00",'
                             '"under_control","human","full_response","2000","50","-100"\n'
                             '"after","QC","2026-09-01T00:00:00","2026-08-31T18:50:00",'
                             '"under_control","human","full_response","2000","50","-100"\n', encoding="utf-8")
            original = {path: path.read_bytes() for path in (nfdb, ciffc)}
            with patch.object(config, "FIRE_DATA_DIR", raw), self.assertLogs(level="WARNING"):
                outputs = data_fire.preprocess(root / "processed")
            self.assertEqual({path.name for path in outputs}, {ciffc.name})
            actual = pd.read_csv(root / "processed" / "fire" / "ciffc.csv", dtype="string", keep_default_na=False)
            self.assertEqual(list(actual.columns), list(config.FIRE_OUTPUT_COLUMNS))
            self.assertEqual(actual.fire_id.tolist(), ["001", "NA"])
            self.assertEqual(actual.report_date.tolist(), ["2020-09-01", "2026-08-31"])
            self.assertEqual(actual.is_large_fire.tolist(), ["0", ""])
            for path, expected in original.items():
                self.assertEqual(path.read_bytes(), expected)

    def test_missing_sources_are_reported(self):
        with TemporaryDirectory() as directory:
            with patch.object(config, "FIRE_DATA_DIR", Path(directory)), self.assertLogs(level="WARNING") as logs:
                outputs = data_fire.preprocess(Path(directory) / "processed")
            self.assertEqual(outputs, [])
            self.assertIn("Missing CIFFC fire inputs", " ".join(logs.output))

    def test_cli_fire_stage_does_not_require_boundaries_or_run_predictors(self):
        from run_pipeline import main
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(data_fire, "preprocess", return_value=[]) as stage:
                result = main(["preprocess", "--only", "fire", "--boundary", str(root / "missing.shp"),
                               "--output-dir", str(root / "processed")])
            self.assertEqual(result, 0)
            stage.assert_called_once_with(root / "processed")
            self.assertFalse((root / "processed" / "grid.nc").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
