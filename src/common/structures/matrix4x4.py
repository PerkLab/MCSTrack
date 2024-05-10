import numpy
from pydantic import BaseModel, Field


def _identity_values() -> list[float]:
    return \
        [1.0, 0.0, 0.0, 0.0,
         0.0, 1.0, 0.0, 0.0,
         0.0, 0.0, 1.0, 0.0,
         0.0, 0.0, 0.0, 1.0]


class Matrix4x4(BaseModel):
    values: list[float] = Field(default_factory=_identity_values)

    def as_numpy_array(self):
        a = self.values
        return numpy.array(
            [[a[0],  a[1],  a[2],  a[3]],
             [a[4],  a[5],  a[6],  a[7]],
             [a[8],  a[9],  a[10], a[11]],
             [a[12], a[13], a[14], a[15]]])

    def __getitem__(self, idx: tuple[int, int]) -> float:
        if isinstance(idx, tuple):
            return self.values[(idx[0]*4) + idx[1]]
        else:
            raise ValueError("Unexpected index. Expected tuple index [row,col].")

    def __mul__(self, other) -> 'Matrix4x4':
        if not isinstance(other, Matrix4x4):
            raise ValueError
        result_numpy_array = numpy.matmul(self.as_numpy_array(), other.as_numpy_array())
        return Matrix4x4(values=list(result_numpy_array.flatten()))

    def inverse(self) -> 'Matrix4x4':
        inv_numpy_array = numpy.linalg.inv(self.as_numpy_array())
        return Matrix4x4.from_numpy_array(inv_numpy_array)

    @staticmethod
    def from_raw_values(
        v00, v01, v02, v03,
        v10, v11, v12, v13,
        v20, v21, v22, v23,
        v30, v31, v32, v33
    ) -> 'Matrix4x4':
        return Matrix4x4(values=[
            v00, v01, v02, v03,
            v10, v11, v12, v13,
            v20, v21, v22, v23,
            v30, v31, v32, v33])

    @staticmethod
    def from_list(
        value_list: list[float]
    ) -> 'Matrix4x4':
        if len(value_list) != 16:
            raise ValueError(f"Expected a list of 16 float. Got {str(value_list)}.")
        return Matrix4x4(values=list(value_list))

    @staticmethod
    def from_numpy_array(
        value_array: numpy.ndarray
    ) -> 'Matrix4x4':
        if len(value_array) != 4:
            raise ValueError(f"Expected input array to have 4 rows. Got {len(value_array)}.")
        for i in range(0, len(value_array)):
            if len(value_array[i]) != 4:
                raise ValueError(f"Expected input row {i} to have 4 col. Got {len(value_array[i])}.")
        return Matrix4x4(values=list(value_array.flatten()))
