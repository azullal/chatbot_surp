import streamlit as st

from chatbot import process_input

st.set_page_config(
    page_title="Owens Valley Paiute Chatbot",
    page_icon="💬",
    layout="centered"
)

st.title("Owens Valley Paiute Chatbot")

st.write(
    "Ask a question about Owens Valley Paiute vocabulary. "
    "You can request definitions, word lists, example sentences, or slide outlines."

)

if "messages" not in st.session_state:
    st.session_state.messages = []


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


prompt = st.chat_input(
    "Example: What is the Paiute word for water?"
)


if prompt:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = process_input(prompt)

                if isinstance(result, dict):
                    response = result.get("content", str(result))
                else:
                    response = str(result)

            except Exception as e:
                response = f"Sorry, something went wrong: {e}"

            st.markdown(response)

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )