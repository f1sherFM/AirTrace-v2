from core.app_factory import create_api_app


def test_stage1_app_factory_builds_app_and_registers_protected_routes():
    app = create_api_app()
    paths = set()
    for route in app.routes:
        if hasattr(route, "path"):
            paths.add(route.path)
        elif hasattr(route, "original_router"):
            prefix = getattr(route.include_context, "prefix", "") if hasattr(route, "include_context") else ""
            for r in getattr(route.original_router, "routes", []):
                if hasattr(r, "path"):
                    paths.add(f"{prefix}{r.path}")

    assert "/weather/current" in paths
    assert "/weather/forecast" in paths
    assert "/history" in paths
    assert "/health" in paths
    assert "/v2/current" in paths
    assert "/v2/forecast" in paths
    assert "/v2/history" in paths
    assert "/v2/health" in paths
