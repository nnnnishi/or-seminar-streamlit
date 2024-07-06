import pandas as pd
import pulp
import streamlit as st


class ShiftScheduler:
    def __init__(self):
        # リスト
        self.S = []  # スタッフのリスト
        self.D = []  # 日付のリスト
        self.SD = []  # スタッフと日付の組のリスト

        # 定数
        self.S2leader_flag = {}  # スタッフの責任者フラグ
        self.S2min_shift = {}  # スタッフの希望最小出勤日数
        self.S2max_shift = {}  # スタッフの希望最大出勤日数
        self.D2required_staff = {}  # 各日の必要人数
        self.D2required_leader = {}  # 各日の必要責任者数

        # 変数
        self.x = {}  # 各スタッフが各日にシフトに入るか否かを表す変数
        self.y_under = {}  # 各スタッフの希望勤務日数の不足数を表すスラック変数
        self.y_over = {}  # 各スタッフの希望勤務日数の超過数を表すスラック変数

        # 数理モデル
        self.model = None

        # 最適化結果
        self.status = -1  # 最適化結果のステータス
        self.sch_df = None  # シフト表を表すデータフレーム

    def set_data(self, staff_df, calendar_df):
        # リストの設定
        self.S = staff_df["スタッフID"].tolist()
        self.D = calendar_df["日付"].tolist()
        self.SD = [(s, d) for s in self.S for d in self.D]

        # 定数の設定
        S2Dic = staff_df.set_index("スタッフID").to_dict()
        self.S2leader_flag = S2Dic["責任者フラグ"]
        self.S2min_shift = S2Dic["希望最小出勤日数"]
        self.S2max_shift = S2Dic["希望最大出勤日数"]

        D2Dic = calendar_df.set_index("日付").to_dict()
        self.D2required_staff = D2Dic["出勤人数"]
        self.D2required_leader = D2Dic["責任者人数"]

    def show(self):
        print("=" * 50)
        print("Staffs:", self.S)
        print("Dates:", self.D)
        print("Staff-Date Pairs:", self.SD)

        print("Staff Leader Flag:", self.S2leader_flag)
        print("Staff Max Shift:", self.S2max_shift)
        print("Staff Min Shift:", self.S2min_shift)

        print("Date Required Staff:", self.D2required_staff)
        print("Date Required Leader:", self.D2required_leader)
        print("=" * 50)

    def build_model(self):
        ### 数理モデルの定義 ###
        self.model = pulp.LpProblem("ShiftScheduler", pulp.LpMinimize)

        ### 変数の定義 ###
        # 各スタッフの各日に対して、シフトに入るなら1、シフトに入らないなら0
        self.x = pulp.LpVariable.dicts("x", self.SD, cat="Binary")

        # 各スタッフの勤務希望日数の不足数を表すためのスラック変数
        self.y_under = pulp.LpVariable.dicts(
            "y_under", self.S, cat="Continuous", lowBound=0
        )

        # 各スタッフの勤務希望日数の超過数を表すためのスラック変数
        self.y_over = pulp.LpVariable.dicts(
            "y_over", self.S, cat="Continuous", lowBound=0
        )

        ### 制約式の定義 ###
        # 各日に対して、必要な人数がシフトに入る
        for d in self.D:
            self.model += (
                pulp.lpSum(self.x[s, d] for s in self.S) >= self.D2required_staff[d]
            )

        # 各日に対して、必要なリーダーの人数がシフトに入る
        for d in self.D:
            self.model += (
                pulp.lpSum(self.x[s, d] * self.S2leader_flag[s] for s in self.S)
                >= self.D2required_leader[d]
            )

        ### 目的関数とスラック変数の定義 ###
        # 各スタッフの勤務希望日数の不足数と超過数を最小化する
        self.model += pulp.lpSum([self.y_under[s] for s in self.S]) + pulp.lpSum(
            [self.y_over[s] for s in self.S]
        )

        # 各スタッフに対して、y_under[s]は勤務希望日数の不足数を表す
        for s in self.S:
            self.model += (
                self.S2min_shift[s] - pulp.lpSum(self.x[s, d] for d in self.D)
                <= self.y_under[s]
            )

        # 各スタッフに対して、y_over[s]は勤務希望日数の超過数を表す
        for s in self.S:
            self.model += (
                pulp.lpSum(self.x[s, d] for d in self.D) - self.S2max_shift[s]
                <= self.y_over[s]
            )

    def solve(self):
        solver = pulp.PULP_CBC_CMD(msg=0)
        self.status = self.model.solve(solver)

        print("status:", pulp.LpStatus[self.status])
        print("objective:", self.model.objective.value())

        Rows = [[int(self.x[s, d].value()) for d in self.D] for s in self.S]
        self.sch_df = pd.DataFrame(Rows, index=self.S, columns=self.D)


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
            # ShiftSchedulerクラスのインスタンスを作成
            shift_scheduler = ShiftScheduler()
            # データをセット
            shift_scheduler.set_data(staff_data, calendar_data)
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
    st.markdown("## スタッフの希望の確認")
    st.markdown("## 責任者の合計シフト数の充足確認")
