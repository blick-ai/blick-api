class BlickAuthError(Exception):
    pass


class BlickUserAlreadyExistsError(BlickAuthError):
    pass


class BlickInvalidCredentialsError(BlickAuthError):
    pass


class BlickUserNotConfirmedError(BlickAuthError):
    pass
