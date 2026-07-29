from datetime import datetime, timedelta

from recommender import (
    calculate_remaining_minutes,
    get_schedule_summary,
    recommend_tasks,
)


# =====================================
# テスト用便利関数
# =====================================

def make_deadline(days=0, hours=0):
    """
    現在時刻から指定した日数・時間後の
    締切をISO形式で返す
    """
    deadline = (
        datetime.now()
        + timedelta(
            days=days,
            hours=hours,
        )
    )

    return deadline.isoformat()


def make_task(
    task_id,
    title,
    deadline,
    estimated_minutes,
    progress=0,
):
    """
    アプリと同じ形式の課題データを作る
    """
    return (
        task_id,
        title,
        deadline,
        estimated_minutes,
        progress,
    )


# 曜日の空き時間を0にすることで、
# テスト結果を安定させる
NO_WEEKLY_TIME = {
    0: 0,
    1: 0,
    2: 0,
    3: 0,
    4: 0,
    5: 0,
    6: 0,
}


# =====================================
# 1. 進捗を残り時間へ反映できるか
# =====================================

def test_remaining_minutes_with_progress():

    task = make_task(
        task_id=1,
        title="レポート",
        deadline=make_deadline(days=2),
        estimated_minutes=120,
        progress=50,
    )

    remaining = (
        calculate_remaining_minutes(
            task
        )
    )

    assert remaining == 60


# =====================================
# 2. 進捗0%なら全時間が残る
# =====================================

def test_remaining_minutes_without_progress():

    task = make_task(
        task_id=1,
        title="レポート",
        deadline=make_deadline(days=2),
        estimated_minutes=180,
        progress=0,
    )

    remaining = (
        calculate_remaining_minutes(
            task
        )
    )

    assert remaining == 180


# =====================================
# 3. 最初の時間不足を検出できるか
# =====================================

def test_detect_first_shortage():

    task_a = make_task(
        task_id=1,
        title="課題A",
        deadline=make_deadline(days=1),
        estimated_minutes=60,
    )

    task_b = make_task(
        task_id=2,
        title="課題B",
        deadline=make_deadline(days=2),
        estimated_minutes=180,
    )

    tasks = [
        task_a,
        task_b,
    ]

    # 今日使える時間は120分
    # 曜日別空き時間はすべて0
    #
    # A締切時点:
    # 必要60分 / 使える120分
    # → OK
    #
    # B締切時点:
    # 必要240分 / 使える120分
    # → 120分不足

    summary = get_schedule_summary(
        tasks,
        current_available_minutes=120,
        weekly_available_minutes=NO_WEEKLY_TIME,
        date_overrides={},
    )

    first_shortage = (
        summary["first_shortage"]
    )

    assert first_shortage is not None

    assert (
        first_shortage[
            "slack_minutes"
        ]
        == -120
    )


# =====================================
# 4. 時間が十分なら不足なし
# =====================================

def test_no_shortage_when_time_is_enough():

    task_a = make_task(
        task_id=1,
        title="課題A",
        deadline=make_deadline(days=1),
        estimated_minutes=60,
    )

    task_b = make_task(
        task_id=2,
        title="課題B",
        deadline=make_deadline(days=2),
        estimated_minutes=60,
    )

    tasks = [
        task_a,
        task_b,
    ]

    summary = get_schedule_summary(
        tasks,
        current_available_minutes=180,
        weekly_available_minutes=NO_WEEKLY_TIME,
        date_overrides={},
    )

    assert (
        summary["first_shortage"]
        is None
    )


# =====================================
# 5. 締切が近い課題を優先できるか
# =====================================

def test_earlier_deadline_is_recommended_first():

    task_a = make_task(
        task_id=1,
        title="明日締切",
        deadline=make_deadline(days=1),
        estimated_minutes=60,
    )

    task_b = make_task(
        task_id=2,
        title="3日後締切",
        deadline=make_deadline(days=3),
        estimated_minutes=60,
    )

    tasks = [
        task_a,
        task_b,
    ]

    recommendations = (
        recommend_tasks(
            tasks,
            current_available_minutes=180,
            weekly_available_minutes=NO_WEEKLY_TIME,
            date_overrides={},
        )
    )

    first_task = (
        recommendations[
            0
        ][
            "task"
        ]
    )

    assert (
        first_task[1]
        == "明日締切"
    )


# =====================================
# 6. 最初に破綻する締切までの課題を
#    後の課題より優先できるか
# =====================================

def test_tasks_before_first_shortage_are_prioritized():

    task_a = make_task(
        task_id=1,
        title="課題A",
        deadline=make_deadline(days=1),
        estimated_minutes=60,
    )

    task_b = make_task(
        task_id=2,
        title="課題B",
        deadline=make_deadline(days=2),
        estimated_minutes=180,
    )

    task_c = make_task(
        task_id=3,
        title="課題C",
        deadline=make_deadline(days=5),
        estimated_minutes=30,
    )

    tasks = [
        task_a,
        task_b,
        task_c,
    ]

    recommendations = (
        recommend_tasks(
            tasks,
            current_available_minutes=120,
            weekly_available_minutes=NO_WEEKLY_TIME,
            date_overrides={},
        )
    )

    recommended_titles = [
        result["task"][1]
        for result in recommendations
    ]

    # Cより先にA・Bが来ることを確認
    c_index = (
        recommended_titles.index(
            "課題C"
        )
    )

    a_index = (
        recommended_titles.index(
            "課題A"
        )
    )

    b_index = (
        recommended_titles.index(
            "課題B"
        )
    )

    assert a_index < c_index
    assert b_index < c_index


# =====================================
# 7. 今の空き時間で終わる課題の
#    相性スコアが高くなるか
# =====================================

def test_task_that_fits_current_time_gets_full_fit_score():

    task = make_task(
        task_id=1,
        title="30分課題",
        deadline=make_deadline(days=3),
        estimated_minutes=30,
    )

    recommendations = (
        recommend_tasks(
            [task],
            current_available_minutes=30,
            weekly_available_minutes=NO_WEEKLY_TIME,
            date_overrides={},
        )
    )

    score_details = (
        recommendations[
            0
        ][
            "score_details"
        ]
    )

    assert (
        score_details[
            "fit"
        ]
        == 20
    )