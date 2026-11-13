"""fit 확인. 답을 손으로 알 수 있는 예제만 쓴다."""
import statistics
import unittest

from recheck import fit


class FitTest(unittest.TestCase):
    def test_exact_line(self):
        # y = 2x + 1 위의 점이면 기울기 2, 절편 1, R² 1이 나와야 한다.
        a, b, r2 = fit.line_fit([0, 1, 2, 3], [1, 3, 5, 7])
        self.assertAlmostEqual(a, 2)
        self.assertAlmostEqual(b, 1)
        self.assertAlmostEqual(r2, 1)

    def test_same_as_standard_library(self):
        # 직접 쓴 식이 파이썬에 들어 있는 직선 맞춤과 같은 답을 내는지 본다.
        xs, ys = [0, 1, 2, 3, 4], [0.1, 0.9, 2.3, 2.8, 4.2]
        a, b, _ = fit.line_fit(xs, ys)
        ref = statistics.linear_regression(xs, ys)
        self.assertAlmostEqual(a, ref.slope)
        self.assertAlmostEqual(b, ref.intercept)

    def made_device(self, sign):
        # μ = 10, Vth = 2 V, W/L = 20/4 인 소자를 식으로 만든다. sign=-1 이면 음전압 소자.
        k = 10 * fit.C_OX * 20 / (2 * 4)
        return [(sign * v / 10, sign * k * (v / 10 - 2) ** 2) for v in range(30, 101)]

    def test_recovers_known_mobility(self):
        r = fit.saturation_fit(self.made_device(+1), 20, 4, 5, 9)
        self.assertAlmostEqual(r["mu"], 10, places=6)
        self.assertAlmostEqual(r["vth"], 2, places=6)
        self.assertEqual(r["points"], 41)

    def test_negative_voltage_device(self):
        r = fit.saturation_fit(self.made_device(-1), 20, 4, -9, -5)
        self.assertAlmostEqual(r["mu"], 10, places=6)
        self.assertAlmostEqual(r["vth"], -2, places=6)

    def test_reports_range_actually_used(self):
        # 측정이 10 V에서 끝나는데 8~12 V를 부탁하면, 실제로 쓴 범위가 8~10 V라고 알려야 한다.
        r = fit.saturation_fit(self.made_device(+1), 20, 4, 8, 12)
        self.assertEqual((r["used_from"], r["used_to"]), (8.0, 10.0))

    def test_too_few_points(self):
        with self.assertRaises(ValueError):
            fit.saturation_fit([(1, 1e-9), (2, 2e-9)], 20, 4, 1, 2)


if __name__ == "__main__":
    unittest.main()
