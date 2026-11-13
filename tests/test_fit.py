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

    def test_windows(self):
        self.assertEqual(fit.windows(self.made_device(+1)), [(0, 2), (2, 4), (4, 6), (6, 8), (8, 10)])
        self.assertEqual(fit.windows(self.made_device(-1))[:2], [(0, -2), (-2, -4)])

    def test_constant_mobility_device_gives_same_mu_in_every_window(self):
        # μ가 일정한 소자라면 Vth(2 V)를 넘은 구간은 모두 같은 μ를 내야 한다.
        for sign in (+1, -1):
            pts = self.made_device(sign)
            rs = [fit.saturation_fit(pts, 20, 4, a, b) for a, b in fit.windows(pts)[2:]]
            for r in rs:
                self.assertTrue(fit.vth_before_window(r))
                self.assertAlmostEqual(r["mu"], 10, places=6)

    def test_window_before_vth_is_flagged(self):
        # 꺼진 쪽으로 기울어진 구간: 계산하지 않는다.
        off = fit.saturation_fit([(0, 4e-12), (1, 2e-12), (2, 1e-12)], 20, 4, 0, 2)
        self.assertFalse(fit.turned_on(off))
        # Vth(2 V)가 구간(1~3 V) 안에 있으면 식과 어긋난다고 표시한다.
        pts = [(v / 10, 1e-9 * max(v / 10 - 2, 0) ** 2 + 1e-13) for v in range(10, 31)]
        self.assertFalse(fit.vth_before_window(fit.saturation_fit(pts, 20, 4, 1, 3)))

    def test_too_few_points(self):
        with self.assertRaises(ValueError):
            fit.saturation_fit([(1, 1e-9), (2, 2e-9)], 20, 4, 1, 2)


if __name__ == "__main__":
    unittest.main()
