"""Pipeline tree-training dispatch and CLI checks; models are mocked throughout."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_pipeline
from src import config


class TreePipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inputs = self.root / config.CLEAN_MERGED_FILENAME
        self.inputs.touch()  # Dispatch tests never read the mocked NetCDF.

    def test_train_defaults_to_both_models_in_order_with_configured_paths(self):
        forest, boosting = Mock(), Mock()
        order = Mock()
        order.attach_mock(forest.run_classifier, "randomforest")
        order.attach_mock(boosting.run_classifier, "xgboost")
        with patch.object(config, "INPUT_DATA_DIR", self.root), \
                patch.object(run_pipeline.importlib, "import_module", side_effect=[forest, boosting]) as loader:
            self.assertEqual(run_pipeline.main(["train"]), 0)
        self.assertEqual(loader.call_args_list, [call("src.randomforest"), call("src.xgboost")])
        self.assertEqual(order.mock_calls, [
            call.randomforest(input_path=self.inputs, output_dir=config.RANDOM_FOREST_OUTPUTS_DIR),
            call.xgboost(input_path=self.inputs, output_dir=config.XGBOOST_OUTPUTS_DIR),
        ])

    def test_single_model_honours_input_and_parent_output_override(self):
        for name in ("randomforest", "xgboost"):
            with self.subTest(model=name), patch.object(run_pipeline.importlib, "import_module") as loader:
                module = loader.return_value
                output = self.root / "outputs"
                self.assertEqual(run_pipeline.main([
                    "train", "--model", name, "--input", str(self.inputs), "--output-dir", str(output),
                ]), 0)
                loader.assert_called_once_with(f"src.{name}")
                module.run_classifier.assert_called_once_with(input_path=self.inputs, output_dir=output / name)
        self.assertFalse((self.root / "outputs").exists())

    def test_missing_input_fails_before_importing_or_starting_models(self):
        with patch.object(run_pipeline.importlib, "import_module") as loader, \
                self.assertLogs("run_pipeline", level="ERROR") as messages:
            self.assertEqual(run_pipeline.main(["train", "--input", str(self.root / "missing.nc")]), 1)
        loader.assert_not_called()
        self.assertIn("src.variable_selection", " ".join(messages.output))

    def test_first_model_failure_stops_before_second_ensemble(self):
        forest = Mock()
        forest.run_classifier.side_effect = ValueError("invalid selected data")
        with patch.object(run_pipeline.importlib, "import_module", return_value=forest) as loader, \
                self.assertLogs("run_pipeline", level="ERROR") as messages:
            self.assertEqual(run_pipeline.main(["train", "--input", str(self.inputs)]), 1)
        loader.assert_called_once_with("src.randomforest")
        self.assertIn("randomforest training failed", " ".join(messages.output))

    def test_second_model_failure_returns_nonzero_after_first_model_finishes(self):
        forest, boosting = Mock(), Mock()
        boosting.run_classifier.side_effect = OSError("output unavailable")
        with patch.object(run_pipeline.importlib, "import_module", side_effect=[forest, boosting]) as loader, \
                self.assertLogs("run_pipeline", level="ERROR"):
            self.assertEqual(run_pipeline.main(["train", "--input", str(self.inputs)]), 1)
        self.assertEqual(loader.call_count, 2)
        forest.run_classifier.assert_called_once()
        boosting.run_classifier.assert_called_once()

    def test_model_import_failure_returns_nonzero_without_fitting(self):
        with patch.object(run_pipeline.importlib, "import_module", side_effect=ImportError("missing dependency")), \
                self.assertLogs("run_pipeline", level="ERROR") as messages:
            self.assertEqual(run_pipeline.main(["train", "--input", str(self.inputs)]), 1)
        self.assertIn("missing dependency", " ".join(messages.output))

    def test_training_cannot_write_inside_any_source_data_directory(self):
        for directory in (config.RAW_DATA_DIR, config.PROCESSED_DATA_DIR, config.CLEAN_DATA_DIR, config.INPUT_DATA_DIR):
            with self.subTest(directory=directory), \
                    patch.object(run_pipeline.importlib, "import_module") as loader, redirect_stderr(StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    run_pipeline.main(["train", "--input", str(self.inputs), "--output-dir", str(directory / "models")])
                self.assertEqual(raised.exception.code, 2)
                loader.assert_not_called()

    def test_help_and_no_command_never_import_models(self):
        with patch.object(run_pipeline.importlib, "import_module") as loader:
            text = StringIO()
            with redirect_stdout(text):
                self.assertEqual(run_pipeline.main([]), 0)
            self.assertIn("train", text.getvalue())
            for window in config.TIME_WINDOWS.values():
                self.assertIn(window[0], text.getvalue())
                self.assertIn(window[1], text.getvalue())
            with redirect_stdout(StringIO()), self.assertRaises(SystemExit) as raised:
                run_pipeline.main(["train", "--help"])
            self.assertEqual(raised.exception.code, 0)
            loader.assert_not_called()

    def test_training_help_runs_outside_project_without_model_imports(self):
        result = subprocess.run(
            [sys.executable, "-B", str(config.PROJECT_ROOT / "run_pipeline.py"), "train", "--help"],
            cwd=self.root, capture_output=True, text=True, timeout=30, check=False,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        for option in ("--model", "randomforest", "xgboost", "--input", "--output-dir"):
            self.assertIn(option, result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
