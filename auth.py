from datetime import datetime, timedelta

import streamlit as st
from streamlit_cookies_controller import CookieController

from supabase_client import create_supabase_client


# =====================================
# 認証Cookie
# =====================================

AUTH_COOKIE_NAME = "task_recommender_refresh_token"
AUTH_COOKIE_DAYS = 30
COOKIE_CONTROLLER_KEY = "task_recommender_auth_cookies"


def get_cookie_controller():
    """ブラウザCookieを操作するコントローラーを返す。"""
    return CookieController(
        key=COOKIE_CONTROLLER_KEY,
    )


def use_secure_cookie():
    """
    localhostではHTTPのためSecure=False、
    公開環境ではSecure=Trueにする。
    """
    try:
        host = (
            st.context.headers
            .get("host", "")
            .split(":")[0]
            .lower()
        )
    except Exception:
        return False

    local_hosts = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    }

    return host not in local_hosts


def save_refresh_cookie(refresh_token):
    """ログイン状態を復元するためのrefresh tokenを保存する。"""
    if not refresh_token:
        return

    controller = get_cookie_controller()

    controller.set(
        AUTH_COOKIE_NAME,
        refresh_token,
        path="/",
        expires=(
            datetime.now()
            + timedelta(days=AUTH_COOKIE_DAYS)
        ),
        secure=use_secure_cookie(),
        same_site="strict",
    )


def remove_refresh_cookie():
    """認証用Cookieを削除する。"""
    controller = get_cookie_controller()

    try:
        if controller.get(AUTH_COOKIE_NAME) is not None:
            controller.remove(
                AUTH_COOKIE_NAME,
                path="/",
                secure=use_secure_cookie(),
                same_site="strict",
            )
    except Exception:
        # Cookieが存在しない場合もログアウト処理は続ける。
        pass


# =====================================
# Streamlit側の認証セッション
# =====================================

def save_auth_session(
    auth_response,
    persist_cookie=True,
):
    """Supabaseの認証情報をSession Stateへ保存する。"""
    session = getattr(
        auth_response,
        "session",
        None,
    )

    user = getattr(
        auth_response,
        "user",
        None,
    )

    # refresh_session()などでは、userがsession側にある場合がある。
    if user is None and session is not None:
        user = getattr(
            session,
            "user",
            None,
        )

    if session is None or user is None:
        return False

    st.session_state["supabase_access_token"] = (
        session.access_token
    )
    st.session_state["supabase_refresh_token"] = (
        session.refresh_token
    )
    st.session_state["user_id"] = user.id
    st.session_state["user_email"] = user.email

    if persist_cookie:
        save_refresh_cookie(
            session.refresh_token,
        )

    return True


def clear_auth_session(remove_cookie=False):
    """Streamlit側の認証情報を削除する。"""
    auth_keys = [
        "supabase_access_token",
        "supabase_refresh_token",
        "user_id",
        "user_email",
    ]

    for key in auth_keys:
        st.session_state.pop(
            key,
            None,
        )

    if remove_cookie:
        remove_refresh_cookie()


def is_logged_in():
    """必要な認証情報がSession Stateにあるか確認する。"""
    return (
        bool(
            st.session_state.get(
                "supabase_access_token"
            )
        )
        and bool(
            st.session_state.get(
                "supabase_refresh_token"
            )
        )
        and bool(
            st.session_state.get(
                "user_id"
            )
        )
    )


# =====================================
# Cookieからログイン状態を復元
# =====================================

def restore_auth_session():
    """
    再読み込みや再訪問時に、Cookieのrefresh tokenから
    Supabaseセッションを復元する。
    """
    if is_logged_in():
        return True

    controller = get_cookie_controller()
    refresh_token = controller.get(
        AUTH_COOKIE_NAME
    )

    if not refresh_token:
        return False

    try:
        client = create_supabase_client()
        response = client.auth.refresh_session(
            refresh_token
        )

        # refresh tokenは更新されるためCookieも更新する。
        return save_auth_session(
            response,
            persist_cookie=True,
        )

    except Exception:
        clear_auth_session(
            remove_cookie=True,
        )
        return False


# =====================================
# 認証済みSupabaseクライアント
# =====================================

def get_authenticated_client():
    """ログイン中ユーザーのJWTを設定したクライアントを返す。"""
    if not is_logged_in():
        if not restore_auth_session():
            return None

    client = create_supabase_client()

    previous_refresh_token = (
        st.session_state.get(
            "supabase_refresh_token"
        )
    )

    try:
        response = client.auth.set_session(
            st.session_state[
                "supabase_access_token"
            ],
            st.session_state[
                "supabase_refresh_token"
            ],
        )

        if response.session is None:
            clear_auth_session(
                remove_cookie=True,
            )
            return None

        new_refresh_token = (
            response.session.refresh_token
        )

        token_changed = (
            new_refresh_token
            != previous_refresh_token
        )

        if not save_auth_session(
            response,
            persist_cookie=token_changed,
        ):
            clear_auth_session(
                remove_cookie=True,
            )
            return None

        return client

    except Exception:
        clear_auth_session(
            remove_cookie=True,
        )
        return None


