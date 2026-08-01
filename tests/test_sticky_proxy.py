import pytest

from mcp_stateless.sticky_proxy import StickyRouter


def test_routes_new_sessions_round_robin_and_keeps_affinity() -> None:
    router = StickyRouter(("replica-a", "replica-b"))

    first = router.route(None)
    router.bind("session-1", first)
    second = router.route(None)

    assert first == "replica-a"
    assert second == "replica-b"
    assert router.route("session-1") == "replica-a"


def test_rejects_an_unknown_session() -> None:
    router = StickyRouter(("replica-a", "replica-b"))

    with pytest.raises(KeyError):
        router.route("unknown")
