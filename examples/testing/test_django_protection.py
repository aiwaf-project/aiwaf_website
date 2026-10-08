"""Run from this directory using django_test_settings; see /docs/testing."""

from django.core.cache import cache
from django.http import JsonResponse
from django.test import TestCase
from django.urls import path


def message(request):
    return JsonResponse({"message": "Protected"})


def health(request):
    return JsonResponse({"ok": True})


def preview(request):
    return JsonResponse({"message": "Preview"})


urlpatterns = [
    path("api/message", message),
    path("health", health),
    path("api/preview", preview),
]


class ProtectionTests(TestCase):
    def setUp(self):
        # django_test_settings points only at a dedicated local-memory test cache.
        cache.clear()
        self.addCleanup(cache.clear)

    def test_protected_route_throttles(self):
        for _ in range(3):
            response = self.client.get("/api/message")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"message": "Protected"})
        response = self.client.get("/api/message")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json(), {"error": "too_many_requests"})

    def test_health_stays_available_after_throttling(self):
        for _ in range(4):
            self.client.get("/api/message")
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})

    def test_selective_exemption_bypasses_rate_limit(self):
        self.assertEqual(
            [self.client.get("/api/preview").status_code for _ in range(5)],
            [200] * 5,
        )
