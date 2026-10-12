import unittest

import pandas as pd

from saa.threshold_analysis import flux_weighted_centroid


class FluxWeightedCentroidTests(unittest.TestCase):
    def test_weights_flux_by_physical_cell_area(self) -> None:
        cells = pd.DataFrame(
            {
                "lat_bin_center": [0.0, 60.0],
                "lon_bin_center": [-60.0, -30.0],
                "mean_flux": [10.0, 10.0],
                "cell_area_km2": [2.0, 1.0],
            }
        )

        lat, lon = flux_weighted_centroid(cells, "mean_flux")

        self.assertAlmostEqual(lat, 20.0)
        self.assertAlmostEqual(lon, -50.0)


if __name__ == "__main__":
    unittest.main()
