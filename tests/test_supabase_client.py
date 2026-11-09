from app.core.supabase import SupabaseClient


def test_new_style_keys_go_only_in_apikey_header():
    h = SupabaseClient._headers("sb_secret_abc")
    assert h == {"apikey": "sb_secret_abc"}


def test_user_token_goes_in_authorization():
    h = SupabaseClient._headers("sb_publishable_abc", bearer="user.jwt.token")
    assert h == {"apikey": "sb_publishable_abc", "Authorization": "Bearer user.jwt.token"}


def test_legacy_jwt_keys_also_go_in_authorization():
    h = SupabaseClient._headers("eyJhbGciOiJIUzI1NiJ9.legacy.key")
    assert h["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiJ9.legacy.key"
