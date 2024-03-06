import inspect
from abc import ABC
from typing import Union, get_type_hints, Any, List

from fastapi import APIRouter
from fastapi.params import Depends
from pydantic import BaseModel
from pydantic.v1.typing import is_classvar
from starlette.routing import Route, WebSocketRoute

from fastapi_cbv.http_methods import HttpMethods


class ClassBasedView(ABC):
    get_status_code: int = None
    post_status_code: int = None
    put_status_code: int = None
    patch_status_code: int = None
    delete_status_code: int = None

    get_response_model: BaseModel = None
    post_response_model: BaseModel = None
    put_response_model: BaseModel = None
    patch_response_model: BaseModel = None
    delete_response_model: BaseModel = None

    get_responses: dict = None
    post_responses: dict = None
    put_responses: dict = None
    patch_responses: dict = None
    delete_responses: dict = None

    get_exceptions: List[Exception] = None
    post_exceptions: List[Exception] = None
    put_exceptions: List[Exception] = None
    patch_exceptions: List[Exception] = None
    delete_exceptions: List[Exception] = None

    response_class: Any = None

    @classmethod
    def _add_dependencies(cls) -> None:
        old_init = cls.__init__
        old_signature = inspect.signature(old_init)
        old_parameters = list(old_signature.parameters.values())[1:]  # drop `self` parameter
        new_parameters = [
            x for x in old_parameters if x.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        dependency_names: list[str] = []
        for name, hint in get_type_hints(cls).items():
            if is_classvar(hint):
                continue
            parameter_kwargs = {"default": getattr(cls, name, Ellipsis)}
            dependency_names.append(name)
            new_parameters.append(
                inspect.Parameter(name=name, kind=inspect.Parameter.KEYWORD_ONLY, annotation=hint, **parameter_kwargs)
            )
        new_signature = old_signature.replace(parameters=new_parameters)

        def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
            for dep_name in dependency_names:
                dep_value = kwargs.pop(dep_name)
                setattr(self, dep_name, dep_value)
            old_init(self, *args, **kwargs)

        setattr(cls, "__signature__", new_signature)
        setattr(cls, "__init__", new_init)

    @classmethod
    def _build_responses(cls, method_name: str) -> Union[dict, None]:
        new_responses = {}
        exceptions = getattr(cls, f'{method_name}_exceptions') or []
        for exception in exceptions:
            exception = exception()
            new_responses[exception.status_code] = {
                'content': {
                    'application/json': {
                        'example': {
                            'message': exception.message,
                            'code': exception.code
                        }
                    }
                }
            }

        method_responses = getattr(cls, f'{method_name}_responses', None) or {}
        new_responses.update(method_responses)

        return new_responses

    @classmethod
    def _start_class_based_view(cls) -> APIRouter:
        cls._add_dependencies()

        router = APIRouter()

        view = cls
        methods = inspect.getmembers(view, predicate=inspect.isfunction)
        for name, method in methods:
            if name.lower() in HttpMethods.all_values():
                router.add_api_route(
                    path='/',
                    name=f'{cls.__name__.lower()}_{name.lower()}',
                    endpoint=method,
                    methods=[name.lower()],
                    status_code=getattr(view, f'{name.lower()}_status_code', None),
                    response_model=getattr(view, f'{name.lower()}_response_model', None),
                    responses=cls._build_responses(method_name=name.lower()),
                    response_class=getattr(view, 'response_class', None)
                )

        return router

    @classmethod
    def _update_route_endpoint_signature(cls, route: Union[Route, WebSocketRoute]) -> None:
        old_endpoint = route.endpoint

        old_signature = inspect.signature(old_endpoint)
        old_parameters: list[inspect.Parameter] = list(old_signature.parameters.values())

        old_first_parameter = old_parameters[0]  # self
        new_first_parameter = old_first_parameter.replace(default=Depends(cls))

        new_parameters = [new_first_parameter] + [
            parameter.replace(kind=inspect.Parameter.KEYWORD_ONLY) for parameter in old_parameters[1:]
        ]

        new_signature = old_signature.replace(parameters=new_parameters)
        setattr(route.endpoint, "__signature__", new_signature)

    @classmethod
    def as_view(cls) -> APIRouter:
        cls_router = cls._start_class_based_view()

        new_router = APIRouter()

        for route in cls_router.routes:
            cls_router.routes.remove(route)
            cls._update_route_endpoint_signature(route=route)
            new_router.routes.append(route)

        cls_router.include_router(new_router)
        return cls_router
