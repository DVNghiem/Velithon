import logging

from velithon.application import Velithon
from velithon.routing import Router

from ..app.params_inject import (
    InjectBodyEndpoint,
    InjectHeadersEndpoint,
    InjectPathEndpoint,
    InjectQueryEndpoint,
    InjectQueryItemEndpoint,
    InjectRequestEndpoint,
)
from .container import container
from .endpoint import TestEndpoint
from .validate import TestValidate

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
