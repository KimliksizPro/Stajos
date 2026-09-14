# tests/test_docs_api.py
def test_openapi_json_lists_export_paths(client):
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    paths = r.json["paths"]
    assert "/api/v1/export/json" in paths
    assert "/api/v1/export/csv" in paths
    assert "/api/v1/health" in paths

def test_docs_html(client):
    r = client.get("/api/v1/docs")
    assert r.status_code == 200
    assert "swagger-ui" in r.text.lower()
