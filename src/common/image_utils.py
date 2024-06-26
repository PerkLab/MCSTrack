import cv2
import numpy


class ImageUtils:
    """
    A "class" to group related static functions, like in a namespace.
    The class itself is not meant to be instantiated.
    """

    def __init__(self):
        raise RuntimeError("ImageUtils is not meant to be instantiated.")

    @staticmethod
    def black_image(
        resolution_px: tuple[int, int],
    ) -> numpy.ndarray:
        return numpy.zeros((resolution_px[1], resolution_px[0], 3), dtype=numpy.uint8)

    @staticmethod
    def image_resize_to_fit(
        opencv_image: numpy.ndarray,
        available_size: tuple[int, int]  # x, y
    ) -> numpy.ndarray:
        # note: opencv height represented by 1st dimension
        source_resolution_px: tuple[int, int] = (opencv_image.shape[1], opencv_image.shape[0])
        image_width_px, image_height_px = ImageUtils.scale_factor_for_available_space_px(
            source_resolution_px=source_resolution_px,
            available_size_px=available_size)
        return cv2.resize(
            src=opencv_image,
            dsize=(image_width_px, image_height_px))

    @staticmethod
    def scale_factor_for_available_space_px(
        source_resolution_px: tuple[int, int],
        available_size_px: tuple[int, int]
    ) -> tuple[int, int]:
        source_width_px: int = source_resolution_px[0]
        source_height_px: int = source_resolution_px[1]
        available_width_px: int = available_size_px[0]
        available_height_px: int = available_size_px[1]
        scale: float = min(
            available_width_px / float(source_width_px),
            available_height_px / float(source_height_px))
        return int(round(source_width_px * scale)), int(round(source_height_px * scale))
