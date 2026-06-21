from supabase import create_client, Client

SUPABASE_URL = "https://tgoknkwjgurnnklmwxiu.supabase.co"
SUPABASE_KEY = "sb_publishable_Ngu0kqglloKdPC8e-fOIHA_Y0QO-zVP"

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)