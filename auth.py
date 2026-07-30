import streamlit as st

from supabase_client import (
    create_supabase_client,
)


# =====================================
# セッション保存
# =====================================

def save_auth_session(
    auth_response,
):
    """
    Supabaseのログイン情報を
    Streamlit Session Stateに保存する。
    """

    session = auth_response.session
    user = auth_response.user

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

    return True


# =====================================
# ログイン状態
# =====================================

def is_logged_in():
    return (
        "supabase_access_token"
        in st.session_state
        and
        "supabase_refresh_token"
        in st.session_state
        and
        "user_id"
        in st.session_state
    )


# =====================================
# 認証済みSupabaseクライアント
# =====================================

def get_authenticated_client():
    """
    保存しているJWTを設定した
    Supabaseクライアントを返す。
    """

    if not is_logged_in():
        return None

    client = (
        create_supabase_client()
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

        # トークンが更新された場合にも対応
        if response.session is not None:
            st.session_state[
                "supabase_access_token"
            ] = (
                response.session.access_token
            )

            st.session_state[
                "supabase_refresh_token"
            ] = (
                response.session.refresh_token
            )

        return client

    except Exception:
        clear_auth_session()
        return None


# =====================================
# ログアウト
# =====================================

def clear_auth_session():
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


def logout():
    client = (
        get_authenticated_client()
    )

    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass

    clear_auth_session()


# =====================================
# ログイン画面
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
                            response
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

                        # メール確認OFFの場合
                        if response.session:
                            save_auth_session(
                                response
                            )
                            st.rerun()

                        # メール確認ONの場合
                        else:
                            st.success(
                                "確認メールを送信しました。"
                                "メール内のリンクを開いたあと、"
                                "ログインしてください ☕"
                            )

                    except Exception as error:
                        st.error(
                            "アカウントを作成できませんでした。"
                        )

                        st.caption(
                            str(error)
                        )