from openai import OpenAI
import json
import streamlit as st
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
def run_segment_stitcher(system_prompt: str, grounding_payload: dict):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "You are given structured segment data for multiple filings.\n"
                        "Here is the JSON context:\n"
                        f"{json.dumps(grounding_payload, indent=2)}\n\n"
                        "Return valid JSON following the schema in the system prompt."
                    )
                }
            ],
            temperature=0.2
        )

        raw_output = response.choices[0].message["content"]

        # Try to parse JSON
        stitched = json.loads(raw_output)
        return stitched, raw_output, None

    except json.JSONDecodeError:
        return None, raw_output, "Model returned invalid JSON."

    except Exception as e:
        return None, None, str(e)
if st.button("Run Segment Stitcher"):
    with st.spinner("Analyzing segments with LLM..."):
        stitched, raw_output, error = run_segment_stitcher(system_prompt, grounding_payload)

    if error:
        st.error(f"Error: {error}")
        if raw_output:
            st.text_area("Raw model output", raw_output, height=300)
    else:
        st.success("LLM analysis complete!")

        st.subheader("Canonical Segments")
        st.json(stitched["canonical_segments"])

        st.subheader("Mappings")
        st.json(stitched["mappings"])

        st.subheader("Global Explanation")
        st.write(stitched["global_explanation"])

        st.expander("Raw Model Output").write(raw_output)

"""
Root-level Streamlit app entry point that imports and runs the actual app from src.
"""
import sys
import os

# Ensure src is in the path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the app
from src.app import *  # noqa: F401, F403
