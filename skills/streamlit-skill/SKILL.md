---
name: streamlit-skill
description: Used generate simple user interfaces that are defined in the python programming language.
---

# When to use this skill
Use this skill when user interfaces are needed, such as an interface to communicate with a chatbot.

## Key concepts

- 1. Streamlit apps are Python scripts that run from top to bottom.
- 2. Every time a browser tab opens for your app, the script is executed and a new session starts.
- 3. As the script executes, Streamlit draws its output live in a browser.
- 4. Every time a user interacts with a widget, your script is re-executed and Streamlit redraws its output in the browser.
- 5. The output value of that widget matches the new value during that rerun.
- 6. Scripts use the Streamlit cache to avoid recomputing expensive functions, so updates are fast.
- 7. Session State lets you save information that persists between reruns.
- 8. Streamlit apps can have multiple pages defined in separate .py files in a pages folder.


## Updatable items
### Some elements have built-in methods to allow you to update them in-place without rerunning the app.
- st.empty containers can be written to in sequence and will always show the last thing written. They can also be cleared with an additional .empty() called like a method.
- st.dataframe and st.table can be updated with the add_rows() method to append data
- st.progress elements can be updated with additional .progress() calls. They can also be cleared with a .empty() method call.
    st.status containers have an .update() method to change their labels, expanded state, and status.
    st.toast messages can be updated in place with additional .toast() calls.


## Additional Resources
- For usage examples, see [examples.md](examples.md)
- Documentation home page [Documentation](https://docs.streamlit.io/)
- Brief reference of all functions[Streamlit-quick-reference](https://docs.streamlit.io/develop/quick-reference/cheat-sheet)
- Animate or update elements [Animate-update](https://docs.streamlit.io/develop/concepts/design/animate)
