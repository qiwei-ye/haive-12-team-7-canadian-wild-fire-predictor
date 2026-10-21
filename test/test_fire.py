"""Small fire fixtures for report dates, area indicators, and CSV schemas."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, data_fire


class FireTests(unittest.TestCase):
    def write_date_reference(self, raw, records):
        path = raw / config.FIRE_DATE_REFERENCE["relative_path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records), encoding="utf-8")
        return path

    def test_nwt_dates_are_corrected_before_filtering_without_replacing_areas_or_locations(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            source = raw / "CWFIS" / "reported_fires_2026_latest.csv"
            source.parent.mkdir(parents=True)
            identifiers = ["2026_NT_SS001-26", "2026_NT_SS002-26", "2026_NT_SS003-26",
                           "2026_NT_SS004-26", "2023_AB_SS001-26", "2026_NT_NO_MATCH"]
            pd.DataFrame({
                "national_fire_id": identifiers, "latitude": [50] * 6, "longitude": [-100] * 6,
                "situation_report_date": ["2026-01-01"] * 3 + ["2026-06-02", "2023-01-01", "2026-01-01"],
                "fire_size": [1000, 0.1, -1, 13, 1100, 5],
            }).to_csv(source, index=False)
            reference = self.write_date_reference(raw, [
                {"title": f"SS00{i}-26", "estimatedstart": start, "discoverydate": discovery,
                 "latitude": 50.00002, "longitude": -99.99998, "currentsize": 0}
                for i, start, discovery in [(1, "2026-07-01T23:30:00", "2026-07-01T23:30:00"),
                                             (2, "2026-09-11T11:00:00", "2026-09-11T11:00:00"),
                                             (3, "2026-07-23T15:09:00", "2026-08-13T15:09:00"),
                                             (4, "2026-07-16T15:00:00", "2026-07-16T15:00:00")]
            ])
            originals = {path: path.read_bytes() for path in (source, reference)}
            with patch.object(config, "FIRE_DATA_DIR", raw), self.assertLogs(level="WARNING"):
                outputs = data_fire.preprocess(root / "processed")
            result = pd.read_csv(outputs[0]).set_index("fire_id")
            self.assertEqual(len(result), 5)
            self.assertNotIn(identifiers[1], result.index)
            self.assertEqual(result.loc[identifiers[0], "report_date"], "2026-07-01")
            self.assertEqual(result.loc[identifiers[0], "size_ha"], 1000)
            self.assertEqual(result.loc[identifiers[0], "is_large_fire"], 1)
            self.assertEqual(result.loc[identifiers[2], "report_date"], "2026-07-23")
            self.assertTrue(pd.isna(result.loc[identifiers[2], "size_ha"]))
            self.assertTrue(pd.isna(result.loc[identifiers[2], "is_large_fire"]))
            self.assertEqual(result.loc[identifiers[3], "report_date"], "2026-06-02")
            self.assertEqual(result.loc[identifiers[4], "report_date"], "2023-01-01")
            self.assertEqual(result.loc[identifiers[5], "report_date"], "2026-01-01")
            self.assertTrue(result.latitude.eq(50).all())
            self.assertTrue(result.longitude.eq(-100).all())
            self.assertEqual(list(outputs[0].parent.iterdir()), outputs)
            for path, expected in originals.items():
                self.assertEqual(path.read_bytes(), expected)

    def test_nwt_reference_validation_rejects_ambiguous_dates_ids_and_coordinates(self):
        valid = {"title": "SS001-26", "estimatedstart": "2026-07-01", "discoverydate": "2026-07-01",
                 "latitude": 50, "longitude": -100}
        records = pd.DataFrame({"fire_id": ["2026_NT_SS001-26"], "report_date": ["2026-01-01"],
                                "latitude": [50], "longitude": [-100], "size_ha": [1000]})
        cases = [([valid, dict(valid)], "duplicate NWT"),
                 ([dict(valid, estimatedstart=False)], "invalid matched NWT"),
                 ([dict(valid, estimatedstart="2026-02-30")], "invalid matched NWT"),
                 ([dict(valid, latitude=51)], "coordinates disagree"),
                 ([{key: value for key, value in valid.items() if key != "estimatedstart"}], "fields are missing")]
        for reference_records, message in cases:
            with self.subTest(message=message), TemporaryDirectory() as directory:
                raw = Path(directory)
                self.write_date_reference(raw, reference_records)
                original = records.copy(deep=True)
                with patch.object(config, "FIRE_DATA_DIR", raw), self.assertRaisesRegex(ValueError, message):
                    data_fire.correct_january_1_dates(records)
                pd.testing.assert_frame_equal(records, original)

    def test_required_nwt_reference_missing_fails_without_creating_processed_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "raw" / "CWFIS" / "reported_fires_2026_latest.csv"
            source.parent.mkdir(parents=True)
            pd.DataFrame({"national_fire_id": ["2026_NT_SS001-26"], "latitude": [50], "longitude": [-100],
                          "situation_report_date": ["2026-01-01"], "fire_size": [1000]}).to_csv(source, index=False)
            with patch.object(config, "FIRE_DATA_DIR", root / "raw"), self.assertRaises(FileNotFoundError):
                data_fire.preprocess(root / "processed")
            self.assertFalse((root / "processed").exists())

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
            "report_date": ["2018-08-31T22:32:00", "2018-09-01T00:00:00", "2023-05-25T18:20:00",
                            "2026-08-31T23:30:00-07:00", "2026-09-01T00:00:00", "", "2026-02-30T01:00:00"],
            "status_date": ["2026-05-27T18:50:00"] * 7, "size_ha": [1000] * 7,
        })
        original = records.copy(deep=True)
        actual = data_fire.standardize_records(records)
        self.assertEqual(actual.report_date.tolist(), ["2018-09-01", "2023-05-25", "2026-08-31"])
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

    def test_cwfis_round_trip_preserves_ids_and_does_not_process_other_sources(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            nfdb = raw / "Canadian National Fire Database" / "NFDB_point_fixture.csv"
            ciffc = raw / "CIFFC" / "ciffc.csv"
            nfdb.parent.mkdir(parents=True)
            ciffc.parent.mkdir(parents=True)
            nfdb.write_text("NFDBFIREID,LATITUDE,LONGITUDE,REP_DATE,SIZE_HA,OUT_DATE\n"
                            "QC-2020-001,50,-100,2020-05-26 0:00:00,1000,2026-10-09\n", encoding="utf-8")
            ciffc.write_text('"unused","QC","2021-05-01","2026-05-01",'
                             '"extinguished","human","full_response","2000","50","-100"\n', encoding="utf-8")
            cwfis = raw / "CWFIS" / "reported_fires_2020_year_end.csv"
            cwfis.parent.mkdir()
            pd.DataFrame({
                "national_fire_id": ["001", "NA", "before", "after"],
                "latitude": [50, 51, 50, 50], "longitude": [-100, -101, -100, -100],
                "situation_report_date": ["2020-09-01T22:32:00", "2026-08-31T00:00:00",
                                          "2018-08-31T00:00:00", "2026-09-01T00:00:00"],
                "status_date": ["2026-10-09T18:50:00"] * 4,
                "fire_size": ["999.9", "-1", "2000", "2000"],
            }).to_csv(cwfis, index=False)
            original = {path: path.read_bytes() for path in (nfdb, ciffc, cwfis)}
            with patch.object(config, "FIRE_DATA_DIR", raw), self.assertLogs(level="WARNING"):
                outputs = data_fire.preprocess(root / "processed")
            self.assertEqual({path.name for path in outputs}, {"cwfis.csv"})
            actual = pd.read_csv(root / "processed" / "fire" / "cwfis.csv", dtype="string", keep_default_na=False)
            self.assertEqual(list(actual.columns), list(config.FIRE_OUTPUT_COLUMNS))
            self.assertEqual(actual.fire_id.tolist(), ["001", "NA"])
            self.assertEqual(actual.report_date.tolist(), ["2020-09-01", "2026-08-31"])
            self.assertEqual(actual.is_large_fire.tolist(), ["0", ""])
            for path, expected in original.items():
                self.assertEqual(path.read_bytes(), expected)

    def test_carryovers_keep_original_date_and_area_before_filtering(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw"
            folder = raw / "CWFIS"
            folder.mkdir(parents=True)
            pd.DataFrame({
                "national_fire_id": ["2020_SK_large", "2020_SK_outside"],
                "latitude": [50, 50], "longitude": [-100, -100],
                "situation_report_date": ["2020-09-01", "2018-08-31"],
                "fire_size": [1500, 2000],
            }).to_csv(folder / "reported_fires_2020_year_end.csv", index=False)
            pd.DataFrame({
                "national_fire_id": ["2020_SK_large", "2020_SK_outside", "2021_SK_new"],
                "latitude": [51, 50, 50], "longitude": [-100, -100, -100],
                "situation_report_date": ["2021-05-31"] * 3,
                "fire_size": [0.1, 0.1, 10],
            }).to_csv(folder / "reported_fires_2021_year_end.csv", index=False)
            with patch.object(config, "FIRE_DATA_DIR", raw):
                outputs = data_fire.preprocess(root / "processed")
            actual = pd.read_csv(outputs[0])
            self.assertEqual(actual.fire_id.tolist(), ["2020_SK_large", "2021_SK_new"])
            self.assertEqual(actual.report_date.tolist(), ["2020-09-01", "2021-05-31"])
            self.assertEqual(actual.size_ha.tolist(), [1500, 10])
            self.assertEqual(actual.is_large_fire.tolist(), [1, 0])
            self.assertEqual(actual.latitude.tolist(), [50, 50])
            self.assertFalse(actual.fire_id.duplicated().any())

    def test_blank_and_duplicate_national_ids_are_rejected_without_output(self):
        for identifiers, message in [(["", "good"], "Missing national"), (["same", "same"], "Duplicate national")]:
            with self.subTest(identifiers=identifiers), TemporaryDirectory() as directory:
                root = Path(directory)
                raw = root / "raw"
                folder = raw / "CWFIS"
                folder.mkdir(parents=True)
                pd.DataFrame({
                    "national_fire_id": identifiers, "latitude": [50, 50], "longitude": [-100, -100],
                    "situation_report_date": ["2021-05-31"] * 2, "fire_size": [10, 2000],
                }).to_csv(folder / "reported_fires_2021_year_end.csv", index=False)
                with patch.object(config, "FIRE_DATA_DIR", raw), self.assertRaisesRegex(ValueError, message):
                    data_fire.preprocess(root / "processed")
                self.assertFalse((root / "processed" / "fire").exists())

    def test_missing_sources_are_reported(self):
        with TemporaryDirectory() as directory:
            with patch.object(config, "FIRE_DATA_DIR", Path(directory)), self.assertLogs(level="WARNING") as logs:
                outputs = data_fire.preprocess(Path(directory) / "processed")
            self.assertEqual(outputs, [])
            self.assertIn("Missing CWFIS fire inputs", " ".join(logs.output))

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
