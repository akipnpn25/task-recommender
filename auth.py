from datetime import datetime, timedelta

import streamlit as st
from streamlit_cookies_controller import CookieController

from supabase_client import create_supabase_client


# =====================================
# 認証Cookie
# =====================================

AUTH_COOKIE_NAME = "task_recommender_refresh_token"
AUTH_COOKIE_DAYS = 30
AUTH_COOKIE_MAX_AGE = AUTH_COOKIE_DAYS * 24 * 60 * 60

COOKIE_READER_KEY = "task_recommender_cookie_reader"
COOKIE_WRITER_KEY = "task_recommender_cookie_writer"
COOKIE_REMOVER_KEY = "task_recommender_cookie_remover"

AUTH_CLIENT_KEY = "_authenticated_supabase_client"
AUTH_COOKIE_PENDING_KEY = "_auth_cookie_pending"
AUTH_COOKIE_LAST_WRITTEN_KEY = "_auth_cookie_last_written"
AUTH_IGNORE_CONTEXT_COOKIE_KEY = "_auth_ignore_context_cookie"


# =====================================
# Cookie操作
# =====================================


def get_cookie_controller(key):
    """指定した用途のCookieControllerを返す。"""
    return CookieController(key=key)


def initialize_cookie_controllers():
    """
    読込・書込・削除で別々のコンポーネントキーを使う。

    同じ実行内で同じキーのCookieコンポーネントを
    複数回呼ぶと競合しやすいため、用途ごとに分離する。
    """

    reader_ready = COOKIE_READER_KEY in st.session_state
    writer_ready = COOKIE_WRITER_KEY in st.session_state
    remover_ready = COOKIE_REMOVER_KEY in st.session_state

    reader = get_cookie_controller(COOKIE_READER_KEY)
    writer = get_cookie_controller(COOKIE_WRITER_KEY)
    remover = get_cookie_controller(COOKIE_REMOVER_KEY)

    return {
        "reader": reader,
        "writer": writer,
        "remover": remover,
        "reader_ready": reader_ready,
        "writer_ready": writer_ready,
        "remover_ready": remover_ready,
    }


def use_secure_cookie():
    """公開環境ではSecure属性を有効にする。"""

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