# =====================================
# ログアウト
# =====================================

def logout():
    """Supabaseからログアウトし、CookieとSession Stateを削除する。"""
    try:
        client = get_authenticated_client()
    except Exception:
        client = None

    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass

    clear_auth_session(
        remove_cookie=True,
    )


# =====================================
# 認証エラーの判定
# =====================================

def is_duplicate_signup_error(error):
    """登録済みメールの可能性が高いエラーか判定する。"""
    error_text = str(error).lower()

    duplicate_markers = (
        "already registered",
        "user already registered",
        "database error saving new user",
        "users_email_partial_key",
        "duplicate key value",
    )

    return any(
        marker in error_text
        for marker in duplicate_markers
    )


# =====================================
# ログインフォーム
# =====================================

def render_login_form():
    with st.form("login_form"):
        email = st.text_input(
            "メールアドレス",
            placeholder="example@email.com",
        )

        password = st.text_input(
            "パスワード",
            type="password",
        )

        submitted = st.form_submit_button(
            "ログイン",
            use_container_width=True,
            type="primary",
        )

    if not submitted:
        return

    email = email.strip().lower()

    if not email or not password:
        st.error(
            "メールアドレスとパスワードを"
            "入力してください。"
        )
        return

    try:
        client = create_supabase_client()
        response = (
            client.auth.sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )
        )

        if save_auth_session(
            response,
            persist_cookie=True,
        ):
            st.rerun()

        st.error(
            "ログインできませんでした。"
        )

    except Exception:
        st.error(
            "メールアドレスまたは"
            "パスワードを確認してください。"
        )
        st.info(
            "新規登録後の場合は、確認メール内の"
            "リンクを開いてからログインしてください。"
        )


# =====================================
# 新規登録フォーム
# =====================================

def render_signup_form():
    with st.form("signup_form"):
        email = st.text_input(
            "メールアドレス",
            placeholder="example@email.com",
        )

        password = st.text_input(
            "パスワード",
            type="password",
            help="6文字以上のパスワードを設定してください。",
        )

        password_confirm = st.text_input(
            "パスワード（確認）",
            type="password",
        )

        submitted = st.form_submit_button(
            "アカウントを作成",
            use_container_width=True,
            type="primary",
        )

    if not submitted:
        return

    email = email.strip().lower()

    if not email:
        st.error(
            "メールアドレスを入力してください。"
        )
        return

    if len(password) < 6:
        st.error(
            "パスワードは6文字以上で"
            "入力してください。"
        )
        return

    if password != password_confirm:
        st.error(
            "確認用パスワードが一致していません。"
        )
        return

    try:
        client = create_supabase_client()
        response = client.auth.sign_up(
            {
                "email": email,
                "password": password,
            }
        )

        # メール確認が無効なら、そのままログインできる。
        if response.session is not None:
            if save_auth_session(
                response,
                persist_cookie=True,
            ):
                st.rerun()

            st.error(
                "登録後のログイン処理に失敗しました。"
            )
            return

        # メール確認が有効な場合。
        st.success(
            "登録を受け付けました。"
            "確認メールが届いた場合は、"
            "メール内のリンクを開いてください ☕"
        )
        st.info(
            "すでに登録済みの場合は、"
            "「ログイン」に切り替えてお試しください。"
        )

    except Exception as error:
        if is_duplicate_signup_error(error):
            st.warning(
                "このメールアドレスは、"
                "すでに登録済み、または確認待ちの"
                "可能性があります。"
            )
            st.info(
                "「ログイン」に切り替えてお試しください。"
                "確認メールが届いている場合は、"
                "メール内のリンクも開いてください。"
            )
            return

        st.error(
            "アカウントを作成できませんでした。"
            "時間をおいて、もう一度お試しください。"
        )


# =====================================
# ログイン / 新規登録画面
# =====================================

def render_auth_page():
    st.markdown(
        "# ☕ 今やる課題推薦"
    )

    st.caption(
        "締切と空き時間から、"
        "今取り組む課題を決めます。"
    )

    st.write("")

    auth_mode = st.segmented_control(
        "認証",
        options=[
            "ログイン",
            "新規登録",
        ],
        default="ログイン",
        selection_mode="single",
        label_visibility="collapsed",
        key="auth_mode",
    )

    st.write("")

    if auth_mode == "新規登録":
        render_signup_form()
    else:
        render_login_form()
