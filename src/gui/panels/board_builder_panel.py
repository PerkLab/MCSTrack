from io import BytesIO
import platform
import uuid
import cv2
import logging
from typing import Final
import numpy
import wx
import wx.grid
from cv2 import aruco
import datetime
import json
import os

from src.common.api.empty_response import EmptyResponse
from src.common.api.error_response import ErrorResponse
from src.common.api.mct_request_series import MCTRequestSeries
from src.common.api.mct_response import MCTResponse
from src.common.api.mct_response_series import MCTResponseSeries
from src.common.image_coding import ImageCoding
from src.common.image_utils import ImageUtils
from src.common.standard_resolutions import StandardResolutions
from src.common.structures.detector_frame import DetectorFrame
from src.common.structures.image_resolution import ImageResolution
from src.common.structures.marker_snapshot import MarkerSnapshot
from src.detector.api import CameraImageGetRequest, CalibrationResultGetActiveRequest, \
    CalibrationResultGetActiveResponse
from src.detector.api import CameraImageGetResponse
from src.gui.panels.detector_panel import _CAPTURE_FORMAT

from .base_panel import BasePanel
from .feedback import ImagePanel
from .parameters import ParameterSpinboxFloat, ParameterCheckbox, ParameterText

from src.board_builder import BoardBuilder
from src.common.structures import PoseSolverFrame, Pose, Matrix4x4
from src.controller import MCTController
from src.common import (
    StatusMessageSource
)
from .pose_solver_panel import POSE_REPRESENTATIVE_MODEL
from .specialized import \
    GraphicsRenderer

logger = logging.getLogger(__name__)

_UPDATE_INTERVAL_MILLISECONDS: Final[int] = 16


