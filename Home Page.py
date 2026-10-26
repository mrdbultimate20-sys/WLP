
import streamlit as st

st.set_page_config(
    page_title="St. Louis Wildlife Project",
    page_icon="🌿",
    layout="wide",
)

st.title("St. Louis Wildlife Project")
st.write(
    "Discover local wildlife, explore observations, "
    "and learn about the projects making a difference."
)

# EDIT THE TEXT BELOW ANYTIME YOU WANT TO UPDATE YOUR HOMEPAGE.

left_box, right_box = st.columns(2, gap="large")

with left_box:
    with st.container(border=True):
        st.subheader("About the St. Louis Wildlife Project")

        st.write(
            "The St. Louis Wildlife Project is dedicated to "
            "exploring, documenting, and learning about wildlife "
            "in the St. Louis area."
        )

        st.write(
            "Browse wildlife observations and help build a "
            "better understanding of the animals that share "
            "our local environment."
        )

with right_box:
    with st.container(border=True):
        st.subheader("About the Bioluminescent Rams")

        st.write(
            "Add your introduction to the Bioluminescent Rams here. "
            "Explain who you are, what your project does, and "
            "why it matters."
        )

        st.write(
            "You can change this text whenever you like by "
            "editing the words in Home Page.py."
        )

