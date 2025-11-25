import streamlit as st
from openai import OpenAI

# Streamlit のシークレットに入れた API キーを使う
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# ==== 計算ロジック ====
def calc_targets(height_cm: float, weight_kg: float, activity_level: str, disease: str):
    """
    身長・体重・活動量・疾患から
    BMI, 標準体重, 目標エネルギー, たんぱく質, 塩分を計算
    ※数値はあくまで例（先生の方針で自由に調整してください）
    """
    height_m = height_cm / 100
    bmi = weight_kg / (height_m ** 2)

    # BMI 22 を標準体重とする例
    std_weight = (height_m ** 2) * 22

    # 活動量ごとの係数（例）
    if activity_level == "軽い":
        kcal_per_kg = 25
    elif activity_level == "普通":
        kcal_per_kg = 30
    elif activity_level == "重い":
        kcal_per_kg = 35
    else:
        kcal_per_kg = 30

    energy = std_weight * kcal_per_kg

    # 疾患ごとのたんぱく制限（例）
    if "腎" in disease or "CKD" in disease:
        protein_per_kg = 0.8
    else:
        protein_per_kg = 1.0

    protein = std_weight * protein_per_kg

    # 塩分量（ここも方針に応じて調整）
    salt = 6.0

    return {
        "bmi": bmi,
        "std_weight": std_weight,
        "energy": energy,
        "protein": protein,
        "salt": salt,
    }


def make_prompt(name: str, age: int, sex: str, disease: str, result: dict) -> str:
    """
    ChatGPT に渡す日本語プロンプト
    """
    return f"""
あなたは日本の内科クリニックで働く管理栄養士です。
医師の方針に沿って、患者さんにわかりやすく・優しく説明してください。
専門用語はできるだけ避け、難しい言葉にはかんたんな説明をつけてください。

【患者情報】
- 患者名: {name}
- 年齢: {age} 歳
- 性別: {sex}
- 主な疾患: {disease}
- BMI: {result['bmi']:.1f}
- 標準体重: {result['std_weight']:.1f} kg
- 1日の目標エネルギー: {result['energy']:.0f} kcal
- 1日の目標たんぱく質: {result['protein']:.0f} g
- 1日の目標塩分: {result['salt']:.1f} g

【出力してほしい内容】
1. 最初に「本日の栄養目標」を箇条書きでまとめてください。
2. 朝・昼・夕・間食ごとに、具体的な食品やメニュー例を2〜3個ずつ挙げてください。
   - 日本の一般的な家庭で用意しやすいメニューにしてください。
3. 食べ方のポイント（ゆっくり食べる・野菜から食べる など）を3つ程度示してください。
4. 最後に、患者さんを励ます一言メッセージを書いてください。

文章はすべて「です・ます調」で、日本語で書いてください。
    """.strip()


def generate_advice(name: str, age: int, sex: str, disease: str, result: dict) -> str:
    """
    OpenAI の API を使って栄養指導文を作る
    """
    prompt = make_prompt(name, age, sex, disease, result)

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",  # 必要に応じて gpt-4.1 / gpt-5.1 なども可
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that writes Japanese nutritional advice for clinic patients."
            },
            {
                "role": "user",
                "content": prompt
            },
        ],
    )

    return resp.choices[0].message.content


def main():
    st.set_page_config(page_title="栄養サポート（デモ）", layout="centered")

    st.title("栄養サポートアプリ")
    st.write("身長・体重・病気などを入力すると、1日の栄養の目安と、具体的な食事の例を表示します。")
    st.info("※このアプリは一般的な目安です。主治医・管理栄養士の指示を必ず優先してください。")

    with st.form(key="input_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("お名前（ニックネームでも可）", value="")
            age = st.number_input("年齢（歳）", min_value=10, max_value=100, value=40, step=1)
        with col2:
            sex = st.selectbox("性別", options=["指定しない", "男性", "女性", "その他"])

        height = st.number_input("身長（cm）", min_value=120.0, max_value=220.0, value=165.0, step=0.5)
        weight = st.number_input("体重（kg）", min_value=30.0, max_value=200.0, value=65.0, step=0.5)

        disease = st.text_input("主な病気（例：2型糖尿病、CKD3、高血圧、脂質異常症など）", value="2型糖尿病")

        activity_level = st.selectbox(
            "ふだんの活動量",
            options=["軽い（座り仕事が多い）", "普通（立ち仕事・よく歩く）", "重い（力仕事が多い）"],
            index=1,
        )

        if activity_level.startswith("軽い"):
            activity_key = "軽い"
        elif activity_level.startswith("普通"):
            activity_key = "普通"
        else:
            activity_key = "重い"

        submitted = st.form_submit_button("栄養アドバイスを作成する")

    if submitted:
        if not height or not weight:
            st.error("身長と体重を入力してください。")
            return

        result = calc_targets(height, weight, activity_key, disease)

        st.subheader("① あなたの1日の目安（計算結果）")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"- BMI：**{result['bmi']:.1f}**")
            st.write(f"- 標準体重（目安）：**{result['std_weight']:.1f} kg**")
        with col2:
            st.write(f"- 1日の目標エネルギー：**{result['energy']:.0f} kcal**")
            st.write(f"- たんぱく質の目安：**{result['protein']:.0f} g/日**")
            st.write(f"- 塩分量の目安：**{result['salt']:.1f} g/日 以下**")

        st.markdown("---")
        st.subheader("② 食事のとり方・メニューの例（AIによる提案）")

        with st.spinner("栄養アドバイスを作成中です…"):
            advice = generate_advice(name or "あなた", int(age), sex, disease, result)

        st.write(advice)

        st.markdown("---")
        st.caption("※この内容はAIによる一般的な提案です。実際の治療方針・栄養指導は必ず主治医・管理栄養士にご確認ください。")


if __name__ == "__main__":
    main()
