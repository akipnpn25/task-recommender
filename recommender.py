from datetime import datetime, timedelta


# =====================================
# 課題単体の残り時間
# =====================================

def calculate_remaining_minutes(task):
    (
        task_id,
        title,
        deadline,
        estimated_minutes,
        progress,
    ) = task

    remaining_ratio = (
        100 - progress
    ) / 100

    return round(
        estimated_minutes
        * remaining_ratio
    )


# =====================================
# 締切までに使える時間
# =====================================

def calculate_available_until(
    deadline,
    current_available_minutes,
    weekly_available_minutes,
    date_overrides=None,
):
    deadline_dt = datetime.fromisoformat(
        deadline
    )

    now = datetime.now()

    if deadline_dt <= now:
        return 0

    if date_overrides is None:
        date_overrides = {}

    # 今日については
    # 「今どれくらい時間がある？」を使う
    total_minutes = (
        current_available_minutes
    )

    current_date = (
        now.date()
        + timedelta(days=1)
    )

    deadline_date = (
        deadline_dt.date()
    )

    while current_date <= deadline_date:

        date_key = (
            current_date.isoformat()
        )

        # 今週だけの変更を優先
        if date_key in date_overrides:

            total_minutes += (
                date_overrides[
                    date_key
                ]
            )

        else:

            weekday = (
                current_date.weekday()
            )

            total_minutes += (
                weekly_available_minutes.get(
                    weekday,
                    0,
                )
            )

        current_date += timedelta(
            days=1
        )

    return total_minutes


# =====================================
# 課題の指標
# =====================================

def get_task_metrics(
    task,
    all_tasks,
    current_available_minutes,
    weekly_available_minutes,
    date_overrides=None,
):
    (
        task_id,
        title,
        deadline,
        estimated_minutes,
        progress,
    ) = task

    deadline_dt = (
        datetime.fromisoformat(
            deadline
        )
    )

    now = datetime.now()

    remaining_hours = (
        deadline_dt - now
    ).total_seconds() / 3600

    available_minutes = (
        calculate_available_until(
            deadline,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
        )
    )

    # この課題の締切以前に来る
    # 全課題の残り時間を合計
    required_minutes = 0

    for other_task in all_tasks:

        other_deadline = (
            datetime.fromisoformat(
                other_task[2]
            )
        )

        if other_deadline <= deadline_dt:

            required_minutes += (
                calculate_remaining_minutes(
                    other_task
                )
            )

    task_remaining_minutes = (
        calculate_remaining_minutes(
            task
        )
    )

    slack_minutes = (
        available_minutes
        - required_minutes
    )

    if available_minutes > 0:

        workload_ratio = (
            required_minutes
            / available_minutes
        )

    elif required_minutes > 0:

        workload_ratio = float(
            "inf"
        )

    else:

        workload_ratio = 0

    return {
        "remaining_hours":
            remaining_hours,

        "available_minutes":
            available_minutes,

        "required_minutes":
            required_minutes,

        "slack_minutes":
            slack_minutes,

        "workload_ratio":
            workload_ratio,

        "task_remaining_minutes":
            task_remaining_minutes,
    }


# =====================================
# 推薦スコア
# =====================================

