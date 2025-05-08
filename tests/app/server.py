
from velithon.application import Velithon
from velithon.endpoint import HTTPEndpoint
from velithon.routing import Route, Router
from velithon.responses import PlainTextResponse
from velithon.requests import Request
from velithon.params import Query, Path, Form, File, Body
from velithon.datastructures import UploadFile, FormData, Headers
from velithon.di import Provide, inject, FactoryProvider, ServiceContainer
from pydantic import BaseModel
from .container import container, MockUserService, MockUserRepository, create_user_service
import logging
from typing import Annotated
from .endpoint import TestEndpoint
from .validate import TestValidate
from ..app.params_inject import (
    InjectQueryEndpoint,
    InjectQueryItemEndpoint,
    InjectPathEndpoint,
    InjectBodyEndpoint,
    InjectHeadersEndpoint,
    InjectRequestEndpoint,
)

logger = logging.getLogger(__name__)
    
router = Router()
router.add_route("/endpoint", TestEndpoint, methods=["GET", "POST", "PUT", "DELETE"])
router.add_route("/validate", TestValidate, methods=["GET", "POST"])
router.add_route("/inject/query", InjectQueryEndpoint, methods=["GET"])
router.add_route("/inject/query/item", InjectQueryItemEndpoint, methods=["GET"])
router.add_route("/inject/path/{name}", InjectPathEndpoint, methods=["GET"])
router.add_route("/inject/body", InjectBodyEndpoint, methods=["POST"])
router.add_route("/inject/headers", InjectHeadersEndpoint, methods=["GET"])
router.add_route("/inject/request", InjectRequestEndpoint, methods=["GET"])


app = Velithon(routes=router.routes)
app.register_container(container)
