from src.common.util import register_corresponding_points
import numpy
from scipy.spatial.transform import Rotation
import unittest


# noinspection DuplicatedCode
class TestRegisterCorrespondingPoints(unittest.TestCase):

    def assertRotationCloseToIdentity(
        self,
        matrix: numpy.ndarray,
        tolerance: float = 0.1
    ) -> None:
        self.assertAlmostEqual(float(matrix[0, 0]), 1.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[0, 1]), 0.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[0, 2]), 0.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[1, 0]), 0.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[1, 1]), 1.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[1, 2]), 0.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[2, 0]), 0.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[2, 1]), 0.0, delta=tolerance)
        self.assertAlmostEqual(float(matrix[2, 2]), 1.0, delta=tolerance)

    def test_identity_3_points(self):
        point_set_from = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0]]
        point_set_to = point_set_from
        matrix = register_corresponding_points(point_set_from, point_set_to)
        self.assertRotationCloseToIdentity(matrix)
        self.assertAlmostEqual(matrix[0, 3], 0.0)
        self.assertAlmostEqual(matrix[1, 3], 0.0)
        self.assertAlmostEqual(matrix[2, 3], 0.0)
        self.assertEqual(matrix[3, 3], 1.0)
        self.assertEqual(matrix[3, 0], 0.0)
        self.assertEqual(matrix[3, 1], 0.0)
        self.assertEqual(matrix[3, 2], 0.0)

    def test_identity_4_points(self):
        point_set_from = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0]]
        point_set_to = point_set_from
        matrix = register_corresponding_points(point_set_from, point_set_to)
        self.assertRotationCloseToIdentity(matrix)
        self.assertAlmostEqual(matrix[0, 3], 0.0)
        self.assertAlmostEqual(matrix[1, 3], 0.0)
        self.assertAlmostEqual(matrix[2, 3], 0.0)
        self.assertEqual(matrix[3, 3], 1.0)
        self.assertEqual(matrix[3, 0], 0.0)
        self.assertEqual(matrix[3, 1], 0.0)
        self.assertEqual(matrix[3, 2], 0.0)

    def test_translation(self):
        point_set_from = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0]]
        translation = [10, 0, 10]
        point_set_to = list(point_set_from + numpy.stack(translation))
        matrix = register_corresponding_points(point_set_from, point_set_to)
        self.assertRotationCloseToIdentity(matrix)
        self.assertAlmostEqual(matrix[0, 3], translation[0])
        self.assertAlmostEqual(matrix[1, 3], translation[1])
        self.assertAlmostEqual(matrix[2, 3], translation[2])
        self.assertEqual(matrix[3, 3], 1.0)
        self.assertEqual(matrix[3, 0], 0.0)
        self.assertEqual(matrix[3, 1], 0.0)
        self.assertEqual(matrix[3, 2], 0.0)

    def test_rotation(self):
        point_set_from = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0]]
        ground_truth = Rotation.as_matrix(Rotation.from_euler(seq="x", angles=90, degrees=True))
        point_set_to = list(numpy.matmul(ground_truth, numpy.asarray(point_set_from).T).T)
        result = register_corresponding_points(point_set_from, point_set_to)
        for i in range(0, 3):
            for j in range(0, 3):
                self.assertAlmostEqual(result[i][j], ground_truth[i][j])
        self.assertAlmostEqual(result[0, 3], 0.0)
        self.assertAlmostEqual(result[1, 3], 0.0)
        self.assertAlmostEqual(result[2, 3], 0.0)
        self.assertEqual(result[3, 3], 1.0)
        self.assertEqual(result[3, 0], 0.0)
        self.assertEqual(result[3, 1], 0.0)
        self.assertEqual(result[3, 2], 0.0)

    def test_rotation_and_translation(self):
        point_set_from = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0]]
        ground_truth = Rotation.as_matrix(Rotation.from_euler(seq="z", angles=-90, degrees=True))
        point_set_to = list(numpy.matmul(ground_truth, numpy.asarray(point_set_from).T).T)
        translation = [10, -20, 30]
        point_set_to = list(point_set_to + numpy.stack(translation))
        result = register_corresponding_points(point_set_from, point_set_to)
        for i in range(0, 3):
            for j in range(0, 3):
                self.assertAlmostEqual(result[i][j], ground_truth[i][j])
        self.assertAlmostEqual(result[0, 3], translation[0])
        self.assertAlmostEqual(result[1, 3], translation[1])
        self.assertAlmostEqual(result[2, 3], translation[2])
        self.assertEqual(result[3, 3], 1.0)
        self.assertEqual(result[3, 0], 0.0)
        self.assertEqual(result[3, 1], 0.0)
        self.assertEqual(result[3, 2], 0.0)

    def test_too_few_points(self):
        point_set_from = [[0.0, 0.0, 0.0]]
        point_set_to = point_set_from
        try:
            register_corresponding_points(point_set_from, point_set_to)
        except ValueError:
            pass

    def test_inequal_point_set_lengths(self):
        point_set_from = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0]]
        point_set_to = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]]
        try:
            register_corresponding_points(point_set_from, point_set_to)
        except ValueError:
            pass

    def test_collinear(self):
        point_set_from = [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0]]
        point_set_to = point_set_from
        try:
            register_corresponding_points(point_set_from, point_set_to, collinearity_do_check=True)
        except ValueError:
            pass

    def test_singular(self):
        point_set_from = [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0]]
        point_set_to = point_set_from
        try:
            register_corresponding_points(point_set_from, point_set_to, collinearity_do_check=True)
        except ValueError:
            pass
