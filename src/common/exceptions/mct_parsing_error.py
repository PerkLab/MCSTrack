from .mct_error import MCTError


class MCTParsingError(MCTError):
    message: str

    def __init__(
        self,
        message: str,
        *args
    ):
        super().__init__(args)
        self.message = message
