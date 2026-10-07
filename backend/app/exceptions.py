class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NO_ACTIVE_GAME(AppError):
    def __init__(self):
        super().__init__("NO_ACTIVE_GAME", "There is no active game.", 404)


class EMPLOYEE_NOT_FOUND(AppError):
    def __init__(self, name: str):
        super().__init__("EMPLOYEE_NOT_FOUND", f"Employee '{name}' not found.", 404)


class DUPLICATE_EMPLOYEE_NAME(AppError):
    def __init__(self, name: str):
        super().__init__("DUPLICATE_EMPLOYEE_NAME", f"Multiple employees found with name '{name}'.", 400)


class EMPLOYEE_INACTIVE(AppError):
    def __init__(self, name: str):
        super().__init__("EMPLOYEE_INACTIVE", f"Employee '{name}' is not active.", 400)


class PLAYER_ALREADY_JOINED(AppError):
    def __init__(self, name: str):
        super().__init__("PLAYER_ALREADY_JOINED", f"Player '{name}' is already joined.", 400)


class GAME_ALREADY_STARTED(AppError):
    def __init__(self):
        super().__init__("GAME_ALREADY_STARTED", "Game has already started.", 400)


class UNAUTHORIZED(AppError):
    def __init__(self):
        super().__init__("UNAUTHORIZED", "Unauthorized action.", 403)


class UNAUTHORIZED_HOST(AppError):
    def __init__(self):
        super().__init__("UNAUTHORIZED_HOST", "Host authorization failed.", 403)


class ROUND_NOT_ACTIVE(AppError):
    def __init__(self):
        super().__init__("ROUND_NOT_ACTIVE", "Round is not active.", 400)


class QUESTION_NOT_ACTIVE(AppError):
    def __init__(self):
        super().__init__("QUESTION_NOT_ACTIVE", "Question is not active.", 400)


class ANSWER_ALREADY_SUBMITTED(AppError):
    def __init__(self, player_name: str):
        super().__init__("ANSWER_ALREADY_SUBMITTED", f"Player '{player_name}' has already submitted an answer.", 400)


QUESTION_ALREADY_ENDED = AppError("QUESTION_ALREADY_ENDED", "Question has already ended.", 400)
ANSWER_NOT_REVEALED = AppError("ANSWER_NOT_REVEALED", "Answer has not been revealed yet.", 400)
SCORE_ALREADY_COMMITTED = AppError("SCORE_ALREADY_COMMITTED", "Score has already been committed.", 400)
GAME_COMPLETED = AppError("GAME_COMPLETED", "Game has already been completed.", 400)