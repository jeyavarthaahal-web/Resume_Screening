from app.config import Settings


def test_frontend_supabase_variables_are_backend_fallbacks(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("VITE_SUPABASE_URL", "https://supabase.example")
    monkeypatch.setenv("VITE_SUPABASE_PUBLISHABLE_KEY", "publishable-test-key")

    settings = Settings(_env_file=None)

    assert settings.supabase_url == "https://supabase.example"
    assert settings.supabase_publishable_key == "publishable-test-key"


def test_server_supabase_variables_take_precedence(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://server.example")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "server-publishable-test-key")
    monkeypatch.setenv("VITE_SUPABASE_URL", "https://frontend.example")
    monkeypatch.setenv("VITE_SUPABASE_PUBLISHABLE_KEY", "frontend-publishable-test-key")

    settings = Settings(_env_file=None)

    assert settings.supabase_url == "https://server.example"
    assert settings.supabase_publishable_key == "server-publishable-test-key"