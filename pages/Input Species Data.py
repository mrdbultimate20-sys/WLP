import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# --------------------------------------------------
# Page setup and storage
# --------------------------------------------------

st.set_page_config(
    page_title="Bird Observation Form",
    page_icon="🐦",
    layout="wide",
)

# Assumes this file is inside your project's pages folder.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "wildlife_data"
IMAGE_DIR = DATA_DIR / "images"
AUDIO_DIR = DATA_DIR / "audio"
CSV_FILE = DATA_DIR / "submissions.csv"

for folder in (DATA_DIR, IMAGE_DIR, AUDIO_DIR):
    folder.mkdir(parents=True, exist_ok=True)

st.title("🐦 St. Louis Project Wildlife Database")
st.write(
    "Record a bird observation, upload media, and optionally "
    "identify bird species from audio using BirdNET."
)

# --------------------------------------------------
# BirdNET model: loaded once and reused
# --------------------------------------------------

@st.cache_resource(show_spinner=False)
def load_birdnet_model():
    import birdnet
    return birdnet.load("acoustic", "3.0", "onnx")


# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def save_uploads(uploaded_files, destination_folder, submission_id):
    saved_paths = []

    for uploaded_file in uploaded_files or []:
        suffix = Path(uploaded_file.name).suffix.lower()

        # Create a unique filename to avoid overwriting files.
        filename = f"{submission_id}_{uuid.uuid4().hex}{suffix}"
        destination = destination_folder / filename
        destination.write_bytes(uploaded_file.getvalue())

        saved_paths.append(str(destination.relative_to(PROJECT_DIR)))

    return saved_paths



def identify_bird_audio(model, audio_path):
    """Identify bird species from a BirdNET audio result."""

    import pandas as pd

    predictions = model.predict(str(audio_path))

    # Convert the result to a DataFrame if the object supports it.
    if isinstance(predictions, pd.DataFrame):
        df = predictions
    else:
        df = None

        for method_name in ("to_dataframe", "to_pandas"):
            method = getattr(predictions, method_name, None)
            if callable(method):
                converted = method()
                if isinstance(converted, pd.DataFrame):
                    df = converted
                    break

        # Check whether the result contains a DataFrame.
        if df is None:
            for value in vars(predictions).values():
                if isinstance(value, pd.DataFrame):
                    df = value
                    break

        if df is None:
            details = ", ".join(vars(predictions).keys())
            raise ValueError(
                "Could not find the prediction table in BirdNET's "
                f"result object. Available fields: {details or 'none'}. "
                "Please share this message so the result format "
                "can be matched correctly."
            )

    if df.empty:
        return []

    required_columns = {"species_name", "confidence"}
    if not required_columns.issubset(df.columns):
        raise ValueError(
            "BirdNET returned unexpected columns: "
            + ", ".join(map(str, df.columns))
        )

    results = (
        df.dropna(subset=["species_name", "confidence"])
        .groupby("species_name", as_index=False)["confidence"]
        .max()
        .sort_values("confidence", ascending=False)
    )

    # Keep predictions with a confidence score of at least 80%.
    results = results[results["confidence"] >= 0.80].head(5)

    output = []

    for _, row in results.iterrows():
        raw_name = str(row["species_name"])
        parts = raw_name.split("_", 1)

        output.append({
            "species": parts[1] if len(parts) == 2 else raw_name,
            "scientific_name": parts[0] if len(parts) == 2 else "",
            "score": round(float(row["confidence"]), 4),
        })

    return output



def append_record(record):
    new_record = pd.DataFrame([record])
    needs_header = (
        not CSV_FILE.exists() or CSV_FILE.stat().st_size == 0
    )

    new_record.to_csv(
        CSV_FILE,
        mode="a",
        header=needs_header,
        index=False,
        encoding="utf-8",
    )


# --------------------------------------------------
# Choose a submission mode
# --------------------------------------------------

mode = st.radio(
    "How would you like to submit your observation?",
    ["Audio identification", "Manual observation"],
    horizontal=True,
)

if mode == "Audio identification":
    st.info(
        "Upload a recording and BirdNET will suggest possible species. "
        "You do not need to know the bird's name."
    )
