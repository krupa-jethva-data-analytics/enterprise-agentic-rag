import os
import streamlit as st
import requests
import time
import uuid
import logfire

from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

env_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".env")
)

load_dotenv(dotenv_path=env_path)


# ============================================================
# LOGFIRE
# ============================================================

try:
    token = os.getenv("LOGFIRE_TOKEN")

    if not token:
        print("ERROR: LOGFIRE_TOKEN is empty or None!")

    logfire.configure(token=token)

    LOGFIRE_STATUS = "Connected & Tracing"

except Exception as e:

    print(f"Logfire Init Error in UI: {e}")

    LOGFIRE_STATUS = f"Standby (Error: {e})"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Enterprise Agentic RAG",
    page_icon="🤖",
    layout="wide",
)


# ============================================================
# AVATARS
# ============================================================

AI_AVATAR = "🤖"
USER_AVATAR = "👤"


# ============================================================
# SESSION MANAGEMENT
# ============================================================

if "session_id" not in st.session_state:

    st.session_state.session_id = str(uuid.uuid4())

    logfire.info(
        f"✨ New User Session Created: "
        f"{st.session_state.session_id}"
    )


if "messages" not in st.session_state:

    st.session_state.messages = []


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🧠 Agent OS")

    st.markdown("---")

    st.success(
        f"Logfire: {LOGFIRE_STATUS}"
    )

    st.info(
        f"Memory ID: "
        f"{st.session_state.session_id[:8]}"
    )

    if st.button(
        "🗑️ Clear History & Memory",
        width="stretch",
        type="primary"
    ):

        logfire.warning(
            f"🗑️ Memory Wipe Triggered: "
            f"{st.session_state.session_id}"
        )

        st.session_state.messages = []

        st.session_state.session_id = str(
            uuid.uuid4()
        )

        st.rerun()


# ============================================================
# MAIN CHAT
# ============================================================

st.title("🤖 Enterprise Agentic Assistant")


# Display previous messages
for message in st.session_state.messages:

    avatar = (
        AI_AVATAR
        if message["role"] == "assistant"
        else USER_AVATAR
    )

    with st.chat_message(
        message["role"],
        avatar=avatar
    ):
        st.markdown(message["content"])


# ============================================================
# CHAT INPUT
# ============================================================

if prompt := st.chat_input(
    "Ask about your documentation..."
):

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )


    with logfire.span(
        "💬 User Chat Interaction",
        user_query=prompt,
        session_id=st.session_state.session_id
    ):

        # ----------------------------------------------------
        # Display user message
        # ----------------------------------------------------

        with st.chat_message(
            "user",
            avatar=USER_AVATAR
        ):
            st.markdown(prompt)


        # ----------------------------------------------------
        # Assistant
        # ----------------------------------------------------

        with st.chat_message(
            "assistant",
            avatar=AI_AVATAR
        ):

            with st.status(
                "🔍 Agent is thinking...",
                expanded=True
            ) as status:

                try:

                    # ==================================================
                    # CALL FASTAPI BACKEND
                    # ==================================================

                    with logfire.span(
                        "📡 Calling RAG Backend"
                    ):

                        base_url = os.getenv(
                            "BACKEND_URL",
                            "http://127.0.0.1:8000"
                        )

                        # Remove accidental trailing /
                        base_url = base_url.rstrip("/")

                        url = f"{base_url}/query"


                        payload = {
                            "q": prompt,
                            "thread_id": (
                                st.session_state.session_id
                            )
                        }


                        response = requests.post(
                            url,
                            json=payload,
                            timeout=60
                        )


                        # Raise an exception for HTTP errors
                        response.raise_for_status()


                        # Convert JSON response
                        data = response.json()


                    # ==================================================
                    # DEBUG - SEE WHAT FASTAPI ACTUALLY SENT
                    # ==================================================

                    # TEMPORARY:
                    # Keep this while debugging.
                    with st.expander(
                        "🔧 Backend Response (Debug)"
                    ):
                        st.json(data)


                    # ==================================================
                    # SHOW REASONING / PLAN
                    # ==================================================

                    steps = data.get(
                        "thought_process",
                        []
                    )

                    for step in steps:

                        st.write(
                            f"⚙️ {step}"
                        )


                    # ==================================================
                    # SHOW SOURCES
                    # ==================================================

                    sources = data.get(
                        "sources",
                        []
                    )

                    if sources:

                        with st.expander(
                            "📄 View Retrieved Context"
                        ):

                            for i, source in enumerate(
                                sources
                            ):

                                preview = (
                                    source[:100]
                                    .replace("\n", " ")
                                    + "..."
                                )

                                with st.expander(
                                    f"Chunk {i + 1}: {preview}"
                                ):

                                    st.info(source)


                    # ==================================================
                    # GET ANSWER
                    # ==================================================

                    full_answer = data.get(
                        "answer"
                    )


                    # ------------------------------------------------
                    # If answer is missing/null
                    # ------------------------------------------------

                    if not full_answer:

                        status.update(
                            label="⚠️ Backend returned no answer",
                            state="error",
                            expanded=True
                        )

                        st.error(
                            "The backend completed the graph "
                            "but did not return an answer."
                        )

                        st.write(
                            "Backend response:"
                        )

                        st.json(data)

                        st.stop()


                    # ==================================================
                    # SUCCESS
                    # ==================================================

                    status.update(
                        label="✅ Answer Synthesized",
                        state="complete",
                        expanded=False
                    )


                except requests.exceptions.ConnectionError:

                    logfire.error(
                        "❌ Cannot connect to FastAPI backend."
                    )

                    status.update(
                        label="❌ Backend Offline",
                        state="error"
                    )

                    st.error(
                        "Cannot connect to the FastAPI backend."
                    )

                    st.stop()


                except requests.exceptions.Timeout:

                    logfire.error(
                        "❌ Backend request timed out."
                    )

                    status.update(
                        label="❌ Request Timed Out",
                        state="error"
                    )

                    st.error(
                        "The backend took too long to respond."
                    )

                    st.stop()


                except requests.exceptions.HTTPError as e:

                    logfire.error(
                        f"❌ Backend HTTP Error: {e}"
                    )

                    status.update(
                        label="❌ Backend Error",
                        state="error"
                    )

                    st.error(
                        f"Backend returned an error: {e}"
                    )

                    st.stop()


                except Exception as e:

                    logfire.error(
                        f"❌ UI-Backend Error: {e}"
                    )

                    status.update(
                        label="❌ Error",
                        state="error"
                    )

                    st.error(
                        f"Unexpected error: {e}"
                    )

                    st.stop()


            # ========================================================
            # DISPLAY ANSWER
            # ========================================================

            answer_placeholder = st.empty()

            curr_text = ""

            for char in full_answer:

                curr_text += char

                answer_placeholder.markdown(
                    curr_text + "▌"
                )

                time.sleep(0.005)


            answer_placeholder.markdown(
                full_answer
            )


            # ========================================================
            # SAVE ASSISTANT MESSAGE
            # ========================================================

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": full_answer
                }
            )


            logfire.info(
                "✅ Chat cycle completed successfully."
            )