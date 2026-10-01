"""A small, self-contained Streamlit chatbot page."""

import streamlit as st


WELCOME_MESSAGE = "안녕하세요! 샤이니 챗봇입니다. 무엇을 도와드릴까요?"
EXAMPLE_QUESTIONS = ("자기소개 해줘", "오늘 기분이 어때?", "무엇을 할 수 있어?")


def get_reply(message: str) -> str:
    """Return a sample response until an AI model is connected."""
    if "안녕" in message:
        return "안녕하세요! 만나서 반가워요 😊"
    if "자기소개" in message:
        return "저는 샤이니 챗봇이에요. 지금은 대화 화면을 시험해 볼 수 있는 예시 챗봇입니다."
    if "기분" in message:
        return "대화할 준비가 되어 있어서 좋아요. 오늘은 어떤 이야기를 나눌까요?"
    if "할 수" in message:
        return "질문을 받고 대화 내용을 화면에 남길 수 있어요. 현재 답변은 예시이며 AI 모델은 아직 연결되지 않았어요."
    return "메시지를 잘 받았어요! 지금은 예시 답변을 보여드리고 있어요. AI 모델을 연결하면 더 다양한 질문에 답할 수 있습니다."


def main() -> None:
    st.set_page_config(page_title="샤이니 챗봇", page_icon="✨", layout="centered")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": WELCOME_MESSAGE}]

    with st.sidebar:
        st.title("✨ 샤이니 챗봇")
        st.caption("Streamlit으로 만든 첫 번째 채팅 페이지")
        if st.button("대화 초기화", key="reset_chat", use_container_width=True):
            st.session_state.messages = [
                {"role": "assistant", "content": WELCOME_MESSAGE}
            ]
            st.rerun()
        st.divider()
        st.info("현재는 예시 답변을 사용합니다. AI 모델은 아직 연결되지 않았어요.")

    st.title("✨ 샤이니 챗봇")
    st.write("궁금한 것을 입력하거나 아래 예시 질문을 눌러보세요.")

    columns = st.columns(len(EXAMPLE_QUESTIONS))
    example_prompt = None
    for index, (column, question) in enumerate(zip(columns, EXAMPLE_QUESTIONS)):
        with column:
            if st.button(question, key=f"example_{index}", use_container_width=True):
                example_prompt = question

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("메시지를 입력하세요") or example_prompt
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        reply = get_reply(prompt)
        st.session_state.messages.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)


if __name__ == "__main__":
    main()