else:
    st.info(
        "Enter the bird's name if you know it. Audio and photos are optional."
    )

# --------------------------------------------------
# Observation form
# --------------------------------------------------

with st.form("bird_observation_form", clear_on_submit=False):

    st.subheader("1. Observation details")

    if mode == "Manual observation":
        bird_name = st.text_input(
            "Bird name (optional)",
            placeholder="e.g. Northern Cardinal, or leave blank",
        )
    else:
        bird_name = ""

    count_options = [
        "1", "2–5", "6–10", "11–25", "26–50",
        "51–100", "100+", "500+", "1,000+", "10,000+", "Unknown",
    ]
    approximate_count = st.selectbox(
        "Approximate number of birds *",
        count_options,
    )

    location = st.text_input(
        "General location *",
        placeholder="e.g. Forest Park, a trail, or a nearby lake",
    )

    col1, col2 = st.columns(2)

    with col1:
        observation_date = st.date_input(
            "Date observed *",
            value=date.today(),
            max_value=date.today(),
        )

    with col2:
        observation_time = st.time_input(
            "Time observed *",
            value=datetime.now().time().replace(second=0, microsecond=0),
        )

    behavior_options = [
        "Unknown",
        "Perching or resting",
        "Flying",
        "Soaring or gliding",
        "Walking or hopping",
        "Feeding on the ground",
        "Eating at a feeder",
        "Hunting or catching prey",
        "Drinking water",
        "Bathing",
        "Swimming or floating",
        "Calling or singing",
        "Chasing another bird",
        "Courtship or mating display",
        "Building a nest",
        "Carrying nesting material",
        "Incubating eggs",
        "Feeding chicks",
        "Flocking or gathering",
        "Migrating",
        "Defending territory",
        "Other",
    ]
    behavior = st.selectbox("What was the bird doing?", behavior_options)

    habitat_options = [
        "Unknown",
        "Forest or woodland",
        "Open field or grassland",
        "Wetland or marsh",
        "Lake, pond, or river",
        "Backyard or garden",
        "Urban area or building",
        "Park or landscaped area",
        "Agricultural land",
        "Roadside",
        "Other",
    ]
    habitat = st.selectbox("Habitat", habitat_options)

    confidence_options = [
        "Not yet identified",
        "Certain",
        "Fairly certain",
        "Unsure",
    ]
    identification_confidence = st.selectbox(
        "Identification confidence",
        confidence_options,
        help=(
            "For audio identification, this describes your confidence "
            "in the result after reviewing it, not BirdNET's score."
        ),
    )

    st.subheader("2. Upload media")

    # BirdNET's Python library supports WAV, MP3, FLAC and OGG.
    # M4A is not supported by the documented audio-reading workflow.
    if mode == "Audio identification":
        audio_files = st.file_uploader(
            "Upload bird audio recordings *",
            type=["wav", "mp3", "flac", "ogg", "aiff", "aif"],
            accept_multiple_files=True,
            help=(
                "BirdNET will analyze each uploaded recording. "
                "WAV, MP3, FLAC and OGG are recommended."
            ),
        )
    else:
        audio_files = st.file_uploader(
            "Upload audio recordings (optional)",
            type=["wav", "mp3", "flac", "ogg", "aiff", "aif"],
            accept_multiple_files=True,
        )

    image_files = st.file_uploader(
        "Upload photographs (optional)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )

    notes = st.text_area(
        "Additional notes (optional)",
        placeholder=(
            "Colors, markings, weather, flock behavior, "
            "or other useful details."
        ),
    )

    st.subheader("3. Submission security")

    pin = st.text_input(
        "Submission PIN *",
        type="password",
        help="Enter the PIN provided by the database administrator.",
    )

    submitted = st.form_submit_button(
        "Submit bird observation",
        type="primary",
        use_container_width=True,
    )


# --------------------------------------------------
# Validate and process submission
# --------------------------------------------------

if submitted:
    expected_pin = st.secrets.get(
        "submission_pin",
        os.environ.get("SUBMISSION_PIN", ""),
    )

    if not expected_pin:
        st.error(
            "No submission PIN is configured. Ask the administrator "
            "to configure submission_pin in Streamlit secrets."
        )

    elif pin != expected_pin:
        st.error("Incorrect PIN. Your observation was not submitted.")

    elif not location.strip():
        st.error("Please enter the general location.")

    elif mode == "Audio identification" and not audio_files:
        st.error("Please upload at least one audio recording.")

    else:
        submission_id = str(uuid.uuid4())

        try:
            saved_audio = save_uploads(
                audio_files, AUDIO_DIR, submission_id
            )
            saved_images = save_uploads(
                image_files, IMAGE_DIR, submission_id
            )

            birdnet_results = []
            analysis_errors = []

            if mode == "Audio identification":
                try:
                    with st.spinner(
                        "Loading BirdNET and analyzing audio..."
                    ):
                        model = load_birdnet_model()

                        for relative_path in saved_audio:
                            absolute_path = PROJECT_DIR / relative_path

                            try:
                                predictions = identify_bird_audio(
                                    model, absolute_path
                                )
                                birdnet_results.append({
                                    "audio_file": relative_path,
                                    "predictions": predictions,
                                })
                            except Exception as error:
                                analysis_errors.append(
                                    f"{Path(relative_path).name}: {error}"
                                )

                except Exception as error:
                    analysis_errors.append(
                        f"BirdNET could not load: {error}"
                    )

            # In audio mode, species names come from BirdNET.
            if mode == "Audio identification":
                unique_species = []
                seen = set()

                for result in birdnet_results:
                    for prediction in result["predictions"]:
                        name = prediction["species"]
                        if name not in seen:
                            unique_species.append(name)
                            seen.add(name)

                final_bird_name = "; ".join(unique_species)
                if not final_bird_name:
                    final_bird_name = "Unknown"
            else:
                final_bird_name = bird_name.strip() or "Unknown"

            record = {
                "submission_id": submission_id,
                "submission_mode": mode,
                "bird_name": final_bird_name,
                "approximate_count": approximate_count,
                "location": location.strip(),
                "observation_date": observation_date.isoformat(),
                "observation_time": observation_time.strftime("%H:%M"),
                "behavior": behavior,
                "habitat": habitat,
                "identification_confidence": identification_confidence,
                "image_files": ";".join(saved_images),
                "audio_files": ";".join(saved_audio),
                "birdnet_results": json.dumps(birdnet_results),
                "analysis_errors": "; ".join(analysis_errors),
                "notes": notes.strip(),
            }

            append_record(record)

            st.success("Observation saved!")

            st.write("### Submission summary")
            st.write(f"**Submission ID:** `{submission_id}`")
            st.write(f"**Mode:** {mode}")
            st.write(f"**Bird name(s):** {final_bird_name}")
            st.write(f"**Location:** {location}")
            st.write(f"**Date:** {observation_date}")
            st.write(f"**Photos saved:** {len(saved_images)}")
            st.write(f"**Audio files saved:** {len(saved_audio)}")

            if birdnet_results:
                st.subheader("BirdNET identification results")

                for result in birdnet_results:
                    st.write(f"**Audio file:** {Path(result['audio_file']).name}")

                    if result["predictions"]:
                        display_rows = []
                        for prediction in result["predictions"]:
                            display_rows.append({
                                "Possible species": prediction["species"],
                                "Scientific name": prediction["scientific_name"],
                                "Model score": prediction["score"],
                            })

                        st.dataframe(
                            pd.DataFrame(display_rows),
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.write("No species predictions were returned.")

                st.caption(
                    "BirdNET scores are model outputs, not guaranteed "
                    "probabilities that an identification is correct."
                )

            if analysis_errors:
                st.warning(
                    "The observation and uploaded files were saved, "
                    "but some audio analysis did not complete."
                )
                for error in analysis_errors:
                    st.write(f"- {error}")

            st.info(
                f"Local data folder: {DATA_DIR}\n\n"
                "Keep a backup of this folder. Local files may not persist "
                "if the app is deployed to some hosting platforms."
            )

        except Exception as error:
            st.error(
                "The submission could not be saved. "
                f"Details: {error}"
            )
