import contextlib
import io
import json
import os
import tempfile
from unittest import TestCase

from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from csv2json.csv2json import Csv2json


def make_ds(rows=1000, cols=500, **tags):
    ds = Dataset()
    if rows is not None:
        ds.Rows = rows
    if cols is not None:
        ds.Columns = cols
    for k, v in tags.items():
        setattr(ds, k, v)
    return ds


def quiet(func, *args, **kwargs):
    """Run func, returning (result, captured stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = func(*args, **kwargs)
    return result, buf.getvalue()


class GetDimensionsTests(TestCase):
    """Tests for Csv2json.get_dimensions()."""

    def dims(self, ds):
        return quiet(Csv2json.get_dimensions, ds, "test-key")[0]

    def test_field_of_view_preferred(self):
        ds = make_ds(FieldOfViewDimensions=[430, 350], PixelSpacing=[0.1, 0.1])
        self.assertEqual(self.dims(ds), (430, 350))

    def test_pixel_spacing(self):
        ds = make_ds(PixelSpacing=[0.2, 0.2])
        self.assertEqual(self.dims(ds), (200, 100))

    def test_imager_pixel_spacing_fallback(self):
        # The case from the bug report: no FOV, no PixelSpacing (typical CR/DX)
        ds = make_ds(ImagerPixelSpacing=[0.15, 0.15])
        self.assertEqual(self.dims(ds), (150, 75))

    def test_nominal_scanned_pixel_spacing_fallback(self):
        ds = make_ds(NominalScannedPixelSpacing=[0.3, 0.3])
        self.assertEqual(self.dims(ds), (300, 150))

    def test_pixel_spacing_beats_imager_pixel_spacing(self):
        ds = make_ds(PixelSpacing=[0.2, 0.2], ImagerPixelSpacing=[0.15, 0.15])
        self.assertEqual(self.dims(ds), (200, 100))

    def test_non_square_pixels_use_column_spacing_for_width(self):
        # Regression: width used spacing[0] instead of spacing[1]
        ds = make_ds(PixelSpacing=[0.2, 0.4])
        self.assertEqual(self.dims(ds), (200, 200))

    def test_both_branches_return_ints(self):
        for ds in (make_ds(FieldOfViewDimensions=[430, 350]),
                   make_ds(PixelSpacing=[0.2, 0.2]),
                   make_ds(ImagerPixelSpacing=[0.15, 0.15]),
                   make_ds()):
            h, w = self.dims(ds)
            self.assertIsInstance(h, int)
            self.assertIsInstance(w, int)

    # --- ImagerPixelSpacing magnification ---

    def test_imager_pixel_spacing_divided_by_magnification(self):
        ds = make_ds(ImagerPixelSpacing=[0.15, 0.15],
                     EstimatedRadiographicMagnificationFactor=1.25)
        (h, w), out = quiet(Csv2json.get_dimensions, ds, "test-key")
        self.assertEqual((h, w), (120, 60))
        self.assertNotIn("EstimatedRadiographicMagnificationFactor does not exist", out)

    def test_imager_pixel_spacing_without_magnification_warns(self):
        ds = make_ds(ImagerPixelSpacing=[0.15, 0.15])
        (h, w), out = quiet(Csv2json.get_dimensions, ds, "test-key")
        self.assertEqual((h, w), (150, 75))
        self.assertIn("EstimatedRadiographicMagnificationFactor does not exist", out)

    def test_magnification_not_applied_to_pixel_spacing(self):
        # PixelSpacing is already patient-plane
        ds = make_ds(PixelSpacing=[0.2, 0.2],
                     EstimatedRadiographicMagnificationFactor=1.25)
        self.assertEqual(self.dims(ds), (200, 100))

    def test_zero_magnification_ignored_with_warning(self):
        ds = make_ds(ImagerPixelSpacing=[0.15, 0.15],
                     EstimatedRadiographicMagnificationFactor=0)
        (h, w), out = quiet(Csv2json.get_dimensions, ds, "test-key")
        self.assertEqual((h, w), (150, 75))
        self.assertIn("EstimatedRadiographicMagnificationFactor does not exist", out)

    # --- Malformed and missing values ---

    def test_no_size_info_returns_zero(self):
        self.assertEqual(self.dims(make_ds()), (0, 0))

    def test_spacing_without_rows_columns_returns_zero(self):
        ds = make_ds(rows=None, cols=None, PixelSpacing=[0.2, 0.2])
        self.assertEqual(self.dims(ds), (0, 0))

    def test_single_value_spacing_is_skipped(self):
        ds = make_ds(PixelSpacing=[0.2], ImagerPixelSpacing=[0.15, 0.15])
        self.assertEqual(self.dims(ds), (150, 75))

    def test_single_value_fov_falls_back_to_spacing(self):
        ds = make_ds(FieldOfViewDimensions=430, PixelSpacing=[0.2, 0.2])
        self.assertEqual(self.dims(ds), (200, 100))

    def test_empty_element_in_spacing_is_skipped(self):
        # e.g. PixelSpacing stored as "0.2\" -> second value is empty
        ds = make_ds(PixelSpacing=["0.2", ""], ImagerPixelSpacing=[0.15, 0.15])
        self.assertEqual(self.dims(ds), (150, 75))

    def test_zero_spacing_does_not_override_fallback(self):
        ds = make_ds(PixelSpacing=[0, 0], ImagerPixelSpacing=[0.15, 0.15])
        self.assertEqual(self.dims(ds), (150, 75))

    def test_zero_fov_falls_back_to_spacing(self):
        ds = make_ds(FieldOfViewDimensions=[0, 0], PixelSpacing=[0.2, 0.2])
        self.assertEqual(self.dims(ds), (200, 100))


class MakeJsonTests(TestCase):
    """End-to-end tests for Csv2json.make_json() with real DICOM files."""

    LANDMARKS = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0,
                 70.0, 80.0, 90.0, 100.0, 110.0, 120.0]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.app = Csv2json()

    def tearDown(self):
        self.tmp.cleanup()

    def write_dicom(self, name, **tags):
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.1.1"  # DX
        meta.MediaStorageSOPInstanceUID = generate_uid()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = make_ds(**tags)
        ds.file_meta = meta
        ds.SOPClassUID = meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
        ds.PatientName = "Test^Patient"
        path = os.path.join(self.dir, name)
        try:
            ds.save_as(path, enforce_file_format=True)  # pydicom >= 3.0
        except TypeError:
            # pydicom 2.x
            ds.is_little_endian = True
            ds.is_implicit_VR = False
            ds.save_as(path, write_like_original=False)
        return path

    def run_make_json(self, keys, dcm_files, tags=("PatientName",)):
        csv_path = os.path.join(self.dir, "landmarks.csv")
        json_path = os.path.join(self.dir, "out.json")
        with open(csv_path, "w") as f:
            for key in keys:
                f.write(",".join([key] + [str(v) for v in self.LANDMARKS]) + "\n")
        _, out = quiet(self.app.make_json, csv_path, json_path,
                       dcm_files, list(tags), [])
        with open(json_path) as f:
            return json.load(f), out

    def test_imager_pixel_spacing_file_no_longer_crashes(self):
        dcm = self.write_dicom("img001.dcm", ImagerPixelSpacing=[0.15, 0.15],
                               EstimatedRadiographicMagnificationFactor=1.25)
        data, _ = self.run_make_json(["img001"], [dcm])
        entry = data["img001"]
        self.assertEqual(entry["origHeight"], 120)
        self.assertEqual(entry["origWidth"], 60)
        self.assertEqual(entry["unit"], "mm")
        self.assertEqual(entry["info"]["PatientName"], "Test^Patient")
        self.assertEqual(entry["landmarks"][0],
                         {"leftFemurHead": {"x": 10.0, "y": 20.0}})

    def test_no_matching_dicom_warns_explicitly(self):
        dcm = self.write_dicom("img001.dcm", PixelSpacing=[0.2, 0.2])
        data, out = self.run_make_json(["img001", "missing"], [dcm])
        self.assertIn("WARNING: no DICOM found for missing.", out)
        self.assertNotIn("No dimension or pixel spacing information for missing", out)
        self.assertEqual(data["missing"]["origHeight"], 0)
        self.assertEqual(data["missing"]["origWidth"], 0)
        # the matched row is unaffected
        self.assertEqual(data["img001"]["origHeight"], 200)

    def test_file_without_size_info_still_produces_json(self):
        dcm = self.write_dicom("img002.dcm")
        data, out = self.run_make_json(["img002"], [dcm])
        self.assertEqual(data["img002"]["origHeight"], 0)
        self.assertIn("No dimension or pixel spacing information for img002", out)
