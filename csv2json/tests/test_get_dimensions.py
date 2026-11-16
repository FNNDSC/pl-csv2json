from unittest import TestCase

from pydicom.dataset import Dataset

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


class GetDimensionsTests(TestCase):
    """Tests for Csv2json.get_dimensions()."""

    def dims(self, ds):
        return Csv2json.get_dimensions(ds, "test-key")

    def test_field_of_view_preferred(self):
        ds = make_ds(FieldOfViewDimensions=[430, 350], PixelSpacing=[0.1, 0.1])
        self.assertEqual(self.dims(ds), (430.0, 350.0))

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

    def test_single_value_fov_falls_back_to_spacing(self):
        ds = make_ds(FieldOfViewDimensions=430, PixelSpacing=[0.2, 0.2])
        self.assertEqual(self.dims(ds), (200, 100))

    def test_no_size_info_returns_zero(self):
        self.assertEqual(self.dims(make_ds()), (0, 0))

    def test_spacing_without_rows_columns_returns_zero(self):
        ds = make_ds(rows=None, cols=None, PixelSpacing=[0.2, 0.2])
        self.assertEqual(self.dims(ds), (0, 0))

    def test_malformed_single_value_spacing_is_skipped(self):
        ds = make_ds(PixelSpacing=[0.2], ImagerPixelSpacing=[0.15, 0.15])
        self.assertEqual(self.dims(ds), (150, 75))

    def test_result_works_with_int_cast_in_make_json(self):
        # make_json does int(height), int(width)
        for ds in (make_ds(FieldOfViewDimensions=[430, 350]),
                   make_ds(ImagerPixelSpacing=[0.15, 0.15]),
                   make_ds()):
            h, w = self.dims(ds)
            int(h), int(w)