class BoardBuilderPanel(BasePanel):
    class LiveDetectorPreview(BasePanel):
        detector_label: str
        detector_frame: DetectorFrame
        image_panel: ImagePanel
        image_request_id: uuid.UUID
        image: str

        def __init__(
                self,
                detector_label: str,
                image_panel: ImagePanel
        ):
            self.detector_label = detector_label
            self.image_panel = image_panel
            self.image_request_id = None
            self.image = None
            self.image_snapshot = None

    _controller: MCTController

    _preview_image_checkbox: ParameterCheckbox
    _annotate_detected_checkbox: ParameterCheckbox
    _annotate_rejected_checkbox: ParameterCheckbox
    _tracked_marker_diameter_spinbox: ParameterSpinboxFloat
    _confirm_parameters_button: wx.Button
    _board_label: ParameterText
    _locate_reference_button: wx.Button
    _collect_data_button: wx.Button
    _build_board_button: wx.Button
    _repeatability_testing_checkbox: ParameterCheckbox
    _reset_button: wx.Button
    _live_markers_detected: list[MarkerSnapshot]

    _tracked_target_poses: list[Pose]
    # This could maybe be added to the LiveDetectorPreview class
    _latest_pose_solver_frames: dict[str, PoseSolverFrame]
    live_detector_previews: list[LiveDetectorPreview]

    def __init__(
            self,
            parent: wx.Window,
            controller: MCTController,
            status_message_source: StatusMessageSource,
            name: str = "BoardBuilderPanel"
    ):
        super().__init__(
            parent=parent,
            status_message_source=status_message_source,
            name=name)

        self._controller = controller

        self.timer = wx.Timer(self)
        self._locating_reference = False
        self._collecting_data = False

        self._tracked_target_poses = list()
        self._latest_pose_solver_frames = dict()
        self._live_markers_detected = list()

        self.board_builder = None
        self._marker_size = 0
        self.marker_color = [
            (0, 0, 255),  # Red
            (0, 255, 0),  # Green
            (255, 0, 0),  # Blue
            (0, 255, 255),  # Cyan
        ]

        self._detector_intrinsics = {}

        ### USER INTERFACE FUNCTIONALITIES AND BUTTONS ###
        self.horizontal_split_sizer: wx.BoxSizer = wx.BoxSizer(
            orient=wx.HORIZONTAL)  # Changed from HORIZONTAL to VERTICAL

        control_border_panel: wx.Panel = wx.Panel(parent=self)
        control_border_box: wx.StaticBoxSizer = wx.StaticBoxSizer(
            wx.VERTICAL,
            control_border_panel,
            label="Control Panel")
        control_panel: wx.ScrolledWindow = wx.ScrolledWindow(
            parent=control_border_panel)
        control_panel.SetScrollRate(
            xstep=1,
            ystep=1)
        control_panel.ShowScrollbars(
            horz=wx.SHOW_SB_NEVER,
            vert=wx.SHOW_SB_ALWAYS)

        control_sizer: wx.BoxSizer = wx.BoxSizer(orient=wx.VERTICAL)

        self.add_text_label(
            parent=control_panel,
            sizer=control_sizer,
            label="Detector",
            font_size_delta=2,
            bold=True)

        self._preview_image_checkbox = self.add_control_checkbox(
            parent=control_panel,
            sizer=control_sizer,
            label="Preview Image")

        self._annotate_detected_checkbox = self.add_control_checkbox(
            parent=control_panel,
            sizer=control_sizer,
            label="Annotate Detected")

        self._annotate_rejected_checkbox = self.add_control_checkbox(
            parent=control_panel,
            sizer=control_sizer,
            label="Annotate Rejected")

        self.add_horizontal_line_to_spacer(
            parent=control_panel,
            sizer=control_sizer)

        self.add_text_label(
            parent=control_panel,
            sizer=control_sizer,
            label="Parameters",
            font_size_delta=2,
            bold=True)

        self._tracked_marker_diameter_spinbox: ParameterSpinboxFloat = self.add_control_spinbox_float(
            parent=control_panel,
            sizer=control_sizer,
            label="Marker diameter (mm)",
            minimum_value=1.0,
            maximum_value=1000.0,
            initial_value=10.0,
            step_value=0.5)

        self._board_label = self.add_control_text_input(
            parent=control_panel,
            sizer=control_sizer,
            label="Board Label")

        self._confirm_parameters_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Confirm parameters")

        self.add_horizontal_line_to_spacer(
            parent=control_panel,
            sizer=control_sizer)

        self.add_text_label(
            parent=control_panel,
            sizer=control_sizer,
            label="Board Builder",
            font_size_delta=2,
            bold=True)

        self._locate_reference_button: wx.ToggleButton = self.add_toggle_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Locate Reference"
        )

        self._collect_data_button: wx.ToggleButton = self.add_toggle_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Collect Data"
        )

        self._build_board_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Build Board"
        )

        self.add_horizontal_line_to_spacer(
            parent=control_panel,
            sizer=control_sizer)

        self.add_text_label(
            parent=control_panel,
            sizer=control_sizer,
            label="Testing",
            font_size_delta=2,
            bold=True)

        self._repeatability_testing_checkbox = self.add_control_checkbox(
            parent=control_panel,
            sizer=control_sizer,
            label="Repeatability Testing")
        self._repeatability_testing_checkbox.checkbox.Enable(False)

        self.add_horizontal_line_to_spacer(
            parent=control_panel,
            sizer=control_sizer)

        self.add_text_label(
            parent=control_panel,
            sizer=control_sizer,
            label="Reset",
            font_size_delta=2,
            bold=True)

        self._reset_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Reset"
        )

        control_spacer_sizer: wx.BoxSizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        control_sizer.Add(
            sizer=control_spacer_sizer,
            flags=wx.SizerFlags(1).Expand())

        control_panel.SetSizerAndFit(sizer=control_sizer)
        control_border_box.Add(
            control_panel,
            proportion=1,
            flag=wx.EXPAND)

        control_border_panel.SetSizer(control_border_box)
        self.horizontal_split_sizer.Add(
            control_border_panel,
            proportion=1,
            flag=wx.EXPAND)

        # Create the image panel by default, and add more panes to it later if needed
        self.camera_split_sizer: wx.BoxSizer = wx.BoxSizer(orient=wx.VERTICAL)  # New sizer for two camera frames
        self.default_image_panel = ImagePanel(parent=self)  # Top camera frame (Camera 0)
        self.default_image_panel.SetBackgroundColour(colour=wx.BLACK)
        self.camera_split_sizer.Add(self.default_image_panel, proportion=1, flag=wx.EXPAND)

        self.live_detector_previews = []

        self.horizontal_split_sizer.Add(
            self.camera_split_sizer,
            proportion=1,
            flag=wx.EXPAND)  # Added new sizer to the main sizer

        if platform.system() == "Linux":
            logger.warning("OpenGL context creation does not currently work well in Linux. Rendering is disabled.")
            self._renderer = None
        else:
            self._renderer = GraphicsRenderer(parent=self)
            self.horizontal_split_sizer.Add(
                self._renderer,
                proportion=1,
                flag=wx.EXPAND)  # Adjusted flag value to balance the new layout
            self._renderer.load_models_into_context_from_data_path()
            self._renderer.add_scene_object("coordinate_axes", Matrix4x4())

        self.SetSizerAndFit(sizer=self.horizontal_split_sizer)

        ### EVENT HANDLING ###
        self._confirm_parameters_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self._on_confirm_parameters_pressed)
        self._board_label.Bind(
            event=wx.EVT_TEXT,
            handler=self._on_confirm_parameters_pressed)
        self._preview_image_checkbox.checkbox.Bind(
            event=wx.EVT_CHECKBOX,
            handler=self._on_display_mode_changed)
        self._annotate_detected_checkbox.checkbox.Bind(
            event=wx.EVT_CHECKBOX,
            handler=self._on_display_mode_changed)
        self._annotate_rejected_checkbox.checkbox.Bind(
            event=wx.EVT_CHECKBOX,
            handler=self._on_display_mode_changed)
        self._locate_reference_button.Bind(
            event=wx.EVT_TOGGLEBUTTON,
            handler=self._on_locate_reference_button_click)
        self._collect_data_button.Bind(
            event=wx.EVT_TOGGLEBUTTON,
            handler=self._on_collect_data_button_click)
        self._build_board_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self._on_build_board_button_click)
        self._repeatability_testing_checkbox.checkbox.Bind(
            event=wx.EVT_CHECKBOX,
            handler=self._on_repeatability_testing_checkbox_change)
        self._reset_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self._on_reset_button_click)

        self._locate_reference_button.Enable(False)
        self._collect_data_button.Enable(False)
        self._build_board_button.Enable(False)

    def handle_error_response(
            self,
            response: ErrorResponse
    ):
        super().handle_error_response(response=response)

    def handle_response_series(
            self,
            response_series: MCTResponseSeries
    ) -> None:
        response: MCTResponse
        for response in response_series.series:
            if isinstance(response, CalibrationResultGetActiveResponse):
                self._handle_calibration_result_get_active_response(
                    response=response,
                    responder=response_series.responder)
            elif isinstance(response, CameraImageGetResponse):
                self._handle_capture_snapshot_response(
                    label=response_series.responder,
                    response=response)
            elif isinstance(response, ErrorResponse):
                self.handle_error_response(response=response)
            elif not isinstance(response, EmptyResponse):
                self.handle_unknown_response(response=response)

    def update_loop(self) -> None:
        super().update_loop()

        if self._renderer is not None:
            self._renderer.render()

        if self._controller.is_running():
            detector_data: dict[str, list[MarkerSnapshot]] = {}
            should_refresh = False  # Add this flag

            for preview in self.live_detector_previews:
                if preview.image_request_id is None:
                    self._begin_capture_snapshot(preview)

                detector_label = preview.detector_label
                preview.detector_frame = self._controller.get_live_detector_frame(
                    detector_label=detector_label)
                self._process_frame(preview)

                # The detector frames (updated above) are used for getting the detected corners
                # The detector images are the actual view of the camera, and are displayed in the GUI
                if preview.image_request_id is not None:
                    preview.image_request_id, response_series = self._controller.response_series_pop(
                        request_series_id=preview.image_request_id)
                    if response_series is not None:  # self._live_preview_request_id will be None
                        self.handle_response_series(response_series)
                        should_refresh = True  # Only refresh when new data is received

                detector_data[detector_label] = preview.detector_frame.detected_marker_snapshots

            if detector_data:
                self._run_board_builder(detector_data)
                should_refresh = True

            if should_refresh:
                self.Refresh()  # Refresh only if new data is available

    # Used for updating the GUI camera preview
    def _begin_capture_snapshot(self, preview: LiveDetectorPreview):
        request_series: MCTRequestSeries = MCTRequestSeries(
            series=[
                CameraImageGetRequest(
                    format=_CAPTURE_FORMAT)])
        preview.image_request_id = self._controller.request_series_push(
            connection_label=preview.detector_label,
            request_series=request_series)

    def _draw_all_corners(self, detected_marker_snapshots, scale, frame, color):
        """
        Takes in a dictionary of marker UUIDs to their corners and draws each set of corners on the frame with different colors.
        """

        corners = self._marker_snapshot_list_to_opencv_points(detected_marker_snapshots, scale)

        cv2.polylines(
            img=frame,
            pts=corners,
            isClosed=True,
            color=color,
            thickness=2)

    def _handle_calibration_result_get_active_response(
            self,
            response: CalibrationResultGetActiveResponse,
            responder: str
    ) -> None:
        if response:
            self._detector_intrinsics[responder] = response.intrinsic_calibration.calibrated_values

    def _handle_capture_snapshot_response(
            self,
            label: str,
            response: CameraImageGetResponse
    ):
        for preview in self.live_detector_previews:
            if preview.detector_label == label:
                preview.image = response.image_base64

    @staticmethod
    def _marker_snapshot_list_to_opencv_points(
            marker_snapshot_list: list[MarkerSnapshot],
            scale: float
    ) -> numpy.ndarray:
        corners: list[list[list[(float, float)]]] = [[[
            (corner_point.x_px * scale, corner_point.y_px * scale)
            for corner_point in marker.corner_image_points
        ]] for marker in marker_snapshot_list]
        return_value = numpy.array(corners, dtype=numpy.int32)
        return return_value

    def _on_build_board_button_click(self, event: wx.CommandEvent) -> None:
        target_board = self.board_builder.build_board()
        self._render_frame(self.board_builder.detector_poses, self.board_builder.target_poses)

        target_board_json = target_board.json(indent=4)

        # Write result to file
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'board_builder',
                                 'board_builder_results', f'{self.board_builder.board_label}_result.json')
        with open(file_path, 'w') as file:
            file.write(target_board_json)

    def _on_collect_data_button_click(self, event: wx.CommandEvent) -> None:
        if self._collect_data_button.GetValue():
            self._collect_data_button.SetLabel("Stop Collect Data")
            self._build_board_button.Enable(True)
            self._locating_reference = False
            self._collecting_data = True
        else:
            self._collect_data_button.SetLabel("Collect Data")
            self._collecting_data = False

    def _on_confirm_parameters_pressed(self, _event: wx.CommandEvent) -> None:
        self._marker_size = self._tracked_marker_diameter_spinbox.spinbox.GetValue()
        self.board_builder = BoardBuilder(self._marker_size)
        self.board_builder.pose_solver.set_board_marker_size(self._marker_size)  # Set board marker size
        self.board_builder.board_label = self._board_label.textbox.GetValue()  # Set board name
        self._locate_reference_button.Enable(True)
        self._repeatability_testing_checkbox.checkbox.Enable(True)
        for detector_label in self._controller.get_active_detector_labels():
            self._detector_intrinsics[detector_label] = self._controller.get_live_detector_intrinsics(detector_label)

    def _on_display_mode_changed(self, _event: wx.CommandEvent):
        if self._preview_image_checkbox.checkbox.GetValue():
            if not self.live_detector_previews:
                for detector in self._controller.get_active_detector_labels():
                    image_panel = self.default_image_panel

                    if len(self.live_detector_previews) > 0:
                        image_panel = ImagePanel(parent=self)
                        image_panel.SetBackgroundColour(colour=wx.BLACK)
                        self.camera_split_sizer.Add(image_panel, proportion=1, flag=wx.EXPAND)
                        self.horizontal_split_sizer.Layout()

                    preview = self.LiveDetectorPreview(
                        detector_label=detector,
                        image_panel=image_panel)
                    self.live_detector_previews.append(preview)

                for preview in self.live_detector_previews:
                    self._begin_capture_snapshot(preview)

        else:
            for preview in self.live_detector_previews:
                preview.image = None  # Stop displaying the live image from the detector
                preview.image_panel.set_bitmap(wx.Bitmap(1, 1))

            self.default_image_panel.set_bitmap(wx.Bitmap(1, 1))
            self.horizontal_split_sizer.Layout()
            self.Refresh()

    def _on_locate_reference_button_click(self, event: wx.CommandEvent) -> None:
        if self._locate_reference_button.GetValue():
            self._locate_reference_button.SetLabel("Stop Locate Reference")
            self._locate_reference_button.Enable(True)
            self._collect_data_button.Enable(False)
            self._locating_reference = True
            self._collecting_data = False
        else:
            self._locate_reference_button.SetLabel("Locate Reference")
            self._locating_reference = False
            self._collect_data_button.Enable(True)

    def _on_repeatability_testing_checkbox_change(self, event:wx.CommandEvent):
        if self._repeatability_testing_checkbox.checkbox.GetValue():
            self.board_builder.repeatability_testing = True
        else:
            self.board_builder.repeatability_testing = False

    def _on_reset_button_click(self, event: wx.CommandEvent) -> None:
        # TODO: Avoid using reset button for now as it is bugged (I think it's carrying over data from before)
        self._locate_reference_button.Enable(False)
        self._collect_data_button.Enable(False)
        self._build_board_button.Enable(False)
        self._locating_reference = False
        self._collecting_data = False
        self.board_builder = BoardBuilder(self._marker_size)
        self._on_repeatability_testing_checkbox_change(event)
        self._render_frame(self.board_builder.detector_poses, self.board_builder.target_poses)

    def _process_frame(self, preview: LiveDetectorPreview):
        # TODO: The Detector should tell us the resolution of the image it operated on.
        resolution_str: str = str(StandardResolutions.RES_1280X720)
        image_panel = preview.image_panel
        display_image: numpy.ndarray
        scale: float | None

        if self._preview_image_checkbox.checkbox.GetValue() and preview.image is not None:
            opencv_image: numpy.ndarray = ImageCoding.base64_to_image(input_base64=preview.image)
            display_image: numpy.ndarray = ImageUtils.image_resize_to_fit(
                opencv_image=opencv_image,
                available_size=image_panel.GetSize())
            scale: float = display_image.shape[0] / opencv_image.shape[0]

        elif resolution_str is not None and len(resolution_str) > 0:
            panel_size_px: tuple[int, int] = image_panel.GetSize()
            image_resolution: ImageResolution = ImageResolution.from_str(in_str=resolution_str)
            rescaled_resolution_px: tuple[int, int] = ImageUtils.scale_factor_for_available_space_px(
                source_resolution_px=(image_resolution.x_px, image_resolution.y_px),
                available_size_px=panel_size_px)
            display_image = ImageUtils.black_image(resolution_px=rescaled_resolution_px)
            scale: float = rescaled_resolution_px[1] / image_resolution.y_px

        else:
            display_image = ImageUtils.black_image(resolution_px=image_panel.GetSize())
            scale = None

        if scale is not None:
            if self._annotate_detected_checkbox.checkbox.GetValue():
                self._draw_all_corners(preview.detector_frame.detected_marker_snapshots, scale, display_image, [255, 191, 127])
            if self._annotate_rejected_checkbox.checkbox.GetValue():
                self._draw_all_corners(preview.detector_frame.rejected_marker_snapshots, scale, display_image, [127, 191, 255])

        image_buffer: bytes = ImageCoding.image_to_bytes(image_data=display_image, image_format=".jpg")
        image_buffer_io: BytesIO = BytesIO(image_buffer)
        wx_image: wx.Image = wx.Image(image_buffer_io)
        wx_bitmap: wx.Bitmap = wx_image.ConvertToBitmap()
        image_panel.set_bitmap(wx_bitmap)
        image_panel.paint()

    def _render_frame(self, detector_poses, target_poses):
        pose_solver_frame = PoseSolverFrame(
            detector_poses=detector_poses,
            target_poses=target_poses,
            timestamp_utc_iso8601=datetime.datetime.utcnow().isoformat()
        )

        ### RENDERER ###
        self._tracked_target_poses.clear()
        if self._renderer is not None:
            self._latest_pose_solver_frames['pose_solver_label'] = pose_solver_frame
            self._renderer.clear_scene_objects()
            self._renderer.add_scene_object(  # Reference
                model_key=POSE_REPRESENTATIVE_MODEL,
                transform_to_world=Matrix4x4())
        for live_pose_solver in self._latest_pose_solver_frames.values():
            for pose in live_pose_solver.target_poses:
                self._tracked_target_poses.append(pose)
                if self._renderer is not None:
                    self._renderer.add_scene_object(
                        model_key=POSE_REPRESENTATIVE_MODEL,
                        transform_to_world=pose.object_to_reference_matrix)
                if self._renderer is not None:
                    self._renderer.add_scene_object(
                        model_key=POSE_REPRESENTATIVE_MODEL,
                        transform_to_world=pose.object_to_reference_matrix)
            for pose in live_pose_solver.detector_poses:
                self._tracked_target_poses.append(pose)
                if self._renderer is not None:
                    self._renderer.add_scene_object(
                        model_key=POSE_REPRESENTATIVE_MODEL,
                        transform_to_world=pose.object_to_reference_matrix)

    def _run_board_builder(self, detector_data):
        if self._locating_reference:
            for detector_name in self._detector_intrinsics:
                self.board_builder.pose_solver.set_intrinsic_parameters(detector_name,
                                                                        self._detector_intrinsics[detector_name])
            self.board_builder.locate_reference_board(detector_data)

        elif self._collecting_data:
            self.board_builder.collect_data(detector_data)
            self._render_frame(self.board_builder.detector_poses, self.board_builder.target_poses)
