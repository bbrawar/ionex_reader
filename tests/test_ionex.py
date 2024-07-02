import unittest
from ionex_reader.ionex import get_tecmaps, create_xarray

class TestIonexReader(unittest.TestCase):

    def test_create_xarray(self):
        tecmaps = [np.random.rand(180, 360) for _ in range(5)]
        epochs = [datetime(2020, 1, 1) for _ in range(5)]
        ds = create_xarray(tecmaps, epochs)
        self.assertEqual(ds.dims['time'], 5)
        self.assertEqual(ds.dims['latitude'], 180)
        self.assertEqual(ds.dims['longitude'], 360)

if __name__ == '__main__':
    unittest.main()
