from datetime import (
    datetime,
    timedelta,
)

import streamlit as st

from streamlit_cookies_controller import (
    CookieController,
)

from supabase_client import (
    create_supabase_client,
)


# =====================================
# 認証Cookie
# =====================================

AUTH_COOKIE_NAME = (
    "task_recommender_refresh_token"
)

AUTH_COOKIE_DAYS = 30

COOKIE_CONTROLLER_KEY = (
    "task_recommender_auth_cookies"
)


def get_cookie_controller():
    return CookieController(
        key=COOKIE_CONTROLLER_KEY
    )


def use_secure_cookie():
    """
    localhostではHTTPなのでSecure=False。
    公開環境ではSecure=Trueにする。
    """

    try:
        host = (
            st.context.headers
            .get(
                "host",
                "",
            )
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
    if not refresh_token:
        return

    controller = (
        get_cookie_controller()
    )

    controller.set(
        AUTH_COOKIE_NAME,
        refresh_token,
        path="/",
        expires=(
            datetime.now()
            + timedelta(
                days=AUTH_COOKIE_DAYS
            )
        ),
        secure=use_secure_cookie(),
        same_site="strict",
    )


def remove_refresh_cookie():
    controller = (
        get_cookie_controller()
    )

    try:
        if (
            controller.get(
                AUTH_COOKIE_NAME
            )
            is not None
        ):
            controller.remove(
                AUTH_COOKIE_NAME,
                path="/",
                secure=(
                    use_secure_cookie()
                ),
                same_site="strict",
            )

    except Exception:
        # Cookieが既に消えていても
        # ログアウト処理は続ける
        pass


# =====================================
# Streamlit側のセッション保存
# =====================================

def save_auth_session(
    auth_response,
    persist_cookie=True,
):
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

    # refresh_session等で
    # userがsession側にある場合にも対応
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
        save_refresh_cookie(
            session.refresh_token
        )

    return True


# =====================================
# ログイン状態
# =====================================

def is_logged_in():
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
    ページを再読み込みした場合などに、
    Cookieのrefresh tokenから
    Supabaseセッションを復元する。
    """

    if is_logged_in():
        return True

    controller = (
        get_cookie_controller()
    )

    refresh_token = (
        controller.get(
            AUTH_COOKIE_NAME
        )
    )

    if not refresh_token:
        return False

    try:
        client = (
            create_supabase_client()
        )

        response = (
            client.auth
            .refresh_session(
                refresh_token
            )
        )

        # refresh tokenは更新されるので
        # Cookieも新しいものへ更新
        return save_auth_session(
            response,
            persist_cookie=True,
        )

    except Exception:
        clear_auth_session(
            remove_cookie=True
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

        # tokenが更新された場合だけ
        # Cookieを書き換える
        token_changed = (
            new_refresh_token
            != previous_refresh_token
        )

        if not save_auth_session(
            response,
            persist_cookie=token_changed,
        ):
            clear_auth_session(
                remove_cookie=True
            )
            return None

        return client

    except Exception:
        clear_auth_session(
            remove_cookie=True
        )

        return None


# =====================================
# ログアウト
# =====================================

def clear_auth_session(
    remove_cookie=False,
):
    keys = [
        "supabase_access_token",
        "supabase_refresh_token",
        "user_id",
        "user_email",
    ]

    for key in keys:
        st.session_state.pop(
            key,
            None,
        )

    if remove_cookie:
        remove_refresh_cookie()


def logout():
    client = None

    try:
        client = (
            get_authenticated_client()
        )

    except Exception:
        client = None

    if client is not None:
        try:
            client.auth.sign_out()

        except Exception:
            pass

    clear_auth_session(
        remove_cookie=True
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
        )
    )

    st.write("")

    # =====================================
    # ログイン
    # =====================================

    if auth_mode == "ログイン":

        with st.form(
            "login_form"
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
            )

            submitted = (
                st.form_submit_button(
                    "ログイン",
                    use_container_width=True,
                    type="primary",
                )
            )

            if submitted:

                if (
                    not email.strip()
                    or not password
                ):
                    st.error(
                        "メールアドレスと"
                        "パスワードを入力してください。"
                    )

                else:
                    try:
                        client = (
                            create_supabase_client()
                        )

                        response = (
                            client.auth
                            .sign_in_with_password(
                                {
                                    "email": (
                                        email.strip()
                                    ),
                                    "password": (
                                        password
                                    ),
                                }
                            )
                        )

                        if save_auth_session(
                            response,
                            persist_cookie=True,
                        ):
                            st.rerun()

                        else:
                            st.error(
                                "ログインできませんでした。"
                            )

                    except Exception:
                        st.error(
                            "メールアドレスまたは"
                            "パスワードを確認してください。"
                        )

    # =====================================
    # 新規登録
    # =====================================

    else:

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

            if submitted:

                if not email.strip():
                    st.error(
                        "メールアドレスを"
                        "入力してください。"
                    )

                elif len(password) < 6:
                    st.error(
                        "パスワードは6文字以上で"
                        "入力してください。"
                    )

                elif (
                    password
                    != password_confirm
                ):
                    st.error(
                        "確認用パスワードが"
                        "一致していません。"
                    )

                else:
                    try:
                        client = (
                            create_supabase_client()
                        )

                        response = (
                            client.auth.sign_up(
                                {
                                    "email": (
                                        email.strip()
                                    ),
                                    "password": (
                                        password
                                    ),
                                }
                            )
                        )

                        # メール確認OFFなら
                        # そのままログイン
                        if response.session:

                            save_auth_session(
                                response,
                                persist_cookie=True,
                            )

                            st.rerun()

                        # メール確認ON
                        else:
                            st.success(
                                "確認メールを送信しました。"
                                "メール内のリンクを開いたあと、"
                                "ログインしてください ☕"
                            )

                    except Exception as error:
                        st.error(
                            "アカウントを"
                            "作成できませんでした。"
                        )

                        st.caption(
                            str(error)
                        )