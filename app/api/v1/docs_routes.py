# app/api/v1/docs_routes.py
from flask import Blueprint, jsonify, Response

docs_bp = Blueprint("docs", __name__)

__all__ = ["docs_bp", "build_openapi_spec"]

def build_openapi_spec():
    return {
        "openapi": "3.0.3",
        "info": {"title": "StajOS API", "version": "1.0.0", "description": "StajOS Solo MVP API"},
        "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}},
        "security": [{"bearerAuth": []}],
        "paths": {
            "/api/v1/health": {"get": {"summary": "Health", "security": [], "responses": {"200": {"description": "ok"}}}},
            "/api/v1/auth/register": {"post": {"summary": "Register", "security": [], "responses": {"201": {"description": "created"}}}},
            "/api/v1/auth/login": {"post": {"summary": "Login", "security": [], "responses": {"200": {"description": "tokens"}}}},
            "/api/v1/internships": {"post": {"summary": "Create internship", "responses": {"201": {"description": "created"}}}},
            "/api/v1/logs": {
                "get": {"summary": "List logs", "parameters": [{"name": "internship_id", "in": "query", "required": True, "schema": {"type": "string"}}], "responses": {"200": {"description": "ok"}}},
                "post": {"summary": "Create log", "responses": {"201": {"description": "created"}}},
            },
            "/api/v1/export/json": {"get": {"summary": "Export JSON", "parameters": [{"name": "internship_id", "in": "query", "required": False, "schema": {"type": "string"}}], "responses": {"200": {"description": "envelope data=list"}}}},
            "/api/v1/export/csv": {"get": {"summary": "Export CSV", "parameters": [{"name": "internship_id", "in": "query", "required": False, "schema": {"type": "string"}}], "responses": {"200": {"description": "text/csv download"}}}},
            "/api/v1/dashboard/stats": {"get": {"summary": "Dashboard stats", "responses": {"200": {"description": "ok"}}}},
            "/api/v1/timeline": {"get": {"summary": "Timeline", "responses": {"200": {"description": "ok"}}}},
        },
    }

@docs_bp.route("/api/v1/openapi.json", methods=["GET"], strict_slashes=False)
def openapi_json():
    return jsonify(build_openapi_spec()), 200

@docs_bp.route("/api/v1/docs", methods=["GET"], strict_slashes=False)
def swagger_ui():
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>StajOS API Docs</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"></head><body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url: '/api/v1/openapi.json', dom_id: '#swagger-ui'});</script>
</body></html>"""
    return Response(html, mimetype="text/html")