def calculate_score(
    task,
    all_tasks,
    current_available_minutes,
    weekly_available_minutes,
    date_overrides=None,
):
    metrics = get_task_metrics(
        task,
        all_tasks,
        current_available_minutes,
        weekly_available_minutes,
        date_overrides,
    )

    remaining_hours = (
        metrics["remaining_hours"]
    )

    slack_minutes = (
        metrics["slack_minutes"]
    )

    workload_ratio = (
        metrics["workload_ratio"]
    )

    task_remaining_minutes = (
        metrics[
            "task_remaining_minutes"
        ]
    )

    # -------------------------
    # 締切超過
    # -------------------------

    if remaining_hours <= 0:

        return {
            "total": 100,
            "urgency": 30,
            "risk": 50,
            "fit": 20,
        }

    # -------------------------
    # 1. 締切の近さ
    # 最大30点
    # -------------------------

    one_week_hours = (
        24 * 7
    )

    urgency_score = max(
        0,
        1 - (
            remaining_hours
            / one_week_hours
        ),
    ) * 30

    # -------------------------
    # 2. 時間不足リスク
    # 最大50点
    # -------------------------

    if slack_minutes < 0:

        risk_score = 50

    else:

        risk_score = min(
            workload_ratio,
            1,
        ) * 50

    # -------------------------
    # 3. 今の空き時間との相性
    # 最大20点
    # -------------------------

    if task_remaining_minutes > 0:

        fit_ratio = min(
            current_available_minutes
            / task_remaining_minutes,
            1,
        )

    else:

        fit_ratio = 1

    fit_score = (
        fit_ratio * 20
    )

    total_score = (
        urgency_score
        + risk_score
        + fit_score
    )

    return {
        "total": round(
            min(
                total_score,
                100,
            )
        ),
        "urgency": round(
            urgency_score
        ),
        "risk": round(
            risk_score
        ),
        "fit": round(
            fit_score
        ),
    }


# =====================================
# 推薦理由
# =====================================

def get_reason(
    task,
    all_tasks,
    current_available_minutes,
    weekly_available_minutes,
    date_overrides=None,
):
    (
        task_id,
        title,
        deadline,
        estimated_minutes,
        progress,
    ) = task

    metrics = get_task_metrics(
        task,
        all_tasks,
        current_available_minutes,
        weekly_available_minutes,
        date_overrides,
    )

    remaining_hours = (
        metrics[
            "remaining_hours"
        ]
    )

    slack_minutes = (
        metrics[
            "slack_minutes"
        ]
    )

    task_remaining_minutes = (
        metrics[
            "task_remaining_minutes"
        ]
    )

    reasons = []

    # -------------------------
    # 締切
    # -------------------------

    if remaining_hours <= 0:

        return [
            "締切を過ぎています"
        ]

    if remaining_hours <= 24:

        reasons.append(
            "締切が24時間以内です"
        )

    elif remaining_hours <= 72:

        reasons.append(
            "締切が近づいています"
        )

    # -------------------------
    # 時間不足
    # -------------------------

    if slack_minutes < 0:

        reasons.append(
            "この締切までに必要な課題時間が、"
            "確保できる時間を超えています"
        )

    elif slack_minutes <= 60:

        reasons.append(
            "締切までの作業時間に"
            "ほとんど余裕がありません"
        )

    elif slack_minutes <= 120:

        reasons.append(
            "締切までの作業時間に"
            "あまり余裕がありません"
        )

    # -------------------------
    # 今の時間との相性
    # -------------------------

    if (
        task_remaining_minutes
        <= current_available_minutes
    ):

        reasons.append(
            "今の空き時間で"
            "終わらせられそうです"
        )

    elif (
        current_available_minutes
        >= task_remaining_minutes / 2
    ):

        reasons.append(
            "今の空き時間で"
            "大きく進められそうです"
        )

    else:

        reasons.append(
            "残り作業量が多いため、"
            "今から少し進めておくのがおすすめです"
        )

    # -------------------------
    # 進捗
    # -------------------------

    if progress >= 70:

        reasons.append(
            "かなり進んでいるため、"
            "今終わらせやすい課題です"
        )

    return reasons


# =====================================
# 推薦
# =====================================

def recommend_tasks(
    tasks,
    current_available_minutes,
    weekly_available_minutes,
    date_overrides=None,
):
    results = []

    for task in tasks:

        metrics = get_task_metrics(
            task,
            tasks,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
        )

        score = calculate_score(
            task,
            tasks,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
        )

        reasons = get_reason(
            task,
            tasks,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
        )

        results.append(
            {
                "task": task,
                "score": score["total"],
                "score_details": score,
                "reasons": reasons,
                "metrics": metrics,
            }
        )

    results.sort(
        key=lambda result:
            result["score"],
        reverse=True,
    )

    return results