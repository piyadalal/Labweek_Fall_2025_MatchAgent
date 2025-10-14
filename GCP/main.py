import streamlit as st
import os
from dotenv import load_dotenv
from google import genai
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel

OUTPUT_FILENAME = ""
OUTPUT_FOLDER = "outputs"
OUTPUT_SUBFOLDER = ""

def get_vertex_ai_content(prompt, key):
    PROJECT_ID = "gen-lang-client-0739157236"
    LOCATION = "us-central1"

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-002")

    try:
        print(f" '{prompt}'")
        images = model.generate_images(
            prompt=prompt,
            number_of_images=3,  # You can request more images (up to 4 typically)
            language="en",
            # Optional: Control image properties
            aspect_ratio="4:3",  # Common aspect ratios: "1:1", "16:9", "4:3", etc.
            # safety_filter_level="block_some", # Adjust safety filter level if needed
            person_generation="dont_allow", # Control generation of people
            seed=100,                 # Use a seed for reproducible results (cannot be used with watermark)
            add_watermark=False       # Watermark is added by default and often cannot be disabled
        )

        # --- Save the Generated Image ---
        if images:
            for idx, image in enumerate(images, start=1):
                # st.image(image, caption=f"Illustration for '{key}'")
                output_filename = key + f"_{idx}.png"
                output_dir = os.path.join(OUTPUT_FOLDER, key)
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                output_path = os.path.join(output_dir, output_filename)
                image.save(location=output_path, include_generation_parameters=False)
                # Speichere das Prompt-Text in einer .txt-Datei im gleichen Ordner
                prompt_path = os.path.join(output_dir, key + "_prompt.txt")
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(prompt)
                image.save(location=output_path, include_generation_parameters=False)

                print(f"Image successfully generated and saved as '{output_path}'")

            # You can also view the image if running in an environment that supports it (e.g., Jupyter notebook)
            # generated_image.show()
        else:
            print("No images were generated.")

    except Exception as e:
        print(f"An error occurred during image generation: {e}")



def get_gemini_client(text):
    # Load environment variables from .env file
    load_dotenv()
    """Initializes and returns a Gemini API client."""
    api_key = os.getenv("GEMINI_API_KEY")
    print(api_key)



    # Check if the API key was loaded (for debugging)
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
    else:
        print("API Key loaded successfully.")

    # Initialize the client with the actual API key variable
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash", contents=text
        # model="google-cloud-aiplatform", contents=text
    )
    print(response.text)
    return response.text

# Assuming sports_terms.py is in the same directory and contains the data
# NOTE: This line requires a file named sports_terms.py to be present.
try:
    from sports_terms import football_terms, basketball_terms, f1_terms
except ImportError:
    st.error(
        "Error: Could not import 'sports_terms.py'. Please ensure it is in the same directory and contains 'football_terms', 'basketball_terms', and 'f1_terms' dictionaries.")
    # Provide dummy data so the app doesn't crash entirely
    football_terms = {"Offside": "Rule not loaded."}
    basketball_terms = {}
    f1_terms = {}

# --- Setup ---
st.set_page_config(layout="wide")
st.title("MatchRules Agent Demo")


# --- Utility Function ---
def search_all_terms(term_list):
    """Searches for terms in all sports dictionaries."""
    found_pairs = []

    for term in term_list:
        term = term.strip().lower()
        if not term:
            continue

        # Combine all term dictionaries
        all_terms = {**football_terms, **basketball_terms, **f1_terms}

        # Check for exact matches and partial matches
        for key, explanation in all_terms.items():
            key_lower = key.lower()
            if term == key_lower or term in key_lower:
                found_pairs.append((key, explanation))

    # Return unique matches (key, explanation)
    unique_matches = {}
    for key, expl in found_pairs:
        unique_matches[key] = expl

    return list(unique_matches.items())


# --- LAYOUT: 3 Columns ---
col_left, col_center, col_right = st.columns([4, 1, 4], gap="large")

with col_left:
    st.header("Content Input")
    st.markdown("**Enter a keyword/phrase or upload a .txt file.**")

    # Text input
    if "user_text_input" not in st.session_state:
        st.session_state["user_text_input"] = ""
    user_text = st.text_area(
        "Type keyword(s) or rule phrase (e.g. Offside, Penalty):",
        value=st.session_state["user_text_input"],
        height=200,
        key="user_text_input_area",
        label_visibility="collapsed"
    )
    st.session_state["user_text_input"] = user_text

    # File uploader
    uploaded_file = st.file_uploader(
        "Or upload a .txt file with terms (one per line):",
        type=["txt"],
        key="file_uploader"
    )

# --- Central Button Logic ---
# Determine which content source to use
input_terms = []
if uploaded_file:
    try:
        # Read uploaded file content
        contents = uploaded_file.read().decode("utf-8")
        input_terms = [line.strip() for line in contents.splitlines() if line.strip()]
    except Exception as e:
        st.error(f"Error reading file: {e}")
        input_terms = []
