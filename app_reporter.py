"""
PROJECT: Smart Pothole Reporter (Competition Edition)
AUTHOR: High School AI Developer
DESCRIPTION: 
    This Streamlit web application features an elegant entry landing page that 
    displays a project logo before revealing the core live telemetry tools.
"""

# ==========================================
# 1. IMPORTING REQUIRED LIBRARIES (TOOLBOX)
# ==========================================
import streamlit as st                  # Streamlit: Helps us build a beautiful web interface using only Python
import google.generativeai as genai     # Google Generative AI: Connects our app to the Gemini AI models
from PIL import Image                   # Pillow (PIL): Used for opening, manipulating, and saving images
import smtplib                          # SMTP Library: Python's built-in tool to send emails via the internet
from email.message import EmailMessage  # Email Message: Helps us format emails cleanly (Subject, To, From, Body)
from streamlit_geolocation import streamlit_geolocation  # A custom Streamlit tool that asks the browser for GPS data
import io                               # Input/Output: Allows us to handle image data in the computer's memory without saving files to disk

# ==========================================
# 2. CONFIGURATION & SECRETS MANAGEMENT
# ==========================================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GMAIL_USER = st.secrets["GMAIL_USER"]
    GMAIL_PASSWORD = st.secrets["GMAIL_APP_PASSWORD"]  # Your 16-character Google App Password
    RECIPIENT_EMAIL = st.secrets["RECIPIENT_EMAIL"]    # Who receives the pothole alerts
except KeyError:
    st.error("🚨 Configuration Error: Missing required keys in Streamlit Secrets!")
    st.info("Please ensure GEMINI_API_KEY, GMAIL_USER, GMAIL_APP_PASSWORD, and RECIPIENT_EMAIL are set up in your secrets.")
    st.stop()

# Activate and set up our Gemini AI model connection
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')  # We use 2.5-flash because it is incredibly fast and great with images

# ==========================================
# 3. EXIF METADATA INJECTION HELPERS
# ==========================================
def change_to_rational(number):
    """Convert decimal degrees to flat floating-point components."""
    deg = int(number)
    min_float = (number - deg) * 60
    minute = int(min_float)
    sec = round((min_float - minute) * 60, 4)
    return [float(deg), float(minute), float(sec)]

def add_geotag_to_image(image_buffer, lat, lon):
    """Manually injects GPS coordinates directly into an image's EXIF matrix block."""
    img = Image.open(image_buffer)
    
    gps_info = {}
    lat_ref = 'N' if lat >= 0 else 'S'
    lon_ref = 'E' if lon >= 0 else 'W'
    
    gps_info[1] = lat_ref
    gps_info[2] = change_to_rational(abs(lat))
    gps_info[3] = lon_ref
    gps_info[4] = change_to_rational(abs(lon))
    
    exif = img.getexif()
    exif[0x8825] = gps_info
    
    output_buffer = io.BytesIO()
    img.save(output_buffer, format="JPEG", exif=exif)
    output_buffer.seek(0)
    return output_buffer

# ==========================================
# 4. AUTOMATED EMAIL DISPATCHER
# ==========================================
def send_notification_email(lat, lon, analysis):
    """Connects to Google's secure mail servers using SMTP to send reports."""
    msg = EmailMessage()
    maps_link = f"https://www.google.com/maps?q={lat},{lon}"
    
    email_body = (
        f"🚨 AUTOMATED ALERT: Pothole Hazard Detected.\n\n"
        f"--- GEOGRAPHIC LOCATION ---\n"
        f"Latitude: {lat}\n"
        f"Longitude: {lon}\n"
        f"Google Maps Link: {maps_link}\n\n"
        f"--- GEMINI AI DAMAGE ANALYSIS ---\n"
        f"{analysis}\n\n"
        f"Sent automatically by the Smart Pothole Reporter Application."
    )
    
    msg.set_content(email_body)
    msg['Subject'] = "🚨 CRITICAL: Pothole Hazard Location Report"
    msg['From'] = GMAIL_USER
    msg['To'] = RECIPIENT_EMAIL

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_PASSWORD)
        smtp.send_message(msg)

# ==========================================
# 5. STREAMLIT FRONTEND USER INTERFACE (UI)
# ==========================================
st.set_page_config(page_title="Smart Pothole Reporter", page_icon="🛡️", layout="centered")

