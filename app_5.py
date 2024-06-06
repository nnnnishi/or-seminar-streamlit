import streamlit as st
import pandas as pd
import pulp
import matplotlib.pyplot as plt

# タイトル
st.title("シフトスケジューリングアプリ")

# サイドバー
st.sidebar.header("データのアップロード")
calendar_file = st.sidebar.file_uploader("カレンダー", type=["csv"])
staff_file = st.sidebar.file_uploader("スタッフ", type=["csv"])

# タブ
tab1, tab2, tab3 = st.tabs(["カレンダー情報", "スタッフ情報", "シフト表作成"])

with tab1:
    if calendar_file is None:
        st.write("カレンダー情報をアップロードしてください")
    else:
        st.markdown("## カレンダー情報")
        calendar_data = pd.read_csv(calendar_file)
        st.table(calendar_data)
        
with tab2:
    if staff_file is None:
        st.write("スタッフ情報をアップロードしてください")
    else:
        st.markdown("## スタッフ情報")
        staff_data = pd.read_csv(staff_file)
        st.table(staff_data)

with tab3:
    if staff_file is None:
        st.write("スタッフ情報をアップロードしてください")
    if calendar_file is None:
        st.write("カレンダー情報をアップロードしてください")
    if staff_file is not None and calendar_file is not None:
        optimize_button = st.button("最適化実行")
        if optimize_button:
            # スタッフ数とシフト数
            num_staff = staff_data.shape[0]
            num_slot = calendar_data.shape[0]

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
                    1 * [y_under[i] for i in range(num_staff)]
                    # スタッフ希望の上限より多い場合のペナルティ
                    + 1 * [y_over[i] for i in range(num_staff)]
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
                    >= calendar_data.loc[j, "出勤人数"]
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
                    >= calendar_data.loc[j, "責任者人数"]
                )

            # 最適化問題を解く
            prob.solve()
            st.markdown("## 最適化結果")

            # 最適化結果の出力
            st.write("実行ステータス:", pulp.LpStatus[prob.status])
            st.write("最適値:", pulp.value(prob.objective))

            # 最適解の出力をpandas DataFrameに格納
            x_ans = [
                [int(x[i][j].value()) for j in range(num_slot)]
                for i in range(num_staff)
            ]
            shift_schedule = pd.DataFrame(
                x_ans, index=staff_data["スタッフID"], columns=calendar_data["日付"]
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