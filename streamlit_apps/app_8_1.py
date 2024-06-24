import streamlit as st
import pandas as pd
import pulp
from src.shift_scheduler.ShiftScheduler_8_1 import ShiftScheduler

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

        ## 休暇希望の設定
        st.markdown("## 休暇希望")
        if calendar_file is None:
            st.write("カレンダー情報をアップロードしてください")
        else:
            staff_ng_date_radio_button = {}
            # スタッフIDごとにいずれかの日付、またはすべてOKにするためのラジオボタンを作成
            for i in range(len(staff_data)):
                staff_id = staff_data.loc[i, "スタッフID"]
                st.write()
                staff_ng_date_radio_button[staff_id] = st.radio(
                    staff_id,
                    ["すべてOK"]
                    + [
                        calendar_data.loc[j, "日付"]
                        for j in range(calendar_data.shape[0])
                    ],
                    horizontal=True,
                )

with tab3:
    if staff_file is None:
        st.write("スタッフ情報をアップロードしてください")
    if calendar_file is None:
        st.write("カレンダー情報をアップロードしてください")
    if staff_file is not None and calendar_file is not None:
        # スタッフごとの希望違反のペナルティをStreamlitのレバーで設定
        staff_penalty = {}
        for i, row in staff_data.iterrows():
            staff_penalty[row["スタッフID"]] = st.slider(
                f"{row['スタッフID']}の希望違反ペナルティ",
                0,  # 最小値
                100,  # 最大値
                50,  # デフォルト値は50
                key=row["スタッフID"],
            )
        optimize_button = st.button("最適化実行")
        if optimize_button:
            # ShiftSchedulerクラスのインスタンスを作成
            shift_scheduler = ShiftScheduler()
            # データをセット
            shift_scheduler.set_data(
                staff_data, calendar_data, staff_penalty, staff_ng_date_radio_button
            )
            # モデルを構築
            shift_scheduler.build_model()
            # 最適化を実行
            shift_scheduler.solve()

            st.markdown("## 最適化結果")

            # 最適化結果の出力
            st.write("実行ステータス:", pulp.LpStatus[shift_scheduler.status])
            st.write("目的関数値:", pulp.value(shift_scheduler.model.objective))

            st.markdown("## シフト表")
            st.table(shift_scheduler.sch_df)

            st.markdown("## シフト数の充足確認")
            # 各スタッフの合計シフト数をstreamlitのbar chartで表示
            shift_sum = shift_scheduler.sch_df.sum(axis=1)
            st.bar_chart(shift_sum)

            st.markdown("## スタッフの希望の確認")
            # 各スロットの合計シフト数をstreamlitのbar chartで表示
            shift_sum_slot = shift_scheduler.sch_df.sum(axis=0)
            st.bar_chart(shift_sum_slot)

            st.markdown("## 責任者の合計シフト数の充足確認")
            # shift_scheduleに対してstaff_dataをマージして責任者の合計シフト数を計算
            shift_schedule_with_staff_data = pd.merge(
                shift_scheduler.sch_df,
                staff_data,
                left_index=True,
                right_on="スタッフID",
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

            # シフト表のダウンロード
            st.download_button(
                label="シフト表をダウンロード",
                data=shift_scheduler.sch_df.to_csv().encode("utf-8"),
                file_name="output.csv",
                mime="text/csv",
            )