# --- INITIALIZE STATE MANAGEMENT ---
# Streamlit reruns the whole script on interactions. We use st.session_state 
# to keep memory of whether the user clicked the "Start Button" or not.
if "app_started" not in st.session_state:
    st.session_state.app_started = False

# --- STATE A: THE LANDING SPLASH SCREEN ---
if not st.session_state.app_started:
    # Centering containers for the competition logo presentation
    col_blank1, col_logo, col_blank2 = st.columns([1, 2, 1])
    
    with col_logo:
        try:
            # Open and display the requested project branding image assets
            logo_img = Image.open("logo_smart.jpeg")
            st.image(logo_img, use_container_width=True)
        except FileNotFoundError:
            st.warning("⚠️ 'logo_smart.jpeg' file missing from root directory. Please check GitHub deployment repository.")
    
    st.markdown("<h3 style='text-align: center;'>Smart Infrastructure Inspection System</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Edge AI Computer Vision Tracking Pipeline</p>", unsafe_allow_html=True)
    
    # Large action button to move past the splash screen entry step
    if st.button("🚀 Initialize Application Platform", use_container_width=True):
        st.session_state.app_started = True
        st.rerun() # Forces Streamlit to instantly refresh into State B

# --- STATE B: THE CORE REPORTING ENGINE APPLICATION ---
else:
    # Small aesthetic top banner so branding remains visible during runtime
    try:
        mini_logo = Image.open("logo_smart.jpeg")
        st.image(mini_logo, width=150)
    except FileNotFoundError:
        pass

    st.title("🛡️ Live-Geotagged Pothole Reporter")
    st.write("An automated AI application to capture, log, and report infrastructure damage.")
    
    # Button to allow judges to return to the landing page if needed
    if st.button("⬅️ Return to Splash Screen", help="Go back to the entry menu"):
        st.session_state.app_started = False
        st.rerun()

    st.markdown("---")
    st.subheader("Step 1: Acquire GPS Coordinates")
    st.write("Click the button below to fetch live device hardware location via your browser.")

    location_data = streamlit_geolocation()

    if location_data and location_data.get('latitude') is not None:
        lat = location_data['latitude']
        lon = location_data['longitude']
        st.success(f"📍 GPS coordinates successfully locked: `{lat}, {lon}`")
        
        st.markdown("---")
        st.subheader("Step 2: Snapshot the Asset Damage")
        
        camera_photo = st.camera_input("Position the camera over the road surface defect:")
        
        if camera_photo:
            with st.spinner("Embedding hardware coordinates directly into image stream..."):
                geotagged_image_file = add_geotag_to_image(camera_photo, lat, lon)
                st.toast("Metadata mapping complete: EXIF headers added.", icon="✅")
                
            st.markdown("---")
            if st.button("🚀 Analyze & Dispatch Report", use_container_width=True):
                with st.spinner("Processing asset frames through Gemini AI Core..."):
                    final_img = Image.open(geotagged_image_file)
                    
                    # Modern safety confirmation logic prompt setup
                    prompt = (
                        "You are a strict city infrastructure monitoring system. Analyze this image. "
                        "Is there an actual pothole, crater, or severe asphalt damage on a road surface? "
                        "If it is a picture of an indoor object, a bottle, a person, or anything else that is NOT a broken road, "
                        "you MUST start your response with 'NO'. "
                        "Only start with 'YES' if you clearly see broken asphalt or a pothole. "
                        "Provide your response with either 'YES' or 'NO' as your first word, followed by a 1-sentence explanation."
                    )
                    
                    response = model.generate_content([prompt, final_img])
                    verdict = response.text.strip()
                    
                    st.subheader("AI Analysis Results:")
                    st.info(f"{verdict}")
                    
                    if verdict.upper().startswith("YES"):
                        st.warning("⚠️ Pothole presence verified. Initializing secure email routing protocol...")
                        try:
                            send_notification_email(lat, lon, verdict)
                            st.balloons() # Gives a neat rewarding visual feedback effect for presentation scoring!
                            st.success("📩 Notification report successfully dispatched to public transit logs!")
                        except Exception as e:
                            st.error(f"Failed to communicate with SMTP relay servers: {e}")
                    else:
                        st.success("🌿 No actionable structural failures identified. No automated alerts triggered.")
    else:
        st.warning("👋 Action Required: Please interact with the location prompt above and grant your browser access to GPS to display camera capture tool.")