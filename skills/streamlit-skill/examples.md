# streamlit-skill Examples

Streamlit can create user interfaces with common components like text inputs and buttons.

---

## Example 1 - Button clicks and text input

When "Check availability" is clicked, users see "We have that animal!" or "We don't have that animal."

```python
import streamlit as st

animal_shelter = ['cat', 'dog', 'rabbit', 'bird']
animal = st.text_input('Type an animal')

if st.button('Check availability'):
    have_it = animal.lower() in animal_shelter
    st.write('We have that animal!' if have_it else "We don't have that animal.")
```

---

## Example 2 - Using session state

When "Check availability" is clicked, "True" is saved to session state so the message persists across reruns.

```python
import streamlit as st

if 'clicked' not in st.session_state:
    st.session_state.clicked = False

def click_button():
    st.session_state.clicked = True

st.button('Click me', on_click=click_button)

if st.session_state.clicked:
    st.write('Button clicked!')
    st.slider('Select a value')
```

---

## Example 3 - Callbacks to manage session state

Use `on_click` with `args` to update session state when a button is pressed.

```python
import streamlit as st

if 'name' not in st.session_state:
    st.session_state['name'] = 'John Doe'

def change_name(name):
    st.session_state['name'] = name

st.header(st.session_state['name'])

st.button('Jane', on_click=change_name, args=['Jane Doe'])
st.button('John', on_click=change_name, args=['John Doe'])
```

---

## Example 4 - WARNING: Do not modify session state from multiple widgets

You cannot modify a key in `st.session_state` if a widget with that key has already been rendered in the current run. This will error:

```python
import streamlit as st

st.text_input('Name', key='name')

# These buttons will ERROR - they modify a widget's key after it was rendered
if st.button('Clear name'):
    st.session_state.name = ''
if st.button('Streamlit!'):
    st.session_state.name = 'Streamlit'
```

Use callbacks (Example 3) or a different key for the buttons instead.

---

## Example 5 - Displaying output with st.write

Use `st.write()` to display strings, DataFrames, and other objects.

```python
import streamlit as st
import pandas as pd

st.write("Here's our first attempt at using data to create a table:")
st.write(pd.DataFrame({
    'first column': [1, 2, 3, 4],
    'second column': [10, 20, 30, 40]
}))
```

---

## Example 6 - Chatbot UI (st.chat_message, st.chat_input)

Chat interface using `st.chat_message()` for message bubbles and `st.chat_input()` for user input. Message history is stored in `st.session_state.messages`.

```python
from openai import OpenAI
import streamlit as st

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", key="chatbot_api_key", type="password")
    st.markdown("[Get an OpenAI API key](https://platform.openai.com/account/api-keys)")

st.title("💬 Chatbot")
st.caption("🚀 A Streamlit chatbot powered by OpenAI")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input():
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    client = OpenAI(api_key=openai_api_key)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=st.session_state.messages
    )
    msg = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": msg})
    st.chat_message("assistant").write(msg)
```
