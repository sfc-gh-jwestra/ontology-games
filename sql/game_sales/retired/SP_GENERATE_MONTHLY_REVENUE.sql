CREATE OR REPLACE PROCEDURE ONTOLOGY_DEMO.GAME_SALES.SP_GENERATE_MONTHLY_REVENUE("P_GAME_ID" NUMBER(38,0) DEFAULT null, "P_INCOME" FLOAT DEFAULT null)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS OWNER
AS $$
import math
import random

def run(session, P_GAME_ID, P_INCOME):
    random.seed(42)

    import json
    from datetime import date

    if P_GAME_ID is not None and P_INCOME is not None:
        games_df = session.sql(f"""
            SELECT g.GAME_ID, g.RELEASE_DATE, {float(P_INCOME)} AS INCOME,
                   ARRAY_AGG(DISTINCT mt.MONETIZATION_NAME) WITHIN GROUP (ORDER BY mt.MONETIZATION_NAME) AS MONETIZATION_MIX
            FROM ONTOLOGY_DEMO.GAMES_CORE.GAMES g
            LEFT JOIN ONTOLOGY_DEMO.GAMES_CORE.GAME_MONETIZATION gm ON g.GAME_ID = gm.GAME_ID
            LEFT JOIN ONTOLOGY_DEMO.GAMES_CORE.MONETIZATION_TYPES mt ON gm.MONETIZATION_ID = mt.MONETIZATION_ID
            WHERE g.GAME_ID = {int(P_GAME_ID)} AND g.RELEASE_DATE IS NOT NULL
            GROUP BY g.GAME_ID, g.RELEASE_DATE
        """).collect()
    elif P_GAME_ID is not None:
        games_df = session.sql(f"""
            SELECT g.GAME_ID, g.RELEASE_DATE, gr.INCOME,
                   ARRAY_AGG(DISTINCT mt.MONETIZATION_NAME) WITHIN GROUP (ORDER BY mt.MONETIZATION_NAME) AS MONETIZATION_MIX
            FROM ONTOLOGY_DEMO.GAMES_CORE.GAMES g
            JOIN ONTOLOGY_DEMO.GAME_SALES.GAME_REVENUE gr ON g.GAME_ID = gr.GAME_ID
            LEFT JOIN ONTOLOGY_DEMO.GAMES_CORE.GAME_MONETIZATION gm ON g.GAME_ID = gm.GAME_ID
            LEFT JOIN ONTOLOGY_DEMO.GAMES_CORE.MONETIZATION_TYPES mt ON gm.MONETIZATION_ID = mt.MONETIZATION_ID
            WHERE g.GAME_ID = {int(P_GAME_ID)} AND g.RELEASE_DATE IS NOT NULL AND gr.INCOME > 0
            GROUP BY g.GAME_ID, g.RELEASE_DATE, gr.INCOME
        """).collect()
    else:
        games_df = session.sql("""
            SELECT g.GAME_ID, g.RELEASE_DATE, gr.INCOME,
                   ARRAY_AGG(DISTINCT mt.MONETIZATION_NAME) WITHIN GROUP (ORDER BY mt.MONETIZATION_NAME) AS MONETIZATION_MIX
            FROM ONTOLOGY_DEMO.GAMES_CORE.GAMES g
            JOIN ONTOLOGY_DEMO.GAME_SALES.GAME_REVENUE gr ON g.GAME_ID = gr.GAME_ID
            LEFT JOIN ONTOLOGY_DEMO.GAMES_CORE.GAME_MONETIZATION gm ON g.GAME_ID = gm.GAME_ID
            LEFT JOIN ONTOLOGY_DEMO.GAMES_CORE.MONETIZATION_TYPES mt ON gm.MONETIZATION_ID = mt.MONETIZATION_ID
            WHERE g.RELEASE_DATE IS NOT NULL AND gr.INCOME > 0
            GROUP BY g.GAME_ID, g.RELEASE_DATE, gr.INCOME
        """).collect()

    if len(games_df) == 0:
        return "No games found matching criteria."

    def parse_array(val):
        if val is None:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return []
        if isinstance(val, list):
            return val
        return []

    def classify_model(mon_mix):
        has_f2p = "free_to_play" in mon_mix
        has_bp = "battle_pass" in mon_mix
        has_mtx = "microtransactions" in mon_mix
        has_dlc = "dlc" in mon_mix
        has_sp = "season_pass" in mon_mix
        has_loot = "loot_boxes" in mon_mix

        if has_f2p and (has_mtx or has_bp):
            return "f2p_live_service"
        if has_f2p:
            return "f2p_only"
        if not has_f2p and has_mtx and not has_dlc:
            return "premium_mtx"
        if not has_f2p and (has_dlc or has_loot) and has_sp:
            return "premium_dlc_season"
        if not has_f2p and (has_dlc or has_loot):
            return "premium_dlc"
        return "premium_only"

    def add_months(d, n):
        month = d.month - 1 + n
        year = d.year + month // 12
        month = month % 12 + 1
        return date(year, month, 1)

    def generate_months(release_date, total_income, model):
        months = []
        today = date.today().replace(day=1)

        windows = {
            "premium_only": 36, "premium_dlc": 48, "premium_dlc_season": 48,
            "premium_mtx": 48, "f2p_live_service": 72, "f2p_only": 36,
        }
        window = windows.get(model, 36)

        weights = []
        for m in range(window):
            if model == "premium_only":
                if m == 0: w = 40.0
                elif m == 1: w = 15.0
                elif m == 2: w = 10.0
                elif m <= 5: w = 5.0
                elif m <= 11: w = 2.0
                else: w = max(0.1, 2.0 * math.exp(-0.15 * (m - 11)))
            elif model == "premium_dlc":
                if m == 0: w = 30.0
                elif m == 1: w = 12.0
                elif m == 2: w = 8.0
                elif m <= 5: w = 4.0
                elif m <= 11: w = 1.5
                else: w = max(0.05, 1.5 * math.exp(-0.12 * (m - 11)))
                if m == 3: w += 5.0
                if m == 6: w += 4.0
                if m == 12: w += 3.0
            elif model == "premium_dlc_season":
                if m == 0: w = 25.0
                elif m == 1: w = 10.0
                elif m == 2: w = 7.0
                elif m <= 5: w = 3.5
                elif m <= 11: w = 1.5
                else: w = max(0.05, 1.0 * math.exp(-0.1 * (m - 11)))
                if m == 6: w += 6.0
                if m == 12: w += 5.0
                if m == 18: w += 4.0
            elif model == "premium_mtx":
                if m == 0: w = 20.0
                elif m == 1: w = 8.0
                elif m == 2: w = 5.0
                elif m <= 11: w = 3.0
                elif m <= 23: w = 2.5
                else: w = max(0.1, 2.0 * math.exp(-0.1 * (m - 23)))
            elif model == "f2p_live_service":
                if m == 0: w = 2.0
                elif m == 1: w = 5.0
                elif m == 2: w = 8.0
                elif m <= 5: w = 10.0
                elif m <= 11: w = 8.0
                elif m <= 23: w = 6.0
                elif m <= 35: w = 4.0
                else: w = max(0.2, 3.0 * math.exp(-0.08 * (m - 35)))
                if m > 2 and m % 3 == 0: w += 2.0
            elif model == "f2p_only":
                if m == 0: w = 3.0
                elif m <= 2: w = 8.0
                elif m <= 5: w = 6.0
                elif m <= 11: w = 3.0
                else: w = max(0.1, 2.0 * math.exp(-0.15 * (m - 11)))
            else:
                w = max(0.1, 10.0 * math.exp(-0.1 * m))

            w *= (1.0 + random.uniform(-0.10, 0.10))
            month_date = add_months(release_date, m)
            if month_date.month in (11, 12) and m > 0:
                w *= 1.3
            weights.append((m, w, month_date))

        total_w = sum(w for _, w, _ in weights)
        if total_w == 0:
            return []

        cumulative = 0.0
        for m, w, month_date in weights:
            if month_date > today:
                break
            income = round(total_income * (w / total_w), 2)
            cumulative += income

            if m == 0: source = "launch"
            elif model in ("premium_dlc", "premium_dlc_season") and m in (3, 6, 12, 18): source = "dlc_bump"
            elif model == "f2p_live_service" and m > 2 and m % 3 == 0: source = "seasonal"
            elif m <= 6: source = "ongoing"
            else: source = "tail"

            months.append((month_date, income, cumulative, source))
        return months

    if P_GAME_ID is not None:
        session.sql(f"DELETE FROM ONTOLOGY_DEMO.GAME_SALES.MONTHLY_REVENUE WHERE GAME_ID = {int(P_GAME_ID)}").collect()
    else:
        session.sql("TRUNCATE TABLE ONTOLOGY_DEMO.GAME_SALES.MONTHLY_REVENUE").collect()

    all_rows = []
    for row in games_df:
        game_id = row["GAME_ID"]
        release_date = row["RELEASE_DATE"]
        income = row["INCOME"]
        mon_mix = parse_array(row["MONETIZATION_MIX"])

        if release_date is None or income is None or income <= 0:
            continue

        if isinstance(release_date, str):
            from datetime import datetime
            release_date = datetime.strptime(release_date, "%Y-%m-%d").date()

        release_first = release_date.replace(day=1)
        model = classify_model(mon_mix)
        months = generate_months(release_first, income, model)

        for month_date, monthly_income, cumulative, source in months:
            all_rows.append((game_id, month_date.strftime("%Y-%m-%d"), monthly_income, cumulative, source))

    batch_size = 200
    for i in range(0, len(all_rows), batch_size):
        batch = all_rows[i:i+batch_size]
        selects = []
        for gid, md, mi, ci, src in batch:
            selects.append(f"SELECT {gid}, '{md}'::DATE, {mi}, {ci}, '{src}'")
        sql = f"""INSERT INTO ONTOLOGY_DEMO.GAME_SALES.MONTHLY_REVENUE
            (GAME_ID, REVENUE_MONTH, MONTHLY_INCOME, CUMULATIVE_INCOME, REVENUE_SOURCE)
            {" UNION ALL ".join(selects)}"""
        session.sql(sql).collect()

    mode = f"game {int(P_GAME_ID)}" if P_GAME_ID is not None else f"{len(games_df)} games"
    return f"Generated {len(all_rows)} monthly revenue rows for {mode}."
$$;
