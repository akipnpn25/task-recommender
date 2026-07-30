import streamlit as st
from datetime import datetime, timedelta

from components import format_minutes

from db import (
    save_weekly_settings,
    save_date_override,
    delete_date_override,
)


def render_sidebar(
    saved_weekly_settings,
    date_overrides,
):
    weekday_names = [
        "月曜日",
        "火曜日",
        "水曜日",
        "木曜日",
        "金曜日",
        "土曜日",
        "日曜日",
    ]

    weekly_time_values = [
        0,
        30,
        60,
        120,
        180,
        240,
        300,
    ]

    weekly_available_minutes = {}

    with st.sidebar:

        # =====================================
        # サイドバー上部
        # =====================================

        st.markdown(
            "## ☕ 今やる課題推薦"
        )

        st.caption(
            "「何からやろう？」を"
            "空き時間と締切から決めるアプリ"
        )

        # =====================================
        # 使い方
        # =====================================

        with st.expander(
            "📖 このアプリの使い方"
        ):
            st.markdown(
                """
**① 課題を登録する**  
「＋ 課題を追加」から、
締切と予想所要時間を登録します。

**② 普段の空き時間を設定する**  
このサイドバーで、
曜日ごとに課題へ使える時間を設定します。

**③ 「今日」でおすすめを見る**  
今使える時間を選ぶと、
今取り組む課題をおすすめします。

**④ そのまま集中する**  
「☕ ○分だけ始める」から
集中モードを開始できます。

**⑤ 終わったら進捗を記録する**  
進み具合を更新すると、
次のおすすめにも反映されます。

**⑥ 「見通し」で今後を確認する**  
課題量と空き時間を比べて、
時間不足になりそうな日を確認できます。
                """
            )

        with st.expander(
            "💡 おすすめの使い方"
        ):
            st.write(
                "最初に課題をまとめて登録したら、"
                "普段は「☕ 今日」を開くだけでOKです。"
            )

            st.write(
                "予定が変わった日だけ"
                "「📅 今週だけ変更」を使うと、"
                "より実際の予定に合った推薦になります。"
            )
            with st.expander(
            "🌿 おすすめはどう決まる？"
        ):
                st.write(
                "このアプリは、単純に"
                "締切が近い課題を選ぶだけではありません。"
            )

            st.markdown(
                """
次の情報を組み合わせて、
**「今から取り組んだ方がいい課題」**
を決めています。

- 📅 **締切までの時間**
- ⏱️ **課題の残り作業時間**
- 🗓️ **締切までに使える空き時間**
- 📈 **現在の進捗**
- ☕ **今使える時間**
                """
            )

            st.info(
                "特に、複数の課題をまとめて考えて、"
                "このままだと時間が足りなくなる締切を探します。"
            )

            st.write(
                "そのため、締切が一番近くなくても、"
                "今から始めないと後で厳しくなる課題が"
                "上位になることがあります。"
            )

        st.divider()

        # =====================================
        # 作業時間の設定
        # =====================================

        st.markdown(
            "### ⚙️ 作業時間の設定"
        )

        st.caption(
            "おすすめと見通しの計算に使います。"
        )

        # =====================================
        # 普段の空き時間
        # =====================================

        with st.expander(
            "📆 普段の空き時間"
        ):
            st.caption(
                "各曜日に普段どれくらい"
                "課題へ使えるか設定します。"
            )

            for (
                weekday_index,
                weekday_name,
            ) in enumerate(
                weekday_names
            ):
                saved_minutes = (
                    saved_weekly_settings.get(
                        weekday_index,
                        120,
                    )
                )

                try:
                    default_index = (
                        weekly_time_values.index(
                            saved_minutes
                        )
                    )

                except ValueError:
                    default_index = 3

                selected_minutes = (
                    st.selectbox(
                        weekday_name,
                        weekly_time_values,
                        index=default_index,
                        format_func=format_minutes,
                        key=(
                            f"weekday_"
                            f"{weekday_index}"
                        ),
                    )
                )

                weekly_available_minutes[
                    weekday_index
                ] = selected_minutes

            if st.button(
                "普段の設定を保存",
                use_container_width=True,
            ):
                save_weekly_settings(
                    weekly_available_minutes
                )

                st.session_state[
                    "message"
                ] = (
                    "普段の空き時間を保存しました。"
                )

                st.rerun()

        # =====================================
        # 今週だけ変更
        # =====================================

        with st.expander(
            "📅 今週だけ変更"
        ):
            st.caption(
                "試験・バイトなどで"
                "普段と違う日だけ変更できます。"
            )

            tomorrow = (
                datetime.now().date()
                + timedelta(
                    days=1
                )
            )

            override_date = (
                st.date_input(
                    "変更する日",
                    value=tomorrow,
                    min_value=tomorrow,
                    max_value=(
                        datetime.now().date()
                        + timedelta(
                            days=7
                        )
                    ),
                    key="override_date",
                )
            )

            override_minutes = (
                st.selectbox(
                    "その日に使える時間",
                    weekly_time_values,
                    index=3,
                    format_func=format_minutes,
                    key="override_minutes",
                )
            )

            if st.button(
                "この日を変更",
                key="save_override",
                use_container_width=True,
            ):
                save_date_override(
                    override_date.isoformat(),
                    override_minutes,
                )

                st.session_state[
                    "message"
                ] = (
                    f"{override_date.strftime('%m/%d')}の"
                    "空き時間を変更しました。"
                )

                st.rerun()

            # =====================================
            # 変更済みの日
            # =====================================

            future_overrides = []

            for (
                date_string,
                minutes,
            ) in sorted(
                date_overrides.items()
            ):
                date_object = (
                    datetime.fromisoformat(
                        date_string
                    ).date()
                )

                if (
                    date_object
                    >= datetime.now().date()
                ):
                    future_overrides.append(
                        (
                            date_string,
                            date_object,
                            minutes,
                        )
                    )

            if future_overrides:
                st.divider()

                st.caption(
                    "変更済み"
                )

                for (
                    date_string,
                    date_object,
                    minutes,
                ) in future_overrides:

                    col1, col2 = (
                        st.columns(
                            [3, 1]
                        )
                    )

                    with col1:
                        st.write(
                            f"{date_object.strftime('%m/%d')} "
                            f"→ {format_minutes(minutes)}"
                        )

                    with col2:
                        if st.button(
                            "戻す",
                            key=(
                                "remove_override_"
                                f"{date_string}"
                            ),
                        ):
                            delete_date_override(
                                date_string
                            )

                            st.session_state[
                                "message"
                            ] = (
                                f"{date_object.strftime('%m/%d')}の"
                                "変更を解除しました。"
                            )

                            st.rerun()

    return weekly_available_minutes