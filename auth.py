from datetime import datetime, timedelta, timezone
import time

import extra_streamlit_components as stx
import streamlit as st

from supabase_client import create_supabase_client


# =====================================
# 認証設定
# =====================================

AUTH_COOKIE_NAME = "task_recommender_refresh_token"
AUTH_COOKIE_DAYS = 30
AUTH_COOKIE_MAX_AGE = AUTH_COOKIE_DAYS * 24 * 60 * 60

COOKIE_MANAGER_STATE_KEY = "_auth_cookie_manager"
COOKIE_WRITE_VERSION_KEY = "_auth_cookie_write_version"
AUTH_CLIENT_KEY = "_authenticated_supabase_client"


# =====================================
# Cookie操作
# =====================================

def get_cookie_manager():
    """
    CookieManagerをユーザーのStreamlitセッション内で
    1回だけ初期化する。
    """

    manager = st.session_state.get(
        COOKIE_MANAGER_STATE_KEY
    )

    if manager is None:
        manager = stx.CookieManager(
            key="task_recommender_auth_cookie_manager"
        )

        st.session_state[
            COOKIE_MANAGER_STATE_KEY
        ] = manager

    return manager


def next_cookie_component_key(
    action,
):
    """
    Cookie書込・削除コンポーネントのキーを
    毎回変えて、ブラウザ側の処理を確実に実行する。
    """

    version = (
        st.session_state.get(
            COOKIE_WRITE_VERSION_KEY,
            0,
        )
        + 1
    )

    st.session_state[
        COOKIE_WRITE_VERSION_KEY
    ] = version

    return (
        f"auth_cookie_{action}_{version}"
    )


def read_refresh_cookie():
    """
    新しいブラウザ接続の最初のリクエストに
    含まれているCookieを読み取る。
    """

    try:
        return st.context.cookies.get(
            AUTH_COOKIE_NAME
        )

    except Exception as error:
        print(
            "[auth] Cookie読込エラー:",
            repr(error),
        )
        return None


def write_refresh_cookie(
    refresh_token,
):
    """
    Refresh Tokenを30日間Cookieへ保存する。

    Cookie書込後すぐにrerunすると、端末によっては
    ブラウザへの保存が完了しないため、短時間待機する。
    """

    if not refresh_token:
        return False

    try:
        manager = get_cookie_manager()

        manager.set(
            AUTH_COOKIE_NAME,
            refresh_token,
            key=next_cookie_component_key(
                "set"
            ),
            path="/",
            expires_at=(
                datetime.now(
                    timezone.utc
                )
                + timedelta(
                    days=AUTH_COOKIE_DAYS
                )
            ),
            max_age=AUTH_COOKIE_MAX_AGE,
            secure=True,
            same_site="lax",
        )

        # ブラウザ側コンポーネントがCookieを書き込む時間を確保
        time.sleep(0.8)

        print(
            "[auth] ログイン維持Cookieを書き込みました。"
        )

        return True

    except Exception as error:
        print(
            "[auth] Cookie保存エラー:",
            repr(error),
        )
        return False


def remove_refresh_cookie():
    """
    ログイン維持用Cookieを削除する。
    """

    try:
        manager = get_cookie_manager()

        manager.delete(
            AUTH_COOKIE_NAME,
            key=next_cookie_component_key(
                "delete"
            ),
        )

        time.sleep(0.5)

        return True

    except KeyError:
        # CookieManager内部のキャッシュに値がなくても、
        # ブラウザ側への削除命令は実行済みの場合がある。
        return True

    except Exception as error:
        print(
            "[auth] Cookie削除エラー:",
            repr(error),
        )
        return False


# =====================================
# Streamlit側の認証セッション
# =====================================

def save_auth_session(
    auth_response,
    persist_cookie=True,
    client=None,
):
    """
    Supabaseの認証情報をSession Stateへ保存する。
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

    if client is not None:
        st.session_state[
            AUTH_CLIENT_KEY
        ] = client

    if persist_cookie:
        write_refresh_cookie(
            session.refresh_token
        )

    return True


def clear_auth_session():
    """
    Streamlit側の認証情報を削除する。
    """

    for key in (
        "supabase_access_token",
        "supabase_refresh_token",
        "user_id",
        "user_email",
        AUTH_CLIENT_KEY,
    ):
        st.session_state.pop(
            key,
            None,
        )


def is_logged_in():
    """
    必要な認証情報がSession Stateにあるか確認する。
    """

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


def is_invalid_refresh_token_error(
    error,
):
    """
    Refresh Tokenが本当に無効なエラーか判定する。
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


# =====================================
# Cookieからログイン状態を復元
# =====================================

def restore_auth_session():
    """
    ページの更新・タブの開き直し時に、
    CookieからSupabaseセッションを復元する。
    """

    if is_logged_in():
        return True

    refresh_token = (
        read_refresh_cookie()
    )

    print(
        "[auth] 復元用Cookie:",
        "あり"
        if refresh_token
        else "なし",
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
            client=client,
        )

        if not restored:
            clear_auth_session()
            return False

        print(
            "[auth] Cookieからログイン状態を復元しました。"
        )

        return True

    except Exception as error:
        print(
            "[auth] セッション復元エラー:",
            repr(error),
        )

        invalid_token = (
            is_invalid_refresh_token_error(
                error
            )
        )

        clear_auth_session()

        if invalid_token:
            remove_refresh_cookie()

        return False


