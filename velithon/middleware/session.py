from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import typing

from velithon.datastructures import Protocol, Scope
from velithon.middleware.base import ProtocolWrapperMiddleware
from velithon.requests import Request
from velithon.responses import Response


class SessionInterface:
    """Base class for session backends."""

    async def load_session(self, session_id: str | None) -> dict[str, typing.Any]:
        """Load session data from storage."""
        raise NotImplementedError()  # pragma: no cover

    async def save_session(
        self, session_id: str, session_data: dict[str, typing.Any]
    ) -> None:
        """Save session data to storage."""
        raise NotImplementedError()  # pragma: no cover

    async def delete_session(self, session_id: str) -> None:
        """Delete session from storage."""
        raise NotImplementedError()  # pragma: no cover

    def generate_session_id(self) -> str:
        """Generate a new session ID."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


class MemorySessionInterface(SessionInterface):
    """In-memory session storage. Not recommended for production."""

    def __init__(self, max_age: int = 3600):
        self._sessions: dict[str, tuple[dict[str, typing.Any], float]] = {}
        self.max_age = max_age

    async def load_session(self, session_id: str | None) -> dict[str, typing.Any]:
        if session_id is None:
            return {}

        if session_id in self._sessions:
            session_data, timestamp = self._sessions[session_id]
            if time.time() - timestamp < self.max_age:
                return session_data.copy()
            else:
                # Session expired
                del self._sessions[session_id]

        return {}

    async def save_session(
        self, session_id: str, session_data: dict[str, typing.Any]
    ) -> None:
        self._sessions[session_id] = (session_data.copy(), time.time())

    async def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


class SignedCookieSessionInterface(SessionInterface):
    """Cookie-based session storage with signing for security."""

    def __init__(self, secret_key: str, max_age: int = 3600):
        if not secret_key:
            raise ValueError("secret_key is required for signed cookie sessions")
        self.secret_key = (
            secret_key.encode() if isinstance(secret_key, str) else secret_key
        )
        self.max_age = max_age

    def _sign_data(self, data: str) -> str:
        """Sign data with HMAC."""
        signature = hmac.new(self.secret_key, data.encode(), hashlib.sha256).hexdigest()
        return f"{data}.{signature}"

    def _unsign_data(self, signed_data: str) -> str | None:
        """Verify and unsign data."""
        try:
            data, signature = signed_data.rsplit(".", 1)
            expected_signature = hmac.new(
                self.secret_key, data.encode(), hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(signature, expected_signature):
                return data
        except (ValueError, TypeError):
            pass
        return None

    def _encode_session(self, session_data: dict[str, typing.Any]) -> str:
        """Encode session data to a signed string."""
        payload = {"data": session_data, "timestamp": time.time()}
        json_data = json.dumps(payload, separators=(",", ":"))
        encoded_data = base64.urlsafe_b64encode(json_data.encode()).decode().rstrip("=")
        return self._sign_data(encoded_data)

    def _decode_session(self, signed_data: str) -> dict[str, typing.Any]:
        """Decode and verify session data."""
        try:
            encoded_data = self._unsign_data(signed_data)
            if encoded_data is None:
                return {}

            # Add padding if needed
            padding = 4 - len(encoded_data) % 4
            if padding != 4:
                encoded_data += "=" * padding

            json_data = base64.urlsafe_b64decode(encoded_data).decode()
            payload = json.loads(json_data)

            # Check expiration
            if time.time() - payload["timestamp"] > self.max_age:
                return {}

            return payload["data"]
        except (ValueError, TypeError, json.JSONDecodeError):
            return {}

    async def load_session(self, session_id: str | None) -> dict[str, typing.Any]:
        if session_id is None:
            return {}
        return self._decode_session(session_id)

    async def save_session(
        self, session_id: str, session_data: dict[str, typing.Any]
    ) -> None:
        # For cookie sessions, the session_id is actually the encoded session data
        pass

    async def delete_session(self, session_id: str) -> None:
        # For cookie sessions, deletion is handled by clearing the cookie
        pass


class Session(dict[str, typing.Any]):
    """Session object that tracks modifications."""

    def __init__(self, session_data: dict[str, typing.Any] | None = None):
        super().__init__(session_data or {})
        self._modified = False
        self._new = session_data is None or len(session_data) == 0

    def __setitem__(self, key: str, value: typing.Any) -> None:
        super().__setitem__(key, value)
        self._modified = True

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        self._modified = True

    def clear(self) -> None:
        super().clear()
        self._modified = True

    def pop(self, key: str, default: typing.Any = None) -> typing.Any:
        self._modified = True
        return super().pop(key, default)

    def update(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().update(*args, **kwargs)
        self._modified = True

    def setdefault(self, key: str, default: typing.Any = None) -> typing.Any:
        if key not in self:
            self._modified = True
        return super().setdefault(key, default)

    @property
    def modified(self) -> bool:
        """Return True if the session has been modified."""
        return self._modified

    @property
    def is_new(self) -> bool:
        """Return True if this is a new session."""
        return self._new


class SessionProtocol:
    """Protocol wrapper that adds session support to responses."""

    def __init__(
        self, protocol: Protocol, session: Session, middleware: SessionMiddleware
    ):
        self.protocol = protocol
        self.session = session
        self.middleware = middleware
        self._response_sent = False

    def __getattr__(self, name: str) -> typing.Any:
        """Delegate all other attributes to the wrapped protocol."""
        return getattr(self.protocol, name)

    def response_bytes(
        self,
        status: int,
        headers: list[tuple[str, str]],
        body: bytes | memoryview,
    ) -> None:
        """Handle response, setting session cookie if needed."""
        if not self._response_sent:
            self._response_sent = True

            # Create a temporary response to handle cookie setting
            from velithon.responses import Response

            response = Response()
            response.raw_headers = list(headers)

            # Handle session cookie
            if self.session.modified or self.session.is_new:
                self.middleware._set_session_cookie(response, self.session)

            # Update headers with any new cookies - convert to list if needed
            if isinstance(headers, tuple):
                headers = list(headers)
            headers[:] = response.raw_headers

        return self.protocol.response_bytes(status, headers, body)

    async def response_start(self, status: int, headers: list[tuple[str, str]]) -> None:
        """Handle response start for streaming responses."""
        if not self._response_sent:
            self._response_sent = True

            # Create a temporary response to handle cookie setting
            from velithon.responses import Response

            response = Response()
            response.raw_headers = list(headers)

            # Handle session cookie
            if self.session.modified or self.session.is_new:
                self.middleware._set_session_cookie(response, self.session)

            # Update headers with any new cookies - convert to list if needed
            if isinstance(headers, tuple):
                headers = list(headers)
            headers[:] = response.raw_headers

        return await self.protocol.response_start(status, headers)


class SessionMiddleware(ProtocolWrapperMiddleware):
    """Session middleware for Velithon framework."""

    def __init__(
        self,
        app: typing.Any,
        session_interface: SessionInterface | None = None,
        cookie_name: str = "velithon_session",
        cookie_params: dict[str, typing.Any] | None = None,
        secret_key: str | None = None,
        max_age: int = 3600,
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.cookie_params = cookie_params or {
            "path": "/",
            "httponly": True,
            "secure": False,
            "samesite": "lax",
        }
        self.max_age = max_age

        # Set up session interface
        if session_interface is not None:
            self.session_interface = session_interface
        elif secret_key is not None:
            self.session_interface = SignedCookieSessionInterface(secret_key, max_age)
        else:
            self.session_interface = MemorySessionInterface(max_age)

    async def process_http_request(self, scope: Scope, protocol: Protocol) -> None:
        # Load session
        request = Request(scope, protocol)
        session_id = request.cookies.get(self.cookie_name)
        session_data = await self.session_interface.load_session(session_id)
        session = Session(session_data)

        # Add session to scope for access in endpoints
        scope._session = session

        # Wrap protocol to handle session saving
        wrapped_protocol = self.create_wrapped_protocol(scope, protocol)

        await self.app(scope, wrapped_protocol)

    def create_wrapped_protocol(self, scope: Scope, protocol: Protocol) -> Protocol:
        """Create a wrapped protocol that handles session cookie setting."""
        return SessionProtocol(protocol, scope._session, self)

    def _set_session_cookie(self, response: Response, session: Session) -> None:
        """Set session cookie on response."""
        if isinstance(self.session_interface, SignedCookieSessionInterface):
            # For cookie sessions, encode the session data as the cookie value
            if session or session.modified:
                cookie_value = self.session_interface._encode_session(dict(session))
                response.set_cookie(
                    self.cookie_name,
                    cookie_value,
                    max_age=self.max_age,
                    **self.cookie_params,
                )
            elif not session and session.modified:
                # Clear empty session
                response.delete_cookie(
                    self.cookie_name,
                    **{
                        k: v
                        for k, v in self.cookie_params.items()
                        if k in ("path", "domain", "secure", "httponly", "samesite")
                    },
                )
        else:
            # For other session interfaces, save session data and set session ID cookie
            if session.modified or session.is_new:
                if session:
                    # Generate session ID if new session
                    if session.is_new:
                        session_id = self.session_interface.generate_session_id()
                    else:
                        # Use existing session ID from request
                        session_id = getattr(
                            session, "_id", self.session_interface.generate_session_id()
                        )

                    # Save session data (async operation needs to be handled differently)
                    # For now, we'll store the data and ID for later processing
                    session._id = session_id
                    session._needs_save = True

                    response.set_cookie(
                        self.cookie_name,
                        session_id,
                        max_age=self.max_age,
                        **self.cookie_params,
                    )
                else:
                    # Clear empty session
                    response.delete_cookie(
                        self.cookie_name,
                        **{
                            k: v
                            for k, v in self.cookie_params.items()
                            if k in ("path", "domain", "secure", "httponly", "samesite")
                        },
                    )


# Helper function to access session from request
def get_session(request: Request) -> Session:
    """Get session from request object."""
    if hasattr(request.scope, "_session"):
        return request.scope._session
    return Session()
