import os
import re
import time
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

stats = {
    "total_bypassed": 23387799,
    "success_count": 0,
    "failure_count": 0,
    "service_stats": {},
    "uptime": time.time()
}

request_counts = {}


def rate_limit(max_requests=200, window=900):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            now = time.time()

            if ip not in request_counts:
                request_counts[ip] = []

            request_counts[ip] = [
                t for t in request_counts[ip]
                if now - t < window
            ]

            if len(request_counts[ip]) >= max_requests:
                return jsonify({
                    "success": False,
                    "error": "Too many requests. Please try again later."
                }), 429

            request_counts[ip].append(now)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


class BypassService:

    TIMEOUT = 30

    BLOCKED_HOSTS = {
        "fonts.gstatic.com",
        "www.google-analytics.com",
        "google-analytics.com",
        "www.googletagmanager.com",
        "googletagmanager.com"
    }

    STATIC_EXTENSIONS = (
        ".css",
        ".js",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".webp",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp4",
        ".webm"
    )

    @staticmethod
    def is_valid_url(url):
        try:
            parsed = urlparse(url)

            return (
                parsed.scheme in ("http", "https")
                and bool(parsed.netloc)
            )

        except Exception:
            return False

    @staticmethod
    def is_valid_destination(url, original_url=None):
        if not BypassService.is_valid_url(url):
            return False

        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower().split(":")[0]
            path = parsed.path.lower()

            # Reject known page assets / analytics endpoints
            if host in BypassService.BLOCKED_HOSTS:
                return False

            # Reject obvious static assets
            if path.endswith(BypassService.STATIC_EXTENSIONS):
                return False

            # Do not accept the original URL as a destination
            if original_url:
                original = urlparse(original_url)

                if (
                    parsed.scheme == original.scheme
                    and parsed.netloc.lower() == original.netloc.lower()
                    and parsed.path == original.path
                    and parsed.query == original.query
                ):
                    return False

            return True

        except Exception:
            return False

    @staticmethod
    def bypass(url):
        start_time = time.time()

        try:
            if not url or not BypassService.is_valid_url(url):
                return {
                    "success": False,
                    "service": "Unknown",
                    "error": "Invalid URL provided",
                    "processingTime": int(
                        (time.time() - start_time) * 1000
                    )
                }

            service = BypassService.detect_service(url)

            if service == "Linkvertise":
                result = BypassService.bypass_linkvertise(url)

            elif service == "Work.ink":
                result = BypassService.bypass_workink(url)

            elif service == "Lootlabs":
                result = BypassService.bypass_lootlabs(url)

            elif service == "Rekonise":
                result = BypassService.bypass_rekonise(url)

            elif service == "Platoboost":
                result = BypassService.bypass_platoboost(url)

            else:
                result = BypassService.universal_bypass(url)

            result["processingTime"] = int(
                (time.time() - start_time) * 1000
            )

            result["service"] = service

            if result.get("success"):
                stats["success_count"] += 1
            else:
                stats["failure_count"] += 1

            stats["total_bypassed"] += 1

            stats["service_stats"][service] = (
                stats["service_stats"].get(service, 0) + 1
            )

            return result

        except Exception as e:
            stats["failure_count"] += 1

            return {
                "success": False,
                "service": "Unknown",
                "error": str(e),
                "processingTime": int(
                    (time.time() - start_time) * 1000
                )
            }

    @staticmethod
    def bypass_linkvertise(url):
        # Normal redirect resolution only.
        return BypassService.resolve_redirect(url, "Linkvertise")

    @staticmethod
    def bypass_workink(url):
        return BypassService.resolve_redirect(url, "Work.ink")

    @staticmethod
    def bypass_lootlabs(url):
        return BypassService.resolve_redirect(url, "Lootlabs")

    @staticmethod
    def bypass_rekonise(url):
        return BypassService.resolve_redirect(url, "Rekonise")

    @staticmethod
    def bypass_platoboost(url):
        return BypassService.resolve_redirect(url, "Platoboost")

    @staticmethod
    def resolve_redirect(url, service="Universal"):
        try:
            response = requests.get(
                url,
                timeout=BypassService.TIMEOUT,
                allow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Linux; Android 13) "
                        "AppleWebKit/537.36 "
                        "Chrome/120.0 Mobile Safari/537.36"
                    )
                }
            )

            final_url = response.url

            if (
                final_url
                and final_url != url
                and BypassService.is_valid_destination(
                    final_url,
                    url
                )
            ):
                return {
                    "success": True,
                    "destination": final_url,
                    "service": service,
                    "method": "http_redirect",
                    "processingTime": 0
                }

            # Explicit Location header
            location = response.headers.get("Location")

            if location:
                destination = urljoin(url, location)

                if BypassService.is_valid_destination(
                    destination,
                    url
                ):
                    return {
                        "success": True,
                        "destination": destination,
                        "service": service,
                        "method": "location_header",
                        "processingTime": 0
                    }

        except requests.RequestException:
            pass

        return {
            "success": False,
            "service": service,
            "error": "No valid HTTP redirect destination found",
            "processingTime": 0
        }

    @staticmethod
    def universal_bypass(url):
        # First try normal HTTP redirects.
        result = BypassService.resolve_redirect(
            url,
            "Universal"
        )

        if result.get("success"):
            return result

        # Safely inspect explicit destination fields only.
        destination = BypassService.direct_extraction(url)

        if destination:
            return {
                "success": True,
                "destination": destination,
                "service": "Universal",
                "method": "explicit_destination",
                "processingTime": 0
            }

        return {
            "success": False,
            "service": "Universal",
            "error": "Unable to determine a valid destination",
            "processingTime": 0
        }

    @staticmethod
    def direct_extraction(url):
        try:
            response = requests.get(
                url,
                timeout=BypassService.TIMEOUT,
                allow_redirects=False,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(Linux; Android 13) "
                        "AppleWebKit/537.36 "
                        "Chrome/120.0 Mobile Safari/537.36"
                    )
                }
            )

            # Check HTTP Location first.
            location = response.headers.get("Location")

            if location:
                destination = urljoin(url, location)

                if BypassService.is_valid_destination(
                    destination,
                    url
                ):
                    return destination

            html = response.text

            # IMPORTANT:
            # Do NOT scan arbitrary href attributes.
            # That was causing fonts.gstatic.com to be returned.

            patterns = [
                r'"destination"\s*:\s*"([^"]+)"',
                r"'destination'\s*:\s*'([^']+)'",

                r'"target"\s*:\s*"([^"]+)"',
                r"'target'\s*:\s*'([^']+)'",

                r'"redirect"\s*:\s*"([^"]+)"',
                r"'redirect'\s*:\s*'([^']+)'",

                r'"destinationUrl"\s*:\s*"([^"]+)"',
                r"'destinationUrl'\s*:\s*'([^']+)'",

               
