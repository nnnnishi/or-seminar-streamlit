import cvxpy as cp
import pandas as pd


class ShiftScheduler:
    def __init__(self):
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

        # スタッフごとの重みペナルティ、各スタッフについてデフォルトは50として辞書を作成
        self.S2penalty_weight = {s: 50 for s in self.S}

    def set_data(self, staff_df, calendar_df, staff_penalty):
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

        # スタッフ希望違反のペナルティーの設定
        self.S2penalty_weight = staff_penalty

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

        print("Staff Penalty Weight:", self.S2penalty_weight)
        print("=" * 50)

    def build_model(self):
        # 変数の定義
        self.x = cp.Variable((len(self.S), len(self.D)), boolean=True)
        self.y_under = cp.Variable(len(self.S), nonneg=True)
        self.y_over = cp.Variable(len(self.S), nonneg=True)

        # 制約条件の定義
        constraints = []

        # 各日の必要人数制約
        for d in range(len(self.D)):
            constraints.append(cp.sum(self.x[:, d]) >= self.D2required_staff[self.D[d]])

        # 各日の必要責任者数制約
        for d in range(len(self.D)):
            constraints.append(
                cp.sum(
                    cp.multiply(self.x[:, d], [self.S2leader_flag[s] for s in self.S])
                )
                >= self.D2required_leader[self.D[d]]
            )

        # 各スタッフの勤務日数制約
        for s in range(len(self.S)):
            constraints.append(
                self.S2min_shift[self.S[s]] - cp.sum(self.x[s, :]) <= self.y_under[s]
            )
            constraints.append(
                cp.sum(self.x[s, :]) - self.S2max_shift[self.S[s]] <= self.y_over[s]
            )

        # 目的関数の定義
        objective = cp.Minimize(
            cp.sum_squares(
                cp.multiply(
                    [self.S2penalty_weight[s] for s in self.S],
                    (self.y_under + self.y_over),
                )
            )
        )

        # 問題の定義
        self.prob = cp.Problem(objective, constraints)

    def solve(self):
        self.prob.solve()

        if self.prob.status == cp.OPTIMAL:
            print("Optimal value:", self.prob.value)
            self.sch_df = pd.DataFrame(
                self.x.value.astype(int), index=self.S, columns=self.D
            )
        else:
            print("Problem status:", self.prob.status)


if __name__ == "__main__":
    staff_df = pd.read_csv("data/staff.csv")
    calendar_df = pd.read_csv("data/calendar.csv")
    staff_penalty = {s: 50 for s in staff_df["スタッフID"]}

    shift_sch = ShiftScheduler()
    shift_sch.set_data(staff_df, calendar_df, staff_penalty)
    shift_sch.show()
    shift_sch.build_model()
    shift_sch.solve()
    print(shift_sch.sch_df)
