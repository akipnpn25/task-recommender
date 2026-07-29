from datetime import datetime


def calculate_score(task, available_minutes):
    """
    課題のおすすめ度を0〜100点で計算する
    """

    task_id, title, deadline, estimated_minutes = task

    deadline_dt = datetime.fromisoformat(deadline)
    now = datetime.now()

    remaining_hours = (
        deadline_dt - now
    ).total_seconds() / 3600

    # 締切済み
    if remaining_hours <= 0:
        return 100

    # =========================
    # 1. 締切の近さ 最大60点
    # =========================

    one_week_hours = 24 * 7

    urgency_score = max(
        0,
        1 - remaining_hours / one_week_hours,
    ) * 60

    # =========================
    # 2. 今の時間との相性 最大25点
    # =========================

    fit_ratio = min(
        available_minutes / estimated_minutes,
        1,
    )

    fit_score = fit_ratio * 25

    # =========================
    # 3. 課題の重さ 最大15点
    # =========================

    workload_score = min(
        estimated_minutes / 180,
        1,
    ) * 15

    total_score = (
        urgency_score
        + fit_score
        + workload_score
    )

    return round(total_score)


def get_reason(task, available_minutes):
    """
    なぜおすすめされたのかを返す
    """

    task_id, title, deadline, estimated_minutes = task

    deadline_dt = datetime.fromisoformat(deadline)
    now = datetime.now()

    remaining_hours = (
        deadline_dt - now
    ).total_seconds() / 3600

    reasons = []

    if remaining_hours <= 24:
        reasons.append("締切が24時間以内です")

    elif remaining_hours <= 72:
        reasons.append("締切が近づいています")

    if estimated_minutes <= available_minutes:
        reasons.append(
            "今の空き時間で終わらせられそうです"
        )

    elif available_minutes >= estimated_minutes / 2:
        reasons.append(
            "今の空き時間で大きく進められそうです"
        )

    else:
        reasons.append(
            "時間のかかる課題なので少しずつ進めるのがおすすめです"
        )

    if estimated_minutes >= 120:
        reasons.append(
            "まとまった作業時間が必要な課題です"
        )

    return reasons


def recommend_tasks(tasks, available_minutes):
    """
    課題をおすすめ度順に並べる
    """

    results = []

    for task in tasks:

        score = calculate_score(
            task,
            available_minutes,
        )

        reasons = get_reason(
            task,
            available_minutes,
        )

        results.append(
            {
                "task": task,
                "score": score,
                "reasons": reasons,
            }
        )

    results.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return results