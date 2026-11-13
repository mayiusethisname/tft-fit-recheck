"""read_raw 확인. 원자료 없이, 여기서 직접 만든 작은 파일로 돌린다."""
import tempfile
import unittest
from pathlib import Path

from recheck import read_raw

DAT = (
    "DATA:  HIGHTRANS  04/08/2020  13:49:07\r\n\r\nVG\tID\r\n1.0E+000\t9.0E-009\r\n"
    "DATA:  MOBILITY  04/08/2020  13:50:05\r\n\r\nVD\tID\tS\tACCSTRESS\r\n"
    "0.00000000E+000\t2.00000000E-014\t*\t0.00000000E+000\r\n"
    "-1.00000000E-001\t-1.10000000E-013\t*\t*\r\n\r\n"
)
CSV = (
    "DATA:  MOBILITY  02/14/2022  21:16:50,,,\n,,,\nVD,ID,,\n-2,-2.93E-08,,\n-1.9,2.63E-08,,\n"
    "DATA:  HYSTERESIS  12/31/2021  21:17:28,,,\n,,,\nVG,ID,,\n5,1E-3,,\n"
)


class ReadRawTest(unittest.TestCase):
    def write(self, name, text):
        path = Path(self.dir.name) / name
        path.write_bytes(text.encode("ascii"))
        return path

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_dat_keeps_sign_and_stops_at_section_end(self):
        pts = read_raw.mobility_points(self.write("LTPS1002.DAT", DAT))
        self.assertEqual(pts, [(0.0, 2e-14), (-0.1, -1.1e-13)])

    def test_csv_reads_only_mobility(self):
        pts = read_raw.mobility_points(self.write("IGZO2004.csv", CSV))
        self.assertEqual(pts, [(-2.0, -2.93e-08), (-1.9, 2.63e-08)])

    def test_unreadable_number_stops(self):
        bad = CSV.replace("-1.9,2.63E-08", "-1.9,*")
        with self.assertRaises(ValueError):
            read_raw.mobility_points(self.write("IGZO2004.csv", bad))

    def test_missing_section_stops(self):
        with self.assertRaises(ValueError):
            read_raw.read_section(self.write("aSi2002.DAT", DAT), "OUTPUT_2")

    def test_device_from_name(self):
        self.assertEqual(read_raw.device("IGZO2004.csv"), ("IGZO", 20, 4))
        self.assertEqual(read_raw.device("LTPS1005.DAT"), ("LTPS", 10, 5))
        self.assertEqual(read_raw.device("aSi2020.DAT"), ("aSi", 20, 20))


if __name__ == "__main__":
    unittest.main()
