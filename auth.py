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
AUTH_CLIENT_KEY = "_authenticated_supabase_client"

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

    controller = get_cookie_controller()

    controller.set(
        AUTH_COOKIE_NAME,
        refresh_token,
        path="/",
        expires=(
            datetime.now()
            + timedelta(days=AUTH_COOKIE_DAYS)
        ),
        max_age=AUTH_COOKIE_MAX_AGE,
        secure=use_secure_cookie(),
        same_site="lax",
    )

    

def read_refresh_cookie():
    """
    ブラウザに保存されたRefresh Tokenを取得する。

    最初のHTTPリクエストに含まれるCookieを先に確認し、
    見つからない場合はCookieControllerのキャッシュを
    ブラウザの実データで更新してから取得する。
    """

    # 新しくページを開いた場合は、
    # st.context.cookiesが最も早く確認できる。
    try:
        refresh_token = st.context.cookies.get(
            AUTH_COOKIE_NAME
        )

        if refresh_token:
            return refresh_token

    except Exception:
        pass

    # CookieControllerはSession State内のキャッシュを
    # 使用するため、get()の前にrefresh()が必要。
    try:
        controller = get_cookie_controller()
        controller.refresh()

        cookies = controller.getAll() or {}

        # 次のrerunでも最新値を使えるようにする。
        st.session_state[
            COOKIE_CONTROLLER_KEY
        ] = cookies

        return cookies.get(
            AUTH_COOKIE_NAME
        )

    except Exception as error:
        print(
            "[auth] Cookie読込エラー:",
            repr(error),
        )
        return None


def ensure_refresh_cookie():
    """
    ログイン中のRefresh TokenがCookieに保存されているか確認し、
    未保存または古い場合は書き直す。
    """

    refresh_token = st.session_state.get(
        "supabase_refresh_token"
    )

    if not refresh_token:
        return

    try:
        controller = get_cookie_controller()

        # Session State内の古いキャッシュではなく、
        # ブラウザの現在のCookieを確認する。
        controller.refresh()
        cookies = controller.getAll() or {}

        st.session_state[
            COOKIE_CONTROLLER_KEY
        ] = cookies

        saved_token = cookies.get(
            AUTH_COOKIE_NAME
        )

        if saved_token != refresh_token:
            save_refresh_cookie(
                refresh_token
            )

    except Exception as error:
        # Cookie保存に失敗しても、
        # 現在のログイン状態は維持する。
        print(
            "[auth] Cookie再保存エラー:",
            repr(error),
        )


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
    client=None,
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

    if client is not None:
        st.session_state[AUTH_CLIENT_KEY] = client

    if persist_cookie:
        try:
            save_refresh_cookie(
                session.refresh_token,
            )
        except Exception as error:
            print(
                "[auth] Cookie保存エラー:",
                repr(error),
            )

    return True



def clear_auth_session(remove_cookie=False):
    """Streamlit側の認証情報を削除する。"""

    auth_keys = [
        "supabase_access_token",
        "supabase_refresh_token",
        "user_id",
        "user_email",
        AUTH_CLIENT_KEY,
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
    ページ再読み込み時に、CookieのRefresh Tokenから
    Supabaseセッションを復元する。
    """

    if is_logged_in():
        ensure_refresh_cookie()
        return True

    refresh_token = read_refresh_cookie()

    if not refresh_token:
        return False

    try:
        client = create_supabase_client()
        response = client.auth.refresh_session(
            refresh_token
        )

        restored = save_auth_session(
            response,
            persist_cookie=True,
            client=client,
        )

        if not restored:
            clear_auth_session(
                remove_cookie=True
            )
            return False

        ensure_refresh_cookie()
        return True

    except Exception as error:
        print(
            "[auth] セッション復元エラー:",
            repr(error),
        )

        should_remove_cookie = (
            is_invalid_refresh_token_error(
                error
            )
        )

        clear_auth_session(
            remove_cookie=should_remove_cookie
        )
        return False



# =====================================
# 認証済みSupabaseクライアント
# =====================================
def get_authenticated_client():
    """
    認証済みSupabaseクライアントを返す。

    同じStreamlitセッション内ではクライアントを使い回し、
    データ取得のたびにRefresh Tokenを更新しないようにする。
    """

    if not is_logged_in():
        if not restore_auth_session():
            return None

    existing_client = st.session_state.get(
        AUTH_CLIENT_KEY
    )

    if existing_client is not None:
        ensure_refresh_cookie()
        return existing_client

    try:
        client = create_supabase_client()
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
                remove_cookie=True
            )
            return None

        saved = save_auth_session(
            response,
            persist_cookie=True,
            client=client,
        )

        if not saved:
            clear_auth_session(
                remove_cookie=False
            )
            return None

        ensure_refresh_cookie()
        return client

    except Exception as error:
        print(
            "[auth] 認証クライアント作成エラー:",
            repr(error),
        )

        should_remove_cookie = (
            is_invalid_refresh_token_error(
                error
            )
        )

        clear_auth_session(
            remove_cookie=should_remove_cookie
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
        "users_email_partial_key",
        "duplicate key value",
    )

    return any(
        marker in error_text
        for marker in duplicate_markers
    )


def is_signup_rate_limit_error(error):
    """新規登録の回数制限エラーか判定する。"""
    error_text = str(error).lower()

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
            client=client,
        ):
            # CookieControllerがブラウザへCookieを書き込む前に
            # 即時rerunすると、書き込みが中断される場合がある。
            # この実行を最後まで完了させ、次のrerunでアプリへ進む。
            st.success(
                "ログインしました ☕"
            )
            st.caption(
                "自動で切り替わらない場合は、"
                "下のボタンを押してください。"
            )
            st.button(
                "アプリを開く",
                key="continue_after_login",
                type="primary",
                use_container_width=True,
            )
            return

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
            "アカウントを作成して始める",
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

    except Exception as error:
        print(
            "[auth] 新規登録エラー:",
            repr(error),
        )

        if is_signup_rate_limit_error(error):
            st.warning(
                "短時間に新規登録が繰り返されたため、"
                "一時的に制限されています。"
            )
            st.info(
                "少し時間を空けてから、"
                "ボタンを1回だけ押してください。"
                "直前の登録が成功している場合は、"
                "「ログイン」もお試しください。"
            )
            return

        if is_duplicate_signup_error(error):
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
            "アカウントを作成できませんでした。"
            "時間をおいて、もう一度お試しください。"
        )
        return

    # Confirm emailがOFFなら、登録成功時にsessionも返る。
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
            "まだONになっている可能性があります。"
        )
        st.info(
            "管理画面でConfirm emailをOFFにしたあと、"
            "「ログイン」からお試しください。"
        )
        return

    if not save_auth_session(
        response,
        persist_cookie=True,
        client=client,
    ):
        st.success(
            "アカウントは作成されました。"
        )
        st.info(
            "「ログイン」から、作成した"
            "メールアドレスとパスワードを"
            "入力してください。"
        )
        return

    # Cookieの書き込みを完了させるため、
    # ここでは即時rerunしない。
    st.session_state["message"] = (
        "アカウントを作成しました ☕"
    )

    st.success(
        "アカウントを作成しました ☕"
    )
    st.caption(
        "自動で切り替わらない場合は、"
        "下のボタンを押してください。"
    )
    st.button(
        "アプリを開く",
        key="continue_after_signup",
        type="primary",
        use_container_width=True,
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