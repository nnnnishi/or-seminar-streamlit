import streamlit as st
import pandas as pd
import pulp

# タイトル
st.title("シフトスケジューリングアプリ")

# サイドバー
st.sidebar.header("データのアップロード")
slot_file = st.sidebar.file_uploader("カレンダー", type=["csv"])
staff_file = st.sidebar.file_uploader("スタッフ", type=["csv"])

# タブ
tab3, tab2, tab1 = st.tabs(["カレンダー情報", "スタッフ情報", "シフト表作成"])

# メイン画面
with tab3:
    if slot_file is not None:
        st.markdown("## カレンダー情報")
        slot_data = pd.read_csv(slot_file)
        st.table(slot_data)
    else:
        st.write("カレンダー情報をアップロードしてください")

with tab2:
    if staff_file is not None:
        staff_data = pd.read_csv(staff_file)
        st.markdown("## スタッフ情報")
        st.table(staff_data)

        ## 休暇希望の設定
        st.markdown("## 休暇希望")
        if slot_file is not None:
            staff_ng_date_radio_button = {}
            # スタッフIDごとにいずれかの日付、またはすべてOKにするためのラジオボタンを作成
            for i in range(len(staff_data)):
                staff_id = staff_data.loc[i, "スタッフID"]
                st.write()
                staff_ng_date_radio_button[staff_id] = st.radio(
                    staff_id,
                    ["すべてOK"]
                    + [slot_data.loc[j, "日付"] for j in range(len(slot_data))],
                    horizontal=True,
                )
        else:
            st.write("カレンダー情報をアップロードしてください")

    else:
        st.write("スタッフ情報をアップロードしてください")


with tab1:
    if staff_file is None:
        st.write("スタッフ情報をアップロードしてください")
    if slot_file is None:
        st.write("カレンダー情報をアップロードしてください")
    if staff_file is not None and slot_file is not None:
        penalty_min = st.slider("下限ペナルティ", 0, 100, 50)
        penalty_max = st.slider("上限ペナルティ", 0, 100, 50)
        optimize_button = st.button("最適化実行")
        if optimize_button:
            # 最適化処理
            # スタッフ数とシフト数
            num_staff = len(staff_data)
            num_slot = len(slot_data)

            # 問題の定義
            prob = pulp.LpProblem("Shift_Scheduling", pulp.LpMinimize)

            # 変数の定義
            x = pulp.LpVariable.dicts(
                "x", (range(num_staff), range(num_slot)), cat="Binary"
            )
            y_over = pulp.LpVariable.dicts("y_over", range(num_staff), cat="Continuous")
            y_under = pulp.LpVariable.dicts(
                "y_under", range(num_staff), cat="Continuous"
            )
            # 目的関数の定義
            prob += pulp.lpSum(
                [
                    # スタッフ希望の下限より少ない場合のペナルティ
                    penalty_min * [y_under[i] for i in range(num_staff)]
                    # スタッフ希望の上限より多い場合のペナルティ
                    + penalty_max * [y_over[i] for i in range(num_staff)]
                ]
            )
            # 制約条件の定義
            # y = max(x, 0)はyの最小化が目的関数の場合はyをcontinuousとして以下のように表現できる
            # x - y <= 0
            # y >= 0
            for i in range(num_staff):
                # 希望最小出勤日数より少ない場合のペナルティ
                prob += (
                    staff_data.loc[i, "希望最小出勤日数"]
                    - pulp.lpSum([x[i][j] for j in range(num_slot)])
                    - y_under[i]
                    <= 0
                )
                prob += y_under[i] >= 0

                # 希望最大出勤日数より多い場合のペナルティ
                prob += (
                    pulp.lpSum([x[i][j] for j in range(num_slot)])
                    - staff_data.loc[i, "希望最大出勤日数"]
                    - y_over[i]
                    <= 0
                )
                prob += y_over[i] >= 0

            # 各スロットの必要人数
            for j in range(num_slot):
                prob += (
                    pulp.lpSum([x[i][j] for i in range(num_staff)])
                    >= slot_data.loc[j, "出勤人数"]
                )

            # 責任者の人数の制約
            for j in range(num_slot):
                prob += (
                    pulp.lpSum(
                        [
                            x[i][j] * staff_data.loc[i, "責任者フラグ"]
                            for i in range(num_staff)
                        ]
                    )
                    >= slot_data.loc[j, "責任者人数"]
                )
            # 指定休の制約
            for i in range(num_staff):
                if (
                    staff_ng_date_radio_button[staff_data.loc[i, "スタッフID"]]
                    != "すべてOK"
                ):
                    for j in range(num_slot):

                        if (
                            slot_data.loc[j, "日付"]
                            == staff_ng_date_radio_button[
                                staff_data.loc[i, "スタッフID"]
                            ]
                        ):
                            prob += x[i][j] == 0
            # 最適化問題を解く
            prob.solve()
            st.markdown("## 最適化結果")

            # 最適化結果の出力
            st.write("Status:", pulp.LpStatus[prob.status])
            st.write("Optimal Value:", pulp.value(prob.objective))

            # 最適解の出力をpandas DataFrameに格納
            x_ans = [
                [int(x[i][j].value()) for j in range(num_slot)]
                for i in range(num_staff)
            ]
            shift_schedule = pd.DataFrame(
                x_ans, index=staff_data["スタッフID"], columns=slot_data["日付"]
            )

            st.markdown("## シフト表")
            st.table(shift_schedule)

            st.markdown("## シフト数の充足確認")
            # 各スタッフの合計シフト数をstreamlitのbar chartで表示
            shift_sum = shift_schedule.sum(axis=1)
            st.bar_chart(shift_sum)

            st.markdown("## スタッフの希望の確認")
            # 各スロットの合計シフト数をstreamlitのbar chartで表示
            shift_sum_slot = shift_schedule.sum(axis=0)
            st.bar_chart(shift_sum_slot)

            st.markdown("## 責任者の合計シフト数の充足確認")
            # shift_scheduleに対してstaff_dataをマージして責任者の合計シフト数を計算
            shift_schedule_with_staff_data = pd.merge(
                shift_schedule, staff_data, left_index=True, right_on="スタッフID"
            )
            shift_chief_only = shift_schedule_with_staff_data.query("責任者フラグ == 1")
            shift_chief_only = shift_chief_only.drop(
                columns=[
                    "スタッフID",
                    "責任者フラグ",
                    "希望最小出勤日数",
                    "希望最大出勤日数",
                ]
            )
            shift_chief_sum = shift_chief_only.sum(axis=0)
            st.bar_chart(shift_chief_sum)