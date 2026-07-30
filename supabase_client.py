import streamlit as st

from supabase import (
    Client,
    create_client,
)


def create_supabase_client() -> Client:
    """
    Supabaseクライアントを作成する。
    """

    url = st.secrets[
        "SUPABASE_URL"
    ]

    key = st.secrets[
        "SUPABASE_PUBLISHABLE_KEY"
    ]

    return create_client(
        url,
        key,
    )