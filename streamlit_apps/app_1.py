import streamlit as st

# タイトル
st.title("シフトスケジューリングアプリ")

# サイドバー
st.sidebar.header("データのアップロード")

# タブ
tab1, tab2, tab3 = st.tabs(["カレンダー情報", "スタッフ情報", "シフト表作成"])

with tab1:
    st.markdown("## カレンダー情報")

with tab2:
    st.markdown("## スタッフ情報")

with tab3:
    st.markdown("## 最適化結果")
    st.markdown("## シフト表")
    st.markdown("## シフト数の充足確認")
    st.markdown("## スタッフの希望の確認")
    st.markdown("## 責任者の合計シフト数の充足確認")
