"""Custom TR-064 port and HTTPS remote access.

Scoped to this integration; does not modify fritzconnection globally.
"""
from urllib.parse import urlsplit, urlunsplit
from fritzconnection import FritzConnection


def remote_url(url, host, port):
    """Rewrite before Requests prepares HTTP Digest authentication."""
    parsed = urlsplit(url)
    if parsed.hostname != host:
        return url
    path = parsed.path or "/"
    if path != "/tr064" and not path.startswith("/tr064/"):
        path = "/tr064" + path
    authority = f"[{host}]" if ":" in host else host
    return urlunsplit(("https", f"{authority}:{port}", path, parsed.query, parsed.fragment))


class RemoteFritzConnection(FritzConnection):
    """Use AVM's WAN endpoint for description, SOAP and list requests."""

    def _load_router_api(self, *args, **kwargs):
        host = urlsplit(self.address).hostname
        request = self.session.request

        def remote_request(method, url, **request_kwargs):
            return request(method, remote_url(url, host, self.port), **request_kwargs)

        self.session.request = remote_request
        return super()._load_router_api(*args, **kwargs)


def create_connection(data, **kwargs):
    remote = data.get("remote_access", False)
    port = data.get("port") or None
    if remote and port is None:
        port = 443
    cls = RemoteFritzConnection if remote else FritzConnection
    return cls(
        address=data["host"],
        user=data["username"],
        password=data["password"],
        use_tls=remote or data.get("use_tls", False),
        port=port,
        redact_debug_log=True,
        **kwargs,
    )
