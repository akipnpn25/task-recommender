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

AUTH_COOKIE_MAX_AGE = (
    AUTH_COOKIE_DAYS
    * 24
    * 60
    * 60
)


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


def save_refresh_cookie(
    refresh_token,
):
    """
    ログイン維持用のRefresh Tokenを
    30日間Cookieへ保存する。
    """

    if not refresh_token:
        return

    controller = (
        get_cookie_controller()
    )

    controller.set(
        AUTH_COOKIE_NAME,
        refresh_token,
        path="/",
        max_age=(
            AUTH_COOKIE_MAX_AGE
        ),
        secure=use_secure_cookie(),
        same_site="lax",
    )
    

def read_refresh_cookie():
    """
    ログイン維持用Cookieを取得する。

    最初にStreamlit標準の
    st.context.cookiesを使い、
    取得できない場合だけ
    CookieControllerを使用する。
    """

    # ページを開いた時点で送信されたCookieを
    # Streamlit標準機能から取得する
    try:
        refresh_token = (
            st.context.cookies.get(
                AUTH_COOKIE_NAME
            )
        )

        if refresh_token:
            return refresh_token

    except Exception:
        pass

    # 古いStreamlitや通常のrerun用
    try:
        controller = (
            get_cookie_controller()
        )

        return controller.get(
            AUTH_COOKIE_NAME
        )

    except Exception:
        return None
    
def is_invalid_refresh_token_error(
    error,
):
    """
    本当にRefresh Tokenが無効な場合だけ
    Cookieを削除するための判定。
    """

    error_text = str(
        error
    ).lower()

    invalid_markers = (
        "invalid refresh token",
        "refresh token not found",
        "refresh token has been revoked",
        "refresh token already used",
        "invalid_grant",
    )

    return any(
        marker in error_text
        for marker in invalid_markers
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
                same_site="lax",
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
    """
    Supabaseの認証情報を
    Session Stateへ保存する。
    """

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

    if (
        user is None
        and session is not None
    ):
        user = getattr(
            session,
            "user",
            None,
        )

    if (
        session is None
        or user is None
    ):
        return False

    st.session_state[
        "supabase_access_token"
    ] = session.access_token

    st.session_state[
        "supabase_refresh_token"
    ] = session.refresh_token

    st.session_state[
        "user_id"
    ] = user.id

    st.session_state[
        "user_email"
    ] = user.email

    if persist_cookie:
        try:
            save_refresh_cookie(
                session.refresh_token
            )

        except Exception as error:
            # Cookie保存に失敗しても、
            # アカウント作成・ログインは成功扱いにする
            print(
                "[auth] Cookie保存に失敗しました:",
                error,
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
    ページ再読み込み時に、
    CookieのRefresh Tokenから
    Supabaseセッションを復元する。
    """

    if is_logged_in():
        return True

    refresh_token = (
        read_refresh_cookie()
    )

    if not refresh_token:
        return False

    try:
        client = (
            create_supabase_client()
        )

        response = (
            client.auth.refresh_session(
                refresh_token
            )
        )

        restored = save_auth_session(
            response,
            persist_cookie=True,
        )

        if not restored:
            clear_auth_session(
                remove_cookie=True
            )
            return False

        return True

    except Exception as error:
        # 通信エラーなどではCookieを消さない。
        # Tokenが本当に無効な場合だけ削除する。
        should_remove_cookie = (
            is_invalid_refresh_token_error(
                error
            )
        )

        clear_auth_session(
            remove_cookie=(
                should_remove_cookie
            )
        )

        return False


# =====================================
# 認証済みSupabaseクライアント
# =====================================
def get_authenticated_client():
    """
    現在ログインしているユーザーの
    JWTを設定したSupabaseクライアントを返す。
    """

    if not is_logged_in():
        restored = (
            restore_auth_session()
        )

        if not restored:
            return None

    client = (
        create_supabase_client()
    )

    previous_refresh_token = (
        st.session_state.get(
            "supabase_refresh_token"
        )
    )

    try:
        response = (
            client.auth.set_session(
                st.session_state[
                    "supabase_access_token"
                ],
                st.session_state[
                    "supabase_refresh_token"
                ],
            )
        )

        if response.session is None:
            clear_auth_session(
                remove_cookie=True
            )
            return None

        new_refresh_token = (
            response.session
            .refresh_token
        )

        token_changed = (
            new_refresh_token
            != previous_refresh_token
        )

        saved = save_auth_session(
            response,
            persist_cookie=(
                token_changed
            ),
        )

        if not saved:
            clear_auth_session(
                remove_cookie=False
            )
            return None

        return client

    except Exception as error:
        # Tokenが本当に無効な場合だけ
        # Cookieも削除する
        should_remove_cookie = (
            is_invalid_refresh_token_error(
                error
            )
        )

        clear_auth_session(
            remove_cookie=(
                should_remove_cookie
            )
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
    with st.form(
        "signup_form"
    ):
        email = st.text_input(
            "メールアドレス",
            placeholder=(
                "example@email.com"
            ),
        )

        password = st.text_input(
            "パスワード",
            type="password",
            help=(
                "6文字以上のパスワードを"
                "設定してください。"
            ),
        )

        password_confirm = (
            st.text_input(
                "パスワード（確認）",
                type="password",
            )
        )

        submitted = (
            st.form_submit_button(
                "アカウントを作成",
                use_container_width=True,
                type="primary",
            )
        )

    if not submitted:
        return

    email = (
        email.strip()
        .lower()
    )

    if not email:
        st.error(
            "メールアドレスを"
            "入力してください。"
        )
        return

    if len(password) < 6:
        st.error(
            "パスワードは6文字以上で"
            "入力してください。"
        )
        return

    if (
        password
        != password_confirm
    ):
        st.error(
            "確認用パスワードが"
            "一致していません。"
        )
        return

    # =====================================
    # Supabaseへのアカウント登録
    # =====================================

    try:
        client = (
            create_supabase_client()
        )

        response = (
            client.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                }
            )
        )

    except Exception as error:
        if is_duplicate_signup_error(
            error
        ):
            st.warning(
                "このメールアドレスは、"
                "すでに登録済み、または"
                "確認待ちの可能性があります。"
            )

            st.info(
                "「ログイン」に切り替えて"
                "お試しください。"
            )

            return

        st.error(
            "アカウントを"
            "作成できませんでした。"
            "時間をおいて、"
            "もう一度お試しください。"
        )

        print(
            "[auth] 新規登録エラー:",
            error,
        )

        return

    # =====================================
    # ここまで来たらアカウント登録は成功
    # =====================================

    if response.user is None:
        st.error(
            "登録結果を確認できませんでした。"
            "もう一度ログインを"
            "お試しください。"
        )
        return

    # メール確認が無効の場合は
    # sessionも返るため、そのままログイン
    if response.session is not None:
        login_saved = (
            save_auth_session(
                response,
                persist_cookie=True,
            )
        )

        if login_saved:
            st.session_state[
                "message"
            ] = (
                "アカウントを作成しました ☕"
            )

            st.rerun()

        # アカウント自体は作成済み
        st.success(
            "アカウントは"
            "作成されています。"
        )

        st.info(
            "「ログイン」に切り替えて、"
            "作成したメールアドレスと"
            "パスワードでログインしてください。"
        )

        return

    # メール確認が有効の場合
    st.success(
        "アカウントを作成しました。"
    )

    st.info(
        "確認メールが届いた場合は、"
        "メール内のリンクを開いてから"
        "ログインしてください ☕"
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