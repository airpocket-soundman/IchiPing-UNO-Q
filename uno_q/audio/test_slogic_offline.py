import csv
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('slogic_converter', Path(__file__).with_name('slogic-sr-to-csv.py'))
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


class SLogicConversionTests(unittest.TestCase):
    def test_preserves_edges_chunk_boundary_and_final_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'test.sr', Path(tmp) / 'test.csv'
            with zipfile.ZipFile(src, 'w') as z:
                z.writestr('metadata', '[device 1]\nunitsize=2\nsamplerate=50 MHz\ncapturefile=logic-1\n' +
                           ''.join(f'probe{i+1}=D{i}\n' for i in range(4)))
                z.writestr('logic-1-1', struct.pack('<4H', 0, 0, 1, 3))
                z.writestr('logic-1-2', struct.pack('<4H', 2, 6, 6, 6))
            result = converter.convert(src, dst)
            with dst.open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(result['samples'], 8)
            self.assertEqual([round(float(r['time_s']) * 50e6) for r in rows], [0, 2, 3, 4, 5, 7])
            self.assertEqual([r['bclk'] for r in rows], ['0', '1', '1', '0', '0', '0'])
            self.assertEqual(rows[-1]['din'], '1')
            with self.assertRaises(FileExistsError):
                converter.convert(src, dst)


if __name__ == '__main__':
    unittest.main()
