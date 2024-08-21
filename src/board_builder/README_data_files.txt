Here is an organisation of where all the collected data is stored:

board_builder/data_recording.json:
This is where all the data_recording is collected. It is refreshed for each new run i.e. when a new BoardBuilder() is created.
self._write_detector_data_to_recording_file in BoardBuilder does that, but it is commented out for now as it slows down the GUI writing to the file each frame

board_builder/test/accuracy/accuracy_test_results:
Stores information related to the accuracy tester such as RMS, parameters, projected frames, etc.

board_builder/test/repeatability/collected_data:
Data about the predicted board collected during in-lab experiment that will be used for repeatability testing

board_builder/test/repeatability/repeatability_test_results:
Stores information related to the repeatability tester such as mean, standard deviation, mean/reference corners, etc.