def read_refresh_cookie(
    reader,
    reader_ready,
):
    """ブラウザからRefresh Tokenを取得する。"""

    # st.context.cookiesは接続開始時点のCookieなので、
    # 通常の再訪問では最も早く、安定して取得できる。
    if not st.session_state.get(
        AUTH_IGNORE_CONTEXT_COOKIE_KEY,
        False,
    ):
        try:
            refresh_token = st.context.cookies.get(
                AUTH_COOKIE_NAME
            )

            if refresh_token:
                return refresh_token

        except Exception:
            pass

    # 初回はCookieControllerのコンストラクタが
    # getAllコンポーネントを1回描画している。
    # 同じ実行でrefresh()まで呼ぶと同一キーが競合するため、
    # 2回目以降だけrefresh()する。
    try:
        if reader_ready:
            reader.refresh()

        cookies = reader.getAll() or {}

        st.session_state[
            COOKIE_READER_KEY
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


def write_refresh_cookie(
    writer,
    writer_ready,
    refresh_token,
):
    """Refresh Tokenを30日間Cookieへ保存する。"""

    if not refresh_token:
        return False

    # 同じStreamlitセッション内で、同一Tokenを
    # 何度も書き込まない。
    if (
        st.session_state.get(
            AUTH_COOKIE_LAST_WRITTEN_KEY
        )
        == refresh_token
    ):
        return True

    try:
        # CookieControllerの初回生成時はgetAllが描画されるが、
        # set()は別のコンポーネント呼び出しなので、
        # 初回でもここで直接保存する。
        writer.set(
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

        st.session_state[
            AUTH_COOKIE_LAST_WRITTEN_KEY
        ] = refresh_token

        st.session_state.pop(
            AUTH_COOKIE_PENDING_KEY,
            None,
        )

        print(
            "[auth] ログイン維持Cookieの保存処理を実行しました。"
        )

        return True

    except Exception as error:
        # 次のrerunでも再試行できるように保持する。
        st.session_state[
            AUTH_COOKIE_PENDING_KEY
        ] = refresh_token

        st.session_state.pop(
            AUTH_COOKIE_LAST_WRITTEN_KEY,
            None,
        )

        print(
            "[auth] Cookie保存エラー:",
            repr(error),
        )

        return False


def sync_refresh_cookie(
    writer,
    writer_ready,
):
    """ログイン中の最新Refresh TokenをCookieへ同期する。"""

    refresh_token = st.session_state.get(
        "supabase_refresh_token"
    )

    if not refresh_token:
        return False

    return write_refresh_cookie(
        writer,
        writer_ready,
        refresh_token,
    )


def remove_refresh_cookie(
    remover,
    remover_ready,
):
    """ログイン維持用Cookieを削除する。"""

    try:
        remover.remove(
            AUTH_COOKIE_NAME,
            path="/",
            secure=use_secure_cookie(),
            same_site="lax",
        )

        st.session_state.pop(
            AUTH_COOKIE_LAST_WRITTEN_KEY,
            None,
        )

        return True

    except Exception as error:
        # Cookieが存在しない場合のKeyErrorも含め、
        # ログアウト処理自体は続ける。
        print(
            "[auth] Cookie削除エラー:",
            repr(error),
        )
        return False


def clear_cookie_caches():
    """CookieControllerのSession Stateキャッシュを消す。"""

    for key in (
        COOKIE_READER_KEY,
        COOKIE_WRITER_KEY,
        COOKIE_REMOVER_KEY,
    ):
        st.session_state.pop(
            key,
            None,
        )


# =====================================
# 認証セッション
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
        st.session_state[
            AUTH_COOKIE_PENDING_KEY
        ] = session.refresh_token

    # ログアウト後に再ログインした場合は、
    # 接続開始時の古いCookieを無視するフラグを解除する。
    st.session_state.pop(
        AUTH_IGNORE_CONTEXT_COOKIE_KEY,
        None,
    )

    return True


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


def clear_auth_session():
    """Streamlit側の認証情報を削除する。"""

    for key in (
        "supabase_access_token",
        "supabase_refresh_token",
        "user_id",
        "user_email",
        AUTH_CLIENT_KEY,
        AUTH_COOKIE_PENDING_KEY,
        AUTH_COOKIE_LAST_WRITTEN_KEY,
    ):
        st.session_state.pop(
            key,
            None,
        )


def is_invalid_refresh_token_error(error):
    """Refresh Tokenが本当に無効なエラーか判定する。"""

    error_text = str(error).lower()

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
    """CookieからSupabaseのログイン状態を復元する。"""

    controllers = initialize_cookie_controllers()

    if is_logged_in():
        # 毎回同じ場所からCookieを同期することで、
        # 遅い端末でも保存処理が実行されやすくなる。
        sync_refresh_cookie(
            controllers["writer"],
            controllers["writer_ready"],
        )
        return True

    refresh_token = read_refresh_cookie(
        controllers["reader"],
        controllers["reader_ready"],
    )

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
            clear_auth_session()
            return False

        # refresh_session()ではRefresh Tokenが更新されるため、
        # 新しいTokenをこの実行中に必ずCookieへ保存する。
        sync_refresh_cookie(
            controllers["writer"],
            controllers["writer_ready"],
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
            remove_refresh_cookie(
                controllers["remover"],
                controllers["remover_ready"],
            )
            clear_cookie_caches()

        return False


# =====================================
# 認証済みSupabaseクライアント
# =====================================


def get_authenticated_client():
    """認証済みSupabaseクライアントを返す。"""

    if not is_logged_in():
        if not restore_auth_session():
            return None

    existing_client = st.session_state.get(
        AUTH_CLIENT_KEY
    )

    if existing_client is not None:
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
            clear_auth_session()
            return None

        saved = save_auth_session(
            response,
            persist_cookie=True,
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

        clear_auth_session()
        return None


# =====================================
# ログアウト
# =====================================


def logout():
    """Supabaseとブラウザの両方からログアウトする。"""

    controllers = initialize_cookie_controllers()

    client = st.session_state.get(
        AUTH_CLIENT_KEY
    )

    if client is not None:
        try:
            client.auth.sign_out()
        except Exception as error:
            print(
                "[auth] Supabaseログアウトエラー:",
                repr(error),
            )

    # st.context.cookiesは接続開始時点の値のため、
    # 同じ接続中は削除前のCookieを返す可能性がある。
    st.session_state[
        AUTH_IGNORE_CONTEXT_COOKIE_KEY
    ] = True

    remove_refresh_cookie(
        controllers["remover"],
        controllers["remover_ready"],
    )

    clear_auth_session()
    clear_cookie_caches()


# =====================================
# 認証エラー判定
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
            st.session_state["message"] = (
                "ログインしました ☕"
            )

            # 次の実行の冒頭で、安定した位置から
            # Cookieを保存する。
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

    st.session_state["message"] = (
        "アカウントを作成しました ☕"
    )

    st.rerun()


# =====================================
# アプリ内ブラウザ判定
# =====================================


def is_in_app_browser():
    """LINE・Instagramなどのアプリ内ブラウザか簡易判定する。"""

    try:
        user_agent = (
            st.context.headers
            .get("user-agent", "")
            .lower()
        )
    except Exception:
        return False

    markers = (
        "line/",
        "instagram",
        "fban",
        "fbav",
        "twitter",
        "micromessenger",
    )

    return any(
        marker in user_agent
        for marker in markers
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

    if is_in_app_browser():
        st.warning(
            "LINEやInstagramなどのアプリ内ブラウザでは、"
            "ログイン情報が保存されないことがあります。"
            "右上のメニューからSafariまたはChromeで開いてください。"
        )

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