elif user_text.strip():
    # Split text area input by commas or newlines for multiple terms
    terms = user_text.replace('\n', ',').split(',')
    input_terms = [term.strip() for term in terms if term.strip()]

content_exists = bool(input_terms)

# Initialize session state for matches and search status
if 'matches' not in st.session_state:
    st.session_state['matches'] = []
if 'search_triggered' not in st.session_state:
    st.session_state['search_triggered'] = False

with col_center:
    # Use native Streamlit spacing/alignment
    st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
    if content_exists:
        # Button to trigger the search
        if st.button("Search Rules", key="run_search_button", type="primary", use_container_width=True):
            st.session_state['matches'] = search_all_terms(input_terms)
            st.session_state['search_triggered'] = True
    else:
        st.markdown(
            "<div style='text-align: center; color: #6b7280; margin-top: 150px; font-size: 14px;'>Input content to enable search.</div>",
            unsafe_allow_html=True)

# --- Results Screen ---
with col_right:
    st.header("Rule Explanation & Context")

    if st.session_state['search_triggered']:
        matches = st.session_state.get('matches', [])

        if matches:
            # Display a mock image related to the first term found
            first_term = matches[0][0]

            st.subheader(f"Visual Context for: **{first_term}**")

            # --- Dynamic Placeholder Image Logic ---
            # Determine the sport of the first matched term for a thematic placeholder
            if first_term in football_terms:
                image_tag = "Football Rule Diagram"
            elif first_term in basketball_terms:
                image_tag = "Basketball Foul Area"
            elif first_term in f1_terms:
                image_tag = "F1 Track Scenario"
            else:
                image_tag = "Generic Match Scenario"

            # Using st.image with a URL or tag (we'll use a URL placeholder here)
            st.image(f"https://placehold.co/600x300/4c7c8c/ffffff?text={image_tag.replace(' ', '+')}",
                     caption=f"Visual Example of '{first_term}'")

            st.markdown("---")
            st.subheader("Search Results")

            for key, explanation in matches:
                st.markdown(f"**{key}:** {explanation}")
                standard_text = (f"Explain the term '{key}' like '{explanation}' in simple terms suitable for someone"
                                 f"unfamiliar with sports rules. Generate a few sentences. Use that info as input to "
                                 f"create for max 3 images that Vertex AI illustrate the concept. Describe each image "
                                 f"in a sentence or two, ensuring they clearly show relevant players, the ball, and any "
                                 f"key boundary lines or zones involved in the rule. Images can be diagrams, illustrations, "
                                 f"or simple scenes that help visualize the rule.")
                gemini_text = get_gemini_client(standard_text)
                print(gemini_text)
                # generated_text, image_urls = get_vertex_ai_content(gemini_text, key)
                st.markdown("#### AI Explanation")
                st.markdown(gemini_text)

                # for img_url in image_urls:
                    # st.image(img_url, caption=f"Illustration for '{key}'")

                st.markdown("---")
        else:
            st.warning("No known explanation for the term(s) you entered or uploaded.")
    else:
        st.info("Click **Search Rules** to display results.")


if __name__ == "__main__":
    #key = "Offside"
    # explanation = "Occurs when an attacking player is nearer to the opponent's goal line than both the ball and second-last defender at the moment the ball is passed to them."
    # The new, safer instruction in the prompt:
    for key, explanation in football_terms.items():
        standard_text = (f"Explain the term '{key}' like '{explanation}' in simple terms suitable for someone"
                     f"unfamiliar with sports rules. Generate a few sentences. Use that info as input to "
                     f"create for max 3 images that Vertex AI illustrate the concept. Describe each image "
                     f"in a sentence or two, ensuring they clearly show relevant players, the ball, and any "
                     f"key boundary lines or zones involved in the rule. Images can be diagrams, illustrations, "
                     f"or simple scenes that help visualize the rule."
                     )
        standard_text += (
        " Ensure the descriptions are clear and concise."
        " Do not create images with people."
        " Do not create images with text."
        " Avoid complex scenes; keep it simple and clear."
        " Focus on the main elements needed to understand the rule."
        " Use arrows, lines, and shapes to highlight important aspects."
        " Avoid any depiction of violence or aggression."
        " Keep the illustrations educational and neutral."
        )
        gemini_text = get_gemini_client(standard_text)
        print(gemini_text)
        get_vertex_ai_content(gemini_text, key)
    gemini_text = (
        "Minimalistic schematic, top-down view of a solid green football field with a white goal frame on the right, "
        "no crowd or stadium. Use simple geometric shapes: dark square (defender) in front of the goal, red triangle "
        "(attacker) to the left and further from goal, yellow circle (ball) even further left. A faint, dashed line "
        "extends from the defender towards the goal, indicating the offside line. The attacking player is clearly behind"
        " this line. High contrast, labeled elements, vector style, no extraneous detail.")
    # get_vertex_ai_content(gemini_text, key)
