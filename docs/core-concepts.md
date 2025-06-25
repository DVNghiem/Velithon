# Core Concepts

## Application Instance

The `Velithon` class is the main application instance:

```python
from velithon import Velithon

app = Velithon(
    title="My API",
    description="A sample API built with Velithon",
    version="1.0.0"
)
```

## Router

Velithon uses a router to manage routes:

```python
from velithon.routing import Router

router = Router()
router.add_route("/users", UserEndpoint, methods=["GET", "POST"])

app = Velithon(routes=router.routes)
```
