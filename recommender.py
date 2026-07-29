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
    deadline_dt = (
        datetime.fromisoformat(
            deadline
        )
    )

    now = datetime.now()

    if deadline_dt <= now:
        return 0

    if date_overrides is None:
        date_overrides = {}

    # 今日については、
    # 「今どれくらい時間がある？」を使用
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

        # 特定日の設定があれば優先
        if date_key in date_overrides:

            total_minutes += (
                date_overrides[
                    date_key
                ]
            )

        # なければ通常の曜日設定
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
# 1つの課題についての指標
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

    # この課題の締切までに
    # 終える必要がある全課題の残り時間
    required_minutes = 0

    for other_task in all_tasks:

        other_deadline = (
            datetime.fromisoformat(
                other_task[2]
            )
        )

        if (
            other_deadline
            <= deadline_dt
        ):

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
# 全締切を順番にチェック
# =====================================

def get_schedule_summary(
    tasks,
    current_available_minutes,
    weekly_available_minutes,
    date_overrides=None,
):
    """
    締切が早い順に、

    必要時間 <= 使える時間

    が成立するか確認する。

    最初に成立しなくなる締切を
    first_shortage として返す。
    """

    if date_overrides is None:
        date_overrides = {}

    checkpoints = []

    unique_deadlines = sorted(
        {
            task[2]
            for task in tasks
        },
        key=datetime.fromisoformat,
    )

    first_shortage = None

    for deadline in unique_deadlines:

        deadline_dt = (
            datetime.fromisoformat(
                deadline
            )
        )

        available_minutes = (
            calculate_available_until(
                deadline,
                current_available_minutes,
                weekly_available_minutes,
                date_overrides,
            )
        )

        required_minutes = sum(
            calculate_remaining_minutes(
                task
            )
            for task in tasks
            if (
                datetime.fromisoformat(
                    task[2]
                )
                <= deadline_dt
            )
        )

        slack_minutes = (
            available_minutes
            - required_minutes
        )

        checkpoint = {
            "deadline":
                deadline,

            "available_minutes":
                available_minutes,

            "required_minutes":
                required_minutes,

            "slack_minutes":
                slack_minutes,
        }

        checkpoints.append(
            checkpoint
        )

        # 最初に時間不足になる地点
        if (
            first_shortage is None
            and slack_minutes < 0
        ):

            first_shortage = (
                checkpoint
            )

    return {
        "checkpoints":
            checkpoints,

        "first_shortage":
            first_shortage,
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
    schedule_summary=None,
):
    metrics = get_task_metrics(
        task,
        all_tasks,
        current_available_minutes,
        weekly_available_minutes,
        date_overrides,
    )

    if schedule_summary is None:

        schedule_summary = get_schedule_summary(
            all_tasks,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
        )

    remaining_hours = (
        metrics["remaining_hours"]
    )

    available_minutes = (
        metrics["available_minutes"]
    )

    task_remaining_minutes = (
        metrics[
            "task_remaining_minutes"
        ]
    )

    # =====================================
    # 締切超過
    # =====================================

    if remaining_hours <= 0:

        return {
            "total": 100,
            "urgency": 30,
            "risk": 50,
            "fit": 20,
        }

    # =====================================
    # 1. 締切の近さ
    # 最大30点
    # =====================================

    one_week_hours = (
        24 * 7
    )

    urgency_score = max(
        0,
        1
        - remaining_hours
        / one_week_hours,
    ) * 30

    # =====================================
    # 個別課題の負荷率
    # =====================================

    if available_minutes > 0:

        individual_workload_ratio = (
            task_remaining_minutes
            / available_minutes
        )

    elif task_remaining_minutes > 0:

        individual_workload_ratio = (
            float("inf")
        )

    else:

        individual_workload_ratio = 0

    # =====================================
    # 2. 時間不足リスク
    # 最大50点
    # =====================================

    first_shortage = (
        schedule_summary[
            "first_shortage"
        ]
    )

    if first_shortage is not None:

        first_shortage_dt = (
            datetime.fromisoformat(
                first_shortage[
                    "deadline"
                ]
            )
        )

        task_deadline_dt = (
            datetime.fromisoformat(
                task[2]
            )
        )

        # 最初に予定が破綻する締切までに
        # 終える必要がある課題は高リスク
        if (
            task_deadline_dt
            <= first_shortage_dt
        ):

            risk_score = 50

        else:

            # 破綻地点より後の課題は
            # その課題自身の負荷で評価
            risk_score = (
                min(
                    individual_workload_ratio,
                    1,
                )
                * 25
            )

    else:

        # 予定全体が間に合う場合は、
        # 累計課題量ではなく
        # その課題自身の残り作業量で評価
        risk_score = (
            min(
                individual_workload_ratio,
                1,
            )
            * 50
        )

    # =====================================
    # 3. 今の空き時間との相性
    # 最大20点
    # =====================================

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

    # =====================================
    # 合計
    # =====================================

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
        1
        - remaining_hours
        / one_week_hours,
    ) * 30

    # -------------------------
    # 2. 時間不足リスク
    # 最大50点
    # -------------------------

    first_shortage = (
        schedule_summary[
            "first_shortage"
        ]
    )

    if first_shortage is not None:

        first_shortage_dt = (
            datetime.fromisoformat(
                first_shortage[
                    "deadline"
                ]
            )
        )

        task_deadline_dt = (
            datetime.fromisoformat(
                task[2]
            )
        )

        # 最初に破綻する締切までに
        # 終える必要がある課題
        if (
            task_deadline_dt
            <= first_shortage_dt
        ):

            risk_score = 50

        else:

            # それより後の課題が
            # 不必要に上位にならないよう抑える
            risk_score = (
                min(
                    workload_ratio,
                    1,
                )
                * 25
            )

    else:

        risk_score = (
            min(
                workload_ratio,
                1,
            )
            * 50
        )

    # -------------------------
    # 3. 今の空き時間との相性
    # 最大20点
    # -------------------------

    if (
        task_remaining_minutes
        > 0
    ):

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
    schedule_summary=None,
):
    (
        task_id,
        title,
        deadline,
        estimated_minutes,
        progress,
    ) = task

    metrics = (
        get_task_metrics(
            task,
            all_tasks,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
        )
    )

    if schedule_summary is None:

        schedule_summary = (
            get_schedule_summary(
                all_tasks,
                current_available_minutes,
                weekly_available_minutes,
                date_overrides,
            )
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
    # 最初の時間不足
    # -------------------------

    first_shortage = (
        schedule_summary[
            "first_shortage"
        ]
    )

    if first_shortage is not None:

        first_shortage_dt = (
            datetime.fromisoformat(
                first_shortage[
                    "deadline"
                ]
            )
        )

        task_deadline_dt = (
            datetime.fromisoformat(
                deadline
            )
        )

        if (
            task_deadline_dt
            == first_shortage_dt
        ):

            reasons.append(
                "この締切時点で初めて、"
                f"約{abs(first_shortage['slack_minutes'])}分"
                "の時間不足が発生する見込みです"
            )

        elif (
            task_deadline_dt
            < first_shortage_dt
        ):

            reasons.append(
                "最初に時間不足が起こる締切までに"
                "終える必要がある課題です"
            )

    # -------------------------
    # 締切時点の余裕
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
    # 今の空き時間との相性
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
            "今から少し進めるのがおすすめです"
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
    schedule_summary = (
        get_schedule_summary(
            tasks,
            current_available_minutes,
            weekly_available_minutes,
            date_overrides,
        )
    )

    first_shortage = (
        schedule_summary[
            "first_shortage"
        ]
    )

    first_shortage_dt = None

    if first_shortage is not None:

        first_shortage_dt = (
            datetime.fromisoformat(
                first_shortage[
                    "deadline"
                ]
            )
        )

    results = []

    for task in tasks:

        metrics = (
            get_task_metrics(
                task,
                tasks,
                current_available_minutes,
                weekly_available_minutes,
                date_overrides,
            )
        )

        score = (
            calculate_score(
                task,
                tasks,
                current_available_minutes,
                weekly_available_minutes,
                date_overrides,
                schedule_summary,
            )
        )

        reasons = (
            get_reason(
                task,
                tasks,
                current_available_minutes,
                weekly_available_minutes,
                date_overrides,
                schedule_summary,
            )
        )

        task_deadline_dt = (
            datetime.fromisoformat(
                task[2]
            )
        )

        contributes_to_first_shortage = (
            first_shortage_dt
            is not None
            and task_deadline_dt
            <= first_shortage_dt
        )

        results.append(
            {
                "task":
                    task,

                "score":
                    score["total"],

                "score_details":
                    score,

                "reasons":
                    reasons,

                "metrics":
                    metrics,

                "schedule_summary":
                    schedule_summary,

                "contributes_to_first_shortage":
                    contributes_to_first_shortage,
            }
        )

    # -------------------------
    # 並び替え
    # -------------------------

    def sort_key(result):

        deadline_dt = (
            datetime.fromisoformat(
                result[
                    "task"
                ][2]
            )
        )

        # 締切超過を最優先
        if (
            result[
                "metrics"
            ][
                "remaining_hours"
            ]
            <= 0
        ):

            return (
                0,
                deadline_dt,
                -result["score"],
            )

        # 最初に時間不足になる地点までの課題
        # → 締切が早いものから優先
        if result[
            "contributes_to_first_shortage"
        ]:

            return (
                1,
                deadline_dt,
                -result["score"],
            )

        # それ以外は通常スコア順
        return (
            2,
            -result["score"],
            deadline_dt,
        )

    results.sort(
        key=sort_key
    )

    return results