# =====================================
# 認証済みSupabaseクライアント
# =====================================

def get_authenticated_client():
    """
    認証済みSupabaseクライアントを返す。
    """

    if not is_logged_in():
        if not restore_auth_session():
            return None

    existing_client = (
        st.session_state.get(
            AUTH_CLIENT_KEY
        )
    )

    if existing_client is not None:
        return existing_client

    previous_refresh_token = (
        st.session_state.get(
            "supabase_refresh_token"
        )
    )

    try:
        client = (
            create_supabase_client()
        )

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
            clear_auth_session()
            return None

        new_refresh_token = (
            response.session.refresh_token
        )

        token_changed = (
            new_refresh_token
            != previous_refresh_token
        )

        saved = save_auth_session(
            response,
            persist_cookie=token_changed,
            client=client,
        )

        if not saved:
            clear_auth_session()
            return None

        return client

    except Exception as error:
        print(
            "[auth] 認証クライアント作成エラー:",
            repr(error),
        )

        invalid_token = (
            is_invalid_refresh_token_error(
                error
            )
        )

        clear_auth_session()

        if invalid_token:
            remove_refresh_cookie()

        return None


# =====================================
# ログアウト
# =====================================

def logout():
    """
    Supabaseとブラウザの両方からログアウトする。
    """

    client = (
        st.session_state.get(
            AUTH_CLIENT_KEY
        )
    )

    if client is not None:
        try:
            client.auth.sign_out()

        except Exception as error:
            print(
                "[auth] Supabaseログアウトエラー:",
                repr(error),
            )

    remove_refresh_cookie()
    clear_auth_session()


# =====================================
# 新規登録エラー判定
# =====================================

def is_duplicate_signup_error(
    error,
):
    """
    登録済みメールの可能性が高いエラーか判定する。
    """

    error_text = str(
        error
    ).lower()

    duplicate_markers = (
        "already registered",
        "user already registered",
        "users_email_partial_key",
        "duplicate key value",
    )

    return any(
        marker in error_text
        for marker in duplicate_markers
    )


def is_signup_rate_limit_error(
    error,
):
    """
    新規登録の回数制限エラーか判定する。
    """

    error_text = str(
        error
    ).lower()

    rate_limit_markers = (
        "429",
        "too many requests",
        "rate limit",
        "rate_limit",
        "over_email_send_rate_limit",
        "email rate limit exceeded",
    )

    return any(
        marker in error_text
        for marker in rate_limit_markers
    )


# =====================================
# ログインフォーム
# =====================================

def render_login_form():
    with st.form(
        "login_form"
    ):
        email = st.text_input(
            "メールアドレス",
            placeholder="example@email.com",
        )

        password = st.text_input(
            "パスワード",
            type="password",
        )

        submitted = (
            st.form_submit_button(
                "ログイン",
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

    if (
        not email
        or not password
    ):
        st.error(
            "メールアドレスとパスワードを"
            "入力してください。"
        )
        return

    try:
        client = (
            create_supabase_client()
        )

        response = (
            client.auth
            .sign_in_with_password(
                {
                    "email": email,
                    "password": password,
                }
            )
        )

        saved = save_auth_session(
            response,
            persist_cookie=True,
            client=client,
        )

        if saved:
            st.session_state[
                "message"
            ] = (
                "ログインしました ☕"
            )

            st.rerun()

        st.error(
            "ログインできませんでした。"
        )

    except Exception as error:
        print(
            "[auth] ログインエラー:",
            repr(error),
        )

        st.error(
            "メールアドレスまたは"
            "パスワードを確認してください。"
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
            placeholder="example@email.com",
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
                "アカウントを作成して始める",
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
        print(
            "[auth] 新規登録エラー:",
            repr(error),
        )

        if is_signup_rate_limit_error(
            error
        ):
            st.warning(
                "短時間に新規登録が"
                "繰り返されたため、"
                "一時的に制限されています。"
            )

            st.info(
                "少し時間を空けてから、"
                "ボタンを1回だけ押してください。"
                "直前の登録が成功している場合は、"
                "「ログイン」もお試しください。"
            )
            return

        if is_duplicate_signup_error(
            error
        ):
            st.warning(
                "このメールアドレスは、"
                "すでに登録されています。"
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
        return

    if response.user is None:
        st.error(
            "登録結果を確認できませんでした。"
            "もう一度お試しください。"
        )
        return

    if response.session is None:
        st.success(
            "アカウントは作成されました。"
        )

        st.warning(
            "SupabaseのConfirm emailが"
            "ONになっている可能性があります。"
        )

        st.info(
            "確認メールを開いたあと、"
            "「ログイン」からお試しください。"
        )
        return

    saved = save_auth_session(
        response,
        persist_cookie=True,
        client=client,
    )

    if not saved:
        st.success(
            "アカウントは作成されました。"
        )

        st.info(
            "「ログイン」から、作成した"
            "メールアドレスとパスワードを"
            "入力してください。"
        )
        return

    st.session_state[
        "message"
    ] = (
        "アカウントを作成しました ☕"
    )

    st.rerun()


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

    auth_mode = (
        st.segmented_control(
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
    )

    st.write("")

    if auth_mode == "新規登録":
        render_signup_form()

    else:
        render_login_form()