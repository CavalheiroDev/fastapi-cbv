from enum import Enum


class HttpMethods(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"

    @classmethod
    def all_values(cls) -> set:
        return {cls.value for cls in cls}
