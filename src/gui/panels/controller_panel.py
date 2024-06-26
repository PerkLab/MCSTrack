from .base_panel import BasePanel
from .parameters import \
    ParameterSelector, \
    ParameterSpinboxInteger, \
    ParameterText
from .specialized import \
    ConnectionTable, \
    LogPanel
from src.common import \
    DequeueStatusMessagesResponse, \
    StatusMessageSource
from src.common.structures import \
    COMPONENT_ROLE_LABEL_DETECTOR, \
    COMPONENT_ROLE_LABEL_POSE_SOLVER, \
    StatusMessage
from src.controller import \
    MCTComponentAddress, \
    MCTController, \
    ConnectionReport
from ipaddress import IPv4Address
from pydantic import ValidationError
from typing import Final
import wx
import wx.grid


_STATUS_MESSAGE_TABLE_SUBSCRIBER_LABEL: Final[str] = "status_message_table"


class ControllerPanel(BasePanel):

    _controller: MCTController
    _parameter_label: ParameterText
    _parameter_role: ParameterSelector
    _parameter_ipaddress: ParameterText
    _parameter_port: ParameterSpinboxInteger
    _add_new_button: wx.Button
    _connection_table: ConnectionTable
    _remove_button: wx.Button
    _controller_status_textbox: wx.TextCtrl
    _start_detectors_only_button: wx.Button
    _start_detectors_solvers_button: wx.Button
    _stop_button: wx.Button
    _log_panel: LogPanel

    _controller_status: str  # last status reported by MCTController
    _connection_reports: list[ConnectionReport]
    _is_updating: bool  # Some things should only trigger during explicit user events

    def __init__(
        self,
        parent: wx.Window,
        controller: MCTController,
        status_message_source: StatusMessageSource,
        name: str = "ControllerPanel"
    ):
        super().__init__(
            parent=parent,
            status_message_source=status_message_source,
            name=name)
        self._controller = controller

        self._controller.add_status_subscriber(client_identifier=_STATUS_MESSAGE_TABLE_SUBSCRIBER_LABEL)
        self.status_message_source.add_status_subscriber(subscriber_label=_STATUS_MESSAGE_TABLE_SUBSCRIBER_LABEL)

        horizontal_split_sizer: wx.BoxSizer = wx.BoxSizer(orient=wx.HORIZONTAL)

        control_border_panel: wx.Panel = wx.Panel(parent=self)
        control_border_box: wx.StaticBoxSizer = wx.StaticBoxSizer(
            orient=wx.VERTICAL,
            parent=control_border_panel)
        control_panel: wx.ScrolledWindow = wx.ScrolledWindow(
            parent=control_border_panel)
        control_panel.SetScrollRate(
            xstep=1,
            ystep=1)
        control_panel.ShowScrollbars(
            horz=wx.SHOW_SB_NEVER,
            vert=wx.SHOW_SB_ALWAYS)

        control_sizer: wx.BoxSizer = wx.BoxSizer(orient=wx.VERTICAL)

        self._parameter_label = self.add_control_text_input(
            parent=control_panel,
            sizer=control_sizer,
            label="Label")

        self._parameter_role: ParameterSelector = self.add_control_selector(
            parent=control_panel,
            sizer=control_sizer,
            label="Role",
            selectable_values=[
                COMPONENT_ROLE_LABEL_DETECTOR,
                COMPONENT_ROLE_LABEL_POSE_SOLVER])

        self._parameter_ipaddress = self.add_control_text_input(
            parent=control_panel,
            sizer=control_sizer,
            label="IP Address",
            value="127.0.0.1")

        self._parameter_port = self.add_control_spinbox_integer(
            parent=control_panel,
            sizer=control_sizer,
            label="Port",
            minimum_value=0,
            maximum_value=65535,
            initial_value=8000)

        self.add_new_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Add New")

        self.add_horizontal_line_to_spacer(
            parent=control_panel,
            sizer=control_sizer)

        self._connection_table = ConnectionTable(parent=control_panel)
        control_sizer.Add(
            window=self._connection_table,
            flags=wx.SizerFlags(0).Expand())
        control_sizer.AddSpacer(size=BasePanel.DEFAULT_SPACING_PX_VERTICAL)

        self._remove_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Remove")

        self.add_horizontal_line_to_spacer(
            parent=control_panel,
            sizer=control_sizer)

        self._controller_status_textbox = wx.TextCtrl(
            parent=control_panel,
            style=wx.TE_READONLY | wx.TE_RICH)
        self._controller_status_textbox.SetEditable(False)
        self._controller_status_textbox.SetBackgroundColour(colour=wx.Colour(red=249, green=249, blue=249, alpha=255))
        control_sizer.Add(
            window=self._controller_status_textbox,
            flags=wx.SizerFlags(0).Expand())
        control_sizer.AddSpacer(size=BasePanel.DEFAULT_SPACING_PX_VERTICAL)

        self._start_detectors_only_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Start Detectors Only")

        self._start_detectors_solvers_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Start Detectors And Solvers")

        self._stop_button: wx.Button = self.add_control_button(
            parent=control_panel,
            sizer=control_sizer,
            label="Stop")

        control_spacer_sizer: wx.BoxSizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        control_sizer.Add(
            sizer=control_spacer_sizer,
            flags=wx.SizerFlags(1).Expand())

        control_panel.SetSizerAndFit(sizer=control_sizer)
        control_border_box.Add(
            window=control_panel,
            flags=wx.SizerFlags(1).Expand())
        control_border_panel.SetSizer(sizer=control_border_box)
        horizontal_split_sizer.Add(
            window=control_border_panel,
            flags=wx.SizerFlags(35).Expand())

        self._log_panel = LogPanel(parent=self)
        self._log_panel.SetBackgroundColour(colour=wx.BLACK)
        horizontal_split_sizer.Add(
            window=self._log_panel,
            flags=wx.SizerFlags(65).Expand())

        self.SetSizerAndFit(sizer=horizontal_split_sizer)

        self._parameter_label.Bind(
            event=wx.EVT_TEXT,
            handler=self.on_add_new_parameters_changed)
        self.add_new_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self.on_add_new_pressed)
        self._connection_table.table.Bind(
            event=wx.grid.EVT_GRID_SELECT_CELL,
            handler=self.on_connection_selected)
        self._remove_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self.on_remove_pressed)
        self._start_detectors_only_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self.on_start_detectors_only_pressed)
        self._start_detectors_solvers_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self.on_start_detectors_solvers_pressed)
        self._stop_button.Bind(
            event=wx.EVT_BUTTON,
            handler=self.on_stop_pressed)
        self.add_new_button.Enable(enable=False)

        self._controller_status = str()
        self._connection_reports = list()
        self._is_updating = False

        self.update_controller_buttons()

    def on_add_new_parameters_changed(self, _event: wx.CommandEvent) -> None:
        label: str = self._parameter_label.textbox.GetValue()
        if len(label) < 1:
            self.add_new_button.Enable(enable=False)
            return
        self.add_new_button.Enable(enable=True)

    def on_add_new_pressed(self, _event: wx.CommandEvent) -> None:
        label: str = self._parameter_label.textbox.GetValue()
        if len(label) < 1:
            message: str = f"Provided label must contain 1 or more characters."
            self._controller.add_status_message(
                severity="error",
                message=message)
            return
        if self._controller.contains_connection_label(label=label):
            message: str = f"Provided label {label} already exists. Remove existing before adding again."
            self._controller.add_status_message(
                severity="error",
                message=message)
            return
        ip_address: IPv4Address
        ip_address_str: str = self._parameter_ipaddress.textbox.GetValue()
        try:
            ip_address = IPv4Address(ip_address_str)
        except ValueError:
            message: str = f"Provided IP Address {ip_address_str} does not appear to be valid."
            self._controller.add_status_message(
                severity="error",
                message=message)
            return
        component_address: MCTComponentAddress
        try:
            selected_role_index: int = self._parameter_role.selector.GetSelection()
            component_address: MCTComponentAddress = MCTComponentAddress(
                label=label,
                role=self._parameter_role.selector.GetString(n=selected_role_index),
                ip_address=ip_address,
                port=self._parameter_port.spinbox.GetValue())
        except ValidationError as e:
            message: str = f"Unexpected validation error {e}"
            self._controller.add_status_message(
                severity="error",
                message=message)
            return
        self._controller.add_connection(component_address=component_address)
        self.update_controller_buttons()
        self._parameter_label.textbox.SetValue(value=str())

    def on_connection_selected(self, event: wx.grid.GridEvent):
        if self._is_updating:
            return  # updates may repopulate the grid automatically, we are only interested in user-initiated events
        if event.Selecting():
            self._remove_button.Enable(enable=True)
        else:
            self._remove_button.Enable(enable=False)

    def on_start_detectors_only_pressed(self, _event: wx.CommandEvent) -> None:
        self._controller.start_up(mode=MCTController.StartupMode.DETECTING_ONLY)
        self.update_controller_buttons()

    def on_start_detectors_solvers_pressed(self, _event: wx.CommandEvent) -> None:
        self._controller.start_up(mode=MCTController.StartupMode.DETECTING_AND_SOLVING)
        self.update_controller_buttons()

    def on_stop_pressed(self, _event: wx.CommandEvent) -> None:
        self._controller.shut_down()
        self.update_controller_buttons()

    def on_remove_pressed(self, _event: wx.CommandEvent):
        selected_row_label: str | None = self._connection_table.get_selected_row_label()
        self._controller.remove_connection(label=selected_row_label)
        self.update_connection_table_display()
        self.update_controller_buttons()
        self._remove_button.Enable(enable=False)

    def update_loop(self):
        super().update_loop()
        self._is_updating = True
        self.update_connection_table_display()
        controller_status: str = self._controller.get_status()
        if controller_status != self._controller_status:
            self._controller_status = controller_status
            self._controller_status_textbox.SetValue(f"MCTController Status: {controller_status}")
            self.update_controller_buttons()
        self.update_loop_log_table()
        self._is_updating = False

    def update_controller_buttons(self):
        self._start_detectors_only_button.Enable(enable=False)
        self._start_detectors_solvers_button.Enable(enable=False)
        self._stop_button.Enable(enable=False)
        if self._controller.is_running():
            self._stop_button.Enable(enable=True)
        elif self._controller.is_idle():
            detector_list: list = self._controller.get_component_labels(role=COMPONENT_ROLE_LABEL_DETECTOR)
            contains_detectors: bool = len(detector_list) > 0
            if contains_detectors:
                self._start_detectors_only_button.Enable(enable=True)
                self._start_detectors_solvers_button.Enable(enable=True)

    def update_connection_table_display(self) -> None:
        # Return if there is no change
        connection_reports: list[ConnectionReport] = self._controller.get_connection_reports()
        if len(connection_reports) == len(self._connection_reports):
            identical: bool = True
            for connection_report in connection_reports:
                contained: bool = connection_report in self._connection_reports
                if not contained:
                    identical = False
                    break
            if identical:
                return
        # There has been a change so update internal variables and UI
        self._connection_reports = connection_reports
        self._connection_table.update_contents(row_contents=self._connection_reports)
        selected_row_index: int | None = self._connection_table.get_selected_row_index()
        if selected_row_index is not None and selected_row_index >= len(self._connection_reports):
            selected_row_index = None
        self._connection_table.set_selected_row_index(selected_row_index)

    def update_loop_log_table(self):
        status_messages_response: DequeueStatusMessagesResponse = \
            self._controller.dequeue_status_messages(
                client_identifier=_STATUS_MESSAGE_TABLE_SUBSCRIBER_LABEL)
        status_messages: list[StatusMessage] = status_messages_response.status_messages
        status_messages += self.status_message_source.pop_new_status_messages(
            subscriber_label=_STATUS_MESSAGE_TABLE_SUBSCRIBER_LABEL)
        self._log_panel.output_status_messages(status_messages=status_messages)
