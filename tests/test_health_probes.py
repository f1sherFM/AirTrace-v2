from unittest.mock import AsyncMock, patch

import httpx
import pytest

import main
from infrastructure.integrations.connection_pool import APIResponse, ServiceType
from services import AirQualityService


@pytest.mark.asyncio
async def test_health_optional_failures_result_in_degraded_not_unhealthy():
    with patch.object(main.AirQualityService, "check_external_api_health", AsyncMock(return_value="unhealthy")), patch.object(
        main.unified_weather_service, "check_weather_api_health", AsyncMock(return_value={"status": "healthy"})
    ), patch.object(main, "get_connection_pool_manager") as pool_manager_mock:
        pool_manager_mock.return_value.health_check_all = AsyncMock(return_value={"open_meteo": True, "weather_api": True})
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "degraded"
            assert payload["services"]["external_api"]["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_liveness_and_readiness_endpoints():
    with patch.object(main.AirQualityService, "check_external_api_health", AsyncMock(return_value="healthy")), patch.object(
        main.unified_weather_service, "check_weather_api_health", AsyncMock(return_value={"status": "healthy"})
    ), patch.object(main, "get_connection_pool_manager") as pool_manager_mock:
        pool_manager_mock.return_value.health_check_all = AsyncMock(return_value={"open_meteo": True, "weather_api": True})
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            live = await client.get("/health/liveness")
            ready = await client.get("/health/readiness")
            live_v2 = await client.get("/v2/liveness")
            ready_v2 = await client.get("/v2/readiness")

            assert live.status_code == 200
            assert live.json()["status"] == "healthy"

            assert ready.status_code == 200
            ready_payload = ready.json()
            assert ready_payload["status"] in {"ready", "not_ready"}
            assert ready_payload["overall"] in {"healthy", "degraded", "unhealthy"}

            assert live_v2.status_code == 200
            assert ready_v2.status_code == 200


@pytest.mark.asyncio
async def test_external_api_health_returns_degraded_and_enters_cooldown_on_429():
    service = AirQualityService()
    service.use_connection_pool = True

    with patch("services.get_connection_pool_manager") as pool_manager_mock:
        pool_manager_mock.return_value.execute_request = AsyncMock(
            return_value=APIResponse(
                status_code=429,
                data={"error": "rate limited"},
                headers={"Retry-After": "120"},
                response_time=0.1,
            )
        )
        first_status = await service.check_external_api_health()
        second_status = await service.check_external_api_health()

    assert first_status == "degraded"
    assert second_status == "degraded"
    assert pool_manager_mock.return_value.execute_request.await_count == 1


@pytest.mark.asyncio
async def test_open_meteo_pool_health_probe_uses_rate_limit_cooldown():
    from infrastructure.integrations.connection_pool import ConnectionPool, PoolConfig

    pool = ConnectionPool(ServiceType.OPEN_METEO, "https://example.test", PoolConfig())

    class _Response:
        def __init__(self):
            self.status_code = 429
            self.headers = {"Retry-After": "120"}
            self.request = httpx.Request("GET", "https://example.test")

    with patch.object(pool.client, "get", AsyncMock(return_value=_Response())):
        first = await pool._perform_health_check()
        second = await pool._perform_health_check()

    assert first is True
    assert second is True
    assert pool.health_check_rate_limited_until is not None
