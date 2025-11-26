import streamlit as st
import openai
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


def make_prompt(name: str, age: int, sex: str, disease: str, result: dict, diary: dict) -> str:
    """
    ChatGPT に渡す日本語プロンプト（目標 + 今日食べた内容へのフィードバック）
    """
    return f"""
あなたは日本の内科クリニックで働く管理栄養士です。
以下の患者さんの情報と、1日の栄養目標、実際に食べた内容をもとに、
やさしく分かりやすくフィードバックをしてください。

【患者情報】
- 患者名: {name}
- 年齢: {age} 歳
- 性別: {sex}
- 主な疾患: {disease}

【本日の目標】
- BMI: {result['bmi']:.1f}
- 標準体重: {result['std_weight']:.1f} kg
- 1日の目標エネルギー: {result['energy']:.0f} kcal
- 1日の目標たんぱく質: {result['protein']:.0f} g
- 1日の目標塩分: {result['salt']:.1f} g 以下

【本日患者さんが実際に食べた内容】
- 朝食: {diary["breakfast"] or "（記載なし）"}
- 昼食: {diary["lunch"] or "（記載なし）"}
- 夕食: {diary["dinner"] or "（記載なし）"}
- 間食・飲み物: {diary["snack"] or "（記載なし）"}

【出力してほしい内容】
1. まず「本日の総評」を2〜3文で書いてください。
2. 次に、良かった点を3つ、箇条書きで挙げてください。
3. 改善できそうな点を3つ、箇条書きで挙げてください。
   - 具体的に「◯◯を△△に置き換える」「ご飯の量を○割減らす」など、実行しやすい表現にしてください。
4. 朝・昼・夕・間食ごとに、それぞれ1〜2つずつ「明日からすぐ試せる工夫」を提案してください。
5. 最後に、患者さんを励ます一言メッセージを書いてください。

注意点:
- カロリーやたんぱく質量は、あくまでおおよそのイメージで構いません。細かい数字は出さなくて大丈夫です。
- 患者さんを責めるような言い方は絶対に避けてください。
- ポジティブな部分を必ず見つけ、そこを評価しながら、無理のない改善案を提案してください。
- 文章はすべて「です・ます調」で、日本語で書いてください。
    """.strip()


def generate_advice(name: str, age: int, sex: str, disease: str, result: dict, diary: dict) -> str:
    """
    OpenAI の API を使って栄養指導文を作る
    """
    prompt = make_prompt(name, age, sex, disease, result, diary)

    try:
        resp = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that writes Japanese nutritional feedback for clinic patients based on what they actually ate."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
        )
        return resp.choices[0].message.content

    except openai.RateLimitError:
        return (
            "【現在AIサーバー側の利用上限に達しているか、APIの残高が不足しています。】\n"
            "しばらく時間をおいてから再度お試しください。\n"
            "改善しない場合は、クリニック側でご確認ください。"
        )
    except Exception:
        # 予期しないエラーの場合も、患者さんには優しいメッセージを返す
        return (
            "【現在AIからの回答に問題が発生しています。】\n"
            "時間をおいてからもう一度お試しください。\n"
            "改善しない場合は、クリニック側にお知らせください。"
        )


def main():
    st.set_page_config(page_title="栄養サポート（食事記録フィードバック）", layout="centered")

    st.title("栄養サポートアプリ（食事内容の振り返り）")
    st.write("身長・体重・病気などから1日の目安を出し、そのうえで『実際に食べた内容』に対してAIがやさしくフィードバックします。")
    st.info("※このアプリは一般的な目安です。実際の診断・治療・個別指導は必ず主治医・管理栄養士の指示を優先してください。")

    with st.form(key="input_form"):
        st.markdown("### ① 基本情報")
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

        st.markdown("---")
        st.markdown("### ② 本日食べた内容を入力してください")

        breakfast = st.text_area("朝食（例：ご飯1杯、味噌汁、焼き鮭、ヨーグルトなど）", height=80)
        lunch = st.text_area("昼食（例：コンビニおにぎり2個、唐揚げ、野菜ジュースなど）", height=80)
        dinner = st.text_area("夕食（例：白ご飯、豚の生姜焼き、サラダ、ビール350mlなど）", height=80)
        snack = st.text_area("間食・飲み物（例：お菓子、ジュース、アルコールなど）", height=80)

        submitted = st.form_submit_button("AIからフィードバックをもらう")

    if submitted:
        if not height or not weight:
            st.error("身長と体重を入力してください。")
            return

        result = calc_targets(height, weight, activity_key, disease)
        diary = {
            "breakfast": breakfast.strip(),
            "lunch": lunch.strip(),
            "dinner": dinner.strip(),
            "snack": snack.strip(),
        }

        st.markdown("### ③ あなたの1日の目安（計算結果）")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"- BMI：**{result['bmi']:.1f}**")
            st.write(f"- 標準体重（目安）：**{result['std_weight']:.1f} kg**")
        with col2:
            st.write(f"- 1日の目標エネルギー：**{result['energy']:.0f} kcal**")
            st.write(f"- たんぱく質の目安：**{result['protein']:.0f} g/日**")
            st.write(f"- 塩分量の目安：**{result['salt']:.1f} g/日 以下**")

        st.markdown("---")
        st.markdown("### ④ 本日の食事内容へのフィードバック（AIによる提案）")

        with st.spinner("AIが食事内容を確認しています…"):
            advice = generate_advice(name or "あなた", int(age), sex, disease, result, diary)

        st.write(advice)

        st.markdown("---")
        st.caption("※この内容はAIによる一般的な提案です。実際の治療方針・栄養指導は必ず主治医・管理栄養士にご確認ください。")


if __name__ == "__main__":
    main()
