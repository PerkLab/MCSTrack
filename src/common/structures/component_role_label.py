from typing import Final, Literal

COMPONENT_ROLE_LABEL_DETECTOR: Final[str] = "detector"
COMPONENT_ROLE_LABEL_POSE_SOLVER: Final[str] = "pose_solver"
ComponentRoleLabel = Literal["detector", "pose_solver"]
