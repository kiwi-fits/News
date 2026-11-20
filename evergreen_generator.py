import os
import json
import time
import random
import re
from urllib.parse import quote
import requests
from config import GEMINI_API_KEY, OUTPUT_DIR
from media_extractor import create_ambient_vertical_canvas
from tamil_transliteration import transliterate_english_to_tamil

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

_session = requests.Session()
_session.headers.update(HEADERS)

EVERGREEN_STATE_FILE = os.path.join(os.path.dirname(__file__), "evergreen_state.json")

CATEGORIES = [
    {
        "id": "history",
        "name": "🏛️ வரலாற்று மர்மம்",
        "theme_desc": "Ancient Tamil civilization (Cholas, Pandyas, Cheras), Thanjavur temple architectural marvels, lost cities, Indus Valley, or world historical mysteries.",
        "badge_tag": "🏛️ வரலாற்றுச் சுவாரசியம்",
        "hashtags": "#TamilHistory #வரலாறு #CholaDynasty #AncientTamil #Mystery #Reels"
    },
    {
        "id": "gk",
        "name": "💡 வியக்கவைக்கும் தகவல்",
        "theme_desc": "Did You Know? Bizarre general knowledge facts, fascinating human body secrets, psychology, or unbelievable world records.",
        "badge_tag": "💡 உங்களுக்குத் தெரியுமா?",
        "hashtags": "#DidYouKnow #TamilGK #பொதுஅறிவு #AmazingFacts #Knowledge #Reels"
    },
    {
        "id": "science",
        "name": "🔬 அறிவியல் உலகம்",
        "theme_desc": "Deep space mysteries (Black Holes, James Webb discoveries, Neutron stars), deep ocean trenches, bizarre wildlife adaptations, or quantum physics in simple terms.",
        "badge_tag": "🔬 அறிவியல் ஆச்சரியம்",
        "hashtags": "#ScienceFacts #Space #Universe #அறிவியல் #Nature #Reels"
    },
    {
        "id": "story",
        "name": "✨ ஞானச் சிறுகதை",
        "theme_desc": "One-minute wisdom story, inspirational Zen tale, Tenali Raman wit, or deep life-lesson story that leaves viewers motivated.",
        "badge_tag": "✨ ஒரு நிமிட ஞானக் கதை",
        "hashtags": "#TamilStories #Motivation #ZenStory #வாழ்க்கைத்_தத்துவம் #Wisdom #Reels"
    }
]

# Rich, pre-curated fallback library (20 topics) in case of offline/network issues
CURATED_FALLBACK_BANK = [
    {
        "category": "history",
        "topic_id": "thanjavur_brihadisvara_temple_shadow",
        "headline": "தஞ்சைப் பெரிய கோவில்: ஆயிரம் ஆண்டுகள் கடந்தும் வியக்கவைக்கும் கட்டிடக்கலை ரகசியம்!",
        "voiceover_script": "ஆயிரம் ஆண்டுகளுக்கு முன்பு எந்தவித நவீன தொழில்நுட்பமும் இல்லாத காலத்தில், எண்பது டன் எடைகொண்ட ஒற்றைக்கல் விமானத்தை தஞ்சை பெரிய கோவிலின் உச்சியில் ராஜராஜ சோழன் எவ்வாறு ஏற்றினார் என்பது இன்றும் விடைதெரியாத மர்மமாக உள்ளது. நிலநடுக்கங்கள் மற்றும் புயல்களைத் தாங்கி இன்றும் கம்பீரமாக நிற்கும் இக்கோவில் தமிழர்களின் கட்டிடக்கலை உச்சத்திற்கு உலகளாவிய சான்றாகும்.",
        "visual_prompt": "Cinematic 9:16 vertical photograph of ancient Thanjavur Brihadisvara big temple gopuram, dramatic golden hour sunlight, majestic clouds, 8k photorealistic documentary style",
        "visual_prompts": [
            "Cinematic 9:16 vertical photograph of ancient Thanjavur Brihadisvara big temple gopuram, dramatic golden hour sunlight, majestic clouds, 8k photorealistic documentary style",
            "Cinematic 9:16 vertical close up of monolithic granite vimana capstone on ancient Chola temple, intricate carved reliefs, historical realism, 8k"
        ],
        "engagement_question": "சோழர்களின் இந்த அசாத்திய கட்டிடக்கலை சாதனை பற்றி நீங்கள் என்ன நினைக்கிறீர்கள்?"
    },
    {
        "category": "gk",
        "topic_id": "octopus_three_hearts_blue_blood",
        "headline": "ஆக்டோபஸ் பற்றிய இந்த வியக்கவைக்கும் உண்மை உங்களுக்குத் தெரியுமா?",
        "voiceover_script": "கடலின் விசித்திர உயிரினமான ஆக்டோபஸுக்கு மூன்று இதயங்கள் மற்றும் ஒன்பது மூளைகள் உள்ளன என்பது உங்களுக்குத் தெரியுமா? அதன் ரத்தம் மனிதர்களைப் போல சிவப்பு நிறத்தில் இல்லாமல் நீல நிறத்தில் இருக்கும். ஆபத்து ஏற்படும் போது தன் உடலின் நிறத்தையும் தோலின் அமைப்பையும் சில நொடிகளில் மாற்றிக்கொள்ளும் பேராற்றல் இதற்கு உண்டு.",
        "visual_prompt": "Cinematic 9:16 vertical underwater photograph of a glowing intelligent octopus with intricate tentacles, deep blue ocean, coral reef background, National Geographic quality, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical underwater photograph of a glowing intelligent octopus with intricate tentacles, deep blue ocean, coral reef background, National Geographic quality, 8k",
            "Cinematic 9:16 vertical macro shot of octopus skin instantly shifting camouflage patterns and textured ripples against seabed coral, 8k"
        ],
        "engagement_question": "இயற்கையின் இந்த விசித்திர படைப்பு உங்களுக்கு ஆச்சரியத்தை ஏற்படுத்துகிறதா?"
    },
    {
        "category": "science",
        "topic_id": "black_hole_event_horizon_time_dilation",
        "headline": "கருந்துளைக்கு அருகில் சென்றால் காலம் நின்றுவிடுமா? விண்வெளி ஆச்சரியம்!",
        "voiceover_script": "விண்வெளியின் மிகப்பெரிய மர்மமான கருந்துளையின் ஈர்ப்பு விசை ஒளியைக் கூட தப்பவிடாத அளவுக்கு அதீத சக்தி வாய்ந்தது. ஐன்ஸ்டீனின் சார்பியல் தத்துவப்படி, கருந்துளையின் எல்லைப் பகுதிக்கு நீங்கள் சென்றால், அங்கு காலம் மிக மிக மெதுவாக நகரும். நீங்கள் அங்கு சில நிமிடங்கள் இருந்துவிட்டு பூமிக்குத் திரும்பினால், பூமியில் பல நூறு ஆண்டுகள் கடந்திருக்கும்.",
        "visual_prompt": "Cinematic 9:16 vertical rendering of a supermassive black hole with glowing fiery accretion disk and bent light rays, deep cosmos starfield, interstellar movie aesthetic, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical rendering of a supermassive black hole with glowing fiery accretion disk and bent light rays, deep cosmos starfield, interstellar movie aesthetic, 8k",
            "Cinematic 9:16 vertical viewpoint near event horizon looking into infinite warped starlight distortion, deep space cosmic mystery, 8k"
        ],
        "engagement_question": "விண்வெளியின் இந்த விசித்திரமான காலப் பயணம் பற்றி உங்கள் கருத்து என்ன?"
    },
    {
        "category": "story",
        "topic_id": "zen_story_heavy_stone_burden",
        "headline": "வாழ்க்கையில் கவலைகளை சுமப்பவர்களுக்கான ஒரு நிமிட ஞானக் கதை!",
        "voiceover_script": "ஒரு ஞானி தன் சீடர்களிடம் ஒரு தம்ளர் தண்ணீரைக் காட்டி, இதன் எடை என்ன என்று கேட்டார். சீடர்கள் வெவ்வேறு எடையைக் கூறினர். ஞானி புன்னகைத்து, இதன் எடையை விட, இதை எவ்வளவு நேரம் தூக்கிப் பிடித்திருக்கிறீர்கள் என்பதே முக்கியம் என்றார். ஒரு நிமிடம் பிடித்தால் வலிக்காது, நாள் முழுவதும் பிடித்தால் கை மரத்துப் போகும். வாழ்க்கையின் கவலைகளும் அப்படித்தான், உடனடியாக இறக்கி வைக்கக் கற்றுக்கொள்ளுங்கள்.",
        "visual_prompt": "Aesthetic 9:16 vertical cinematic photograph of a serene Zen monk standing beside a tranquil mountain waterfall, warm morning sunlight, peaceful atmosphere, 8k fine art",
        "visual_prompts": [
            "Aesthetic 9:16 vertical cinematic photograph of a serene Zen monk standing beside a tranquil mountain waterfall, warm morning sunlight, peaceful atmosphere, 8k fine art",
            "Cinematic 9:16 vertical close up of serene monk holding a simple glass of pure water, tranquil bamboo garden background, warm golden light, 8k"
        ],
        "engagement_question": "இந்தக் கதையின் கருத்து உங்கள் வாழ்க்கைக்கு பொருந்துகிறதா?"
    },
    {
        "category": "history",
        "topic_id": "chola_navy_southeast_asia_expedition",
        "headline": "ஆயிரம் ஆண்டுகளுக்கு முன்பே கடல்கடந்து வென்ற ராஜேந்திர சோழனின் கடற்படை!",
        "voiceover_script": "பண்டைய உலக வரலாற்றில் மிக பலம் வாய்ந்த கடற்படையைக் கொண்டு வங்காள விரிகுடாவை சோழர்களின் ஏரியாக மாற்றியவர் ராஜேந்திர சோழர். நவீன கப்பல்கள் இல்லாத காலத்திலேயே ஆயிரக்கணக்கான போர் வீரர்களுடன் இந்தோனேசியா, மலேசியா மற்றும் இலங்கை நாடுகளுக்கு கடல் வழியாகச் சென்று வெற்றி பெற்ற சோழர் கடற்படையின் வீரம் தமிழர்களின் அழிக்க முடியாத வரலாற்றுப் பெருமையாகும்.",
        "visual_prompt": "Cinematic 9:16 vertical artwork of ancient Tamil Chola war galleys sailing across rough ocean waters at sunset, fluttering tiger flags, epic historical realism, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical artwork of ancient Tamil Chola war galleys sailing across rough ocean waters at sunset, fluttering tiger flags, epic historical realism, 8k",
            "Cinematic 9:16 vertical detailed battle deck view of ancient Tamil warriors with spears on grand sailing war galleon, ocean horizon, 8k"
        ],
        "engagement_question": "சோழர்களின் கடல்சார் ஆதிக்கம் பற்றி பள்ளிகளில் அதிகம் கற்பிக்கப்பட வேண்டுமா?"
    },
    {
        "category": "gk",
        "topic_id": "human_brain_storage_capacity",
        "headline": "மனித மூளையின் அசாத்திய சக்தி: எத்தனை மெகாபைட் நினைவாற்றல் தெரியுமா?",
        "voiceover_script": "நவீன உலகின் அதிநவீன சூப்பர் கம்ப்யூட்டர்களை விட மனித மூளை பல மடங்கு சக்தி வாய்ந்தது என்று நரம்பியல் ஆய்வாளர்கள் கூறுகின்றனர். மனித மூளையின் சேமிக்கும் திறன் சுமார் இரண்டரை பெட்டாபைட்டுகள், அதாவது இருபத்தி ஐந்து லட்சம் கிகாபைட்டுகளுக்கு சமம். இது சுமார் முந்நூறு ஆண்டுகள் தொடர்ந்து ஒளிபரப்பாகும் உயர்தர வீடியோக்களைச் சேமிப்பதற்குச் சமமாகும்.",
        "visual_prompt": "Cinematic 9:16 vertical visualization of a glowing human brain with firing golden neural synapses and digital cosmic energy circuits, hyperdetailed, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical visualization of a glowing human brain with firing golden neural synapses and digital cosmic energy circuits, hyperdetailed, 8k",
            "Cinematic 9:16 vertical macro view of intricate glowing blue and gold neurons connecting through neural network pathways, hyperrealistic 8k"
        ],
        "engagement_question": "நமது மூளையின் இந்த வியக்கவைக்கும் சக்தியை நாம் முழுமையாகப் பயன்படுத்துகிறோமா?"
    },
    {
        "category": "science",
        "topic_id": "deep_ocean_mariana_trench_mystery",
        "headline": "மரியானா அகழி: உலகின் மிக ஆழமான இடத்தில் வாழும் விசித்திர உயிரினங்கள்!",
        "voiceover_script": "பூமியின் மிக ஆழமான பகுதியான பசிபிக் பெருங்கடலின் மரியானா அகழி பதினொரு கிலோமீட்டர் ஆழமுடையது. எவரெஸ்ட் சிகரத்தையே உள்ளே மூழ்கடித்தாலும் மேலும் இரண்டு கிலோமீட்டர் நீர் மேலே நிற்கும். சூரிய வெளிச்சமே இல்லாத மற்றும் அதீத நீர் அழுத்தம் உள்ள இந்த இருண்ட உலகிலும் ஒளிரும் விசித்திர உயிரினங்கள் வாழ்வது விஞ்ஞானிகளை வியப்பில் ஆழ்த்தியுள்ளது.",
        "visual_prompt": "Cinematic 9:16 vertical deep sea exploration documentary photo, research submersible spotlight revealing glowing ethereal translucent deep-sea creatures in dark abyss, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical deep sea exploration documentary photo, research submersible spotlight revealing glowing ethereal translucent deep-sea creatures in dark abyss, 8k",
            "Cinematic 9:16 vertical macro shot of alien-like bioluminescent jellyfish and deep sea anglerfish glowing in midnight ocean trench, 8k"
        ],
        "engagement_question": "விண்வெளியை விட பூமியின் கடல்களைப் பற்றி நாம் குறைவாகவே அறிந்துள்ளோமா?"
    },
    {
        "category": "story",
        "topic_id": "two_wolves_fighting_inside_heart",
        "headline": "நமக்குள்ளே போராடும் இரண்டு ஓநாய்கள்: பழங்குடி மக்களின் அரிய ஞானக் கதை!",
        "voiceover_script": "ஒரு வயதான தாத்தா தன் பேரனிடம், மனிதனின் மனதிற்குள் எப்போதும் இரண்டு ஓநாய்கள் சண்டையிட்டுக்கொண்டே இருக்கும் என்றார். ஒன்று கோபம், பொறாமை, பேராசை மற்றும் சுயநலம் கொண்டது. மற்றொன்று அன்பு, கருணை, அமைதி மற்றும் நம்பிக்கை கொண்டது. பேரன் கேட்டான், இதில் எந்த ஓநாய் வெற்றி பெறும் தாத்தா? தாத்தா புன்னகையுடன் சொன்னார், நீ எதற்கு தினமும் உணவு ஊட்டுகிறாயோ அதுவே வெற்றி பெறும்.",
        "visual_prompt": "Mystical 9:16 vertical digital painting of two ethereal wolves facing each other under a starry moonlit forest night sky, one glowing with warm golden light, one with dark smoke, 8k",
        "visual_prompts": [
            "Mystical 9:16 vertical digital painting of two ethereal wolves facing each other under a starry moonlit forest night sky, one glowing with warm golden light, one with dark smoke, 8k",
            "Cinematic 9:16 vertical close up of a wise indigenous elder smiling by a warm campfire under a starry sky, storytelling atmosphere, 8k"
        ],
        "engagement_question": "உங்கள் மனதுக்குள் இன்று நீங்கள் எந்த குணத்திற்கு உணவு ஊட்டுகிறீர்கள்?"
    },
    {
        "category": "history",
        "topic_id": "keezhadi_ancient_urban_civilization",
        "headline": "கீழடி அகழ்வாராய்ச்சி: 2600 ஆண்டுகளுக்கு முந்தைய தமிழர் நகர நாகரிகம்!",
        "voiceover_script": "வைகை நதிக்கரையில் அமைந்துள்ள கீழடியில் கண்டெடுக்கப்பட்ட பொருட்கள், இரண்டாயிரத்து அறுநூறு ஆண்டுகளுக்கு முன்பே தமிழர்கள் எழுத்தறிவு பெற்ற நாகரிக மக்களாக வாழ்ந்ததை உலகிற்கு நிரூபித்துள்ளன. செங்கற்களால் கட்டப்பட்ட வீடுகள், வடிகால் வசதிகள் மற்றும் தமிழ் பிராமி எழுத்துக்கள் பொறிக்கப்பட்ட மண்பாண்டங்கள் தமிழர்களின் தொன்மைக்கு அழிக்க முடியாத சான்றுகளாகும்.",
        "visual_prompt": "Cinematic 9:16 vertical photograph of ancient Keezhadi archaeological excavation trenches revealing well planned brick walls and pottery, golden sunlight, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical photograph of ancient Keezhadi archaeological excavation trenches revealing well planned brick walls and pottery, golden sunlight, 8k",
            "Cinematic 9:16 vertical close up of ancient Sangam era terracotta pottery shard with inscribed Tamil Brahmi script, museum lighting, 8k"
        ],
        "engagement_question": "கீழடி நாகரிகம் உலகளாவிய அங்கீகாரம் பெற என்ன செய்ய வேண்டும்?"
    },
    {
        "category": "history",
        "topic_id": "sigiriya_rock_fortress_sky_palace",
        "headline": "சிகிரியா: செங்குத்தான பாறை உச்சியில் அமைக்கப்பட்ட பிரம்மாண்ட அரண்மனை!",
        "voiceover_script": "இலங்கையின் எட்டாவது உலக அதிசயமாகக் கருதப்படும் சிகிரியா பாறைக்கோட்டை, ஐந்தாம் நூற்றாண்டில் காசியப்ப மன்னனால் கட்டப்பட்ட கட்டிடக்கலை விந்தை. சுமார் அறுநூறு அடி உயர செங்குத்தான பாறையின் உச்சியில் நீச்சல் குளங்கள் மற்றும் அரண்மனைகள் அமைக்கப்பட்டதும், அதன் பாறை ஓவியங்கள் மற்றும் கண்ணாடி சுவர் இன்றும் வியப்பை ஏற்படுத்துவதும் தமிழர்களின் வரலாற்றுப் பெருமைகளில் ஒன்றாகும்.",
        "visual_prompt": "Majestic 9:16 vertical drone view of Sigiriya lion rock fortress rising out of lush emerald green jungle, misty dramatic sunrise lighting, 8k documentary",
        "visual_prompts": [
            "Majestic 9:16 vertical drone view of Sigiriya lion rock fortress rising out of lush emerald green jungle, misty dramatic sunrise lighting, 8k documentary",
            "Cinematic 9:16 vertical detail of ancient colorful frescoes painted on sheer granite overhang at Sigiriya rock fortress, warm natural light, 8k"
        ],
        "engagement_question": "சிகிரியாவின் இந்த அசாத்திய கட்டிடக்கலை சாதனை உங்களுக்கு ஆச்சரியமளிக்கிறதா?"
    },
    {
        "category": "history",
        "topic_id": "kallanai_dam_karikala_chola_engineering",
        "headline": "கல்லணை: இரண்டாயிரம் ஆண்டுகளாக காவிரியை அடக்கிய கரிகால் சோழனின் சாதனை!",
        "voiceover_script": "உலகிலேயே பயன்பாட்டில் உள்ள மிகப்பழமையான அணைகளில் ஒன்றான கல்லணை, இரண்டாயிரம் ஆண்டுகளுக்கு முன்பு கரிகால் சோழனால் கட்டப்பட்டது. மணல் அடித்தளத்தில் நீரோட்டத்தின் வேகத்தை எதிர்கொள்ளும் வகையில் பாறைகளை அடுக்கி களிமண்ணால் இணைத்த சோழர்களின் நீர்ப்பாசன பொறியியல் திறன் இன்றும் உலக பொறியாளர்களுக்கு வியப்பை அளிக்கிறது.",
        "visual_prompt": "Cinematic 9:16 vertical aerial view of historic Kallanai Grand Anicut dam spanning rushing Kaveri river waters, golden hour sunlight, 8k documentary",
        "visual_prompts": [
            "Cinematic 9:16 vertical aerial view of historic Kallanai Grand Anicut dam spanning rushing Kaveri river waters, golden hour sunlight, 8k documentary",
            "Cinematic 9:16 vertical close up of ancient massive granite stone masonry enduring rushing river waters, historical engineering realism, 8k"
        ],
        "engagement_question": "இரண்டாயிரம் ஆண்டுகள் பழமையான கல்லணையை தமிழர்களின் மிகப்பெரிய பொறியியல் மைல்கல்லாக ஏற்கலாமா?"
    },
    {
        "category": "gk",
        "topic_id": "tardigrades_immortal_water_bears",
        "headline": "டார்டிகிரேட்: விண்வெளியிலும் உறைபனியிலும் சாகாமல் வாழும் விசித்திர உயிரி!",
        "voiceover_script": "ஒரு மில்லிமீட்டருக்கும் குறைவான அளவுடைய டார்டிகிரேட் அல்லது நீர் கரடி எனப்படும் நுண்ணுயிரி உலகின் மிகக் கடுமையான சூழலிலும் அழியாமல் வாழும் ஆற்றல் கொண்டது. மைனஸ் இருநூறு டிகிரி உறைபனி, கொதிக்கும் வெப்பம், கதிர்வீச்சு மற்றும் விண்வெளியின் வெற்றிடத்தைக் கூட தாங்கி முப்பது ஆண்டுகளுக்குப் பிறகும் மீண்டும் உயிர்வாழும் தன்மை இதற்கு உண்டு.",
        "visual_prompt": "Hyperdetailed 9:16 vertical electron microscope 3D visualization of a tardigrade water bear on moss leaf, scientific documentary aesthetic, 8k",
        "visual_prompts": [
            "Hyperdetailed 9:16 vertical electron microscope 3D visualization of a tardigrade water bear on moss leaf, scientific documentary aesthetic, 8k",
            "Cinematic 9:16 vertical artistic representation of microscopic tardigrade floating calmly in starry deep cosmic space, glowing nebula background, 8k"
        ],
        "engagement_question": "இயற்கையின் இந்த அழிக்க முடியாத உயிரினம் உங்களுக்கு ஆச்சரியத்தை தருகிறதா?"
    },
    {
        "category": "gk",
        "topic_id": "honeybee_waggle_dance_language",
        "headline": "தேன் தேனீக்களின் நடன மொழி: பூக்கள் இருக்கும் திசையை எப்படி பகிர்கின்றன?",
        "voiceover_script": "தேன் தேனீக்கள் பூக்கள் இருக்கும் இடத்தை மற்ற தேனீக்களுக்கு நடனத்தின் மூலமாகவே துல்லியமாக விவரிக்கின்றன என்பது அறிவியல் பூர்வமாக நிரூபிக்கப்பட்டுள்ளது. வேகில் நடனம் எனப்படும் இந்த அசைவுகள் மூலம் சூரியனின் கோணம், தூரம் மற்றும் காற்றின் வேகத்தைக் கூட கணக்கிட்டு சரியான திசையை கூட்டிற்கு தெரிவிக்கும் விந்தை இவற்றில் காணப்படுகிறது.",
        "visual_prompt": "Cinematic 9:16 vertical macro photograph of honeybees on golden honeycomb inside sunlit wooden hive, warm amber honey glow, National Geographic 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical macro photograph of honeybees on golden honeycomb inside sunlit wooden hive, warm amber honey glow, National Geographic 8k",
            "Cinematic 9:16 vertical close up of a single worker bee landing on a vibrant blooming yellow wildflower, pollen grains visible, 8k"
        ],
        "engagement_question": "தேனீக்களின் இந்த அதிசய தகவல் பரிமாற்றம் மனிதர்களின் மொழியை விட ஆச்சரியமானது என்று நினைக்கிறீர்களா?"
    },
    {
        "category": "gk",
        "topic_id": "immortal_jellyfish_reversing_age",
        "headline": "சாகா வரம் பெற்ற ஜெல்லிமீன்: முதுமையில் இருந்து மீண்டும் குழந்தையாக மாறும் விந்தை!",
        "voiceover_script": "இயற்கையில் உயிரியல் ரீதியாக மரணமே இல்லாத ஒரே உயிரினம் டூரிடாப்சிஸ் டோர்னி எனப்படும் ஜெல்லிமீன் ஆகும். காயம் அல்லது முதுமை அடையும் போது, தன் செல்களை மீண்டும் மாற்றி இளமை நிலைக்குத் திரும்பும் அசாத்திய ஆற்றல் இதற்கு உண்டு. இந்த சுழற்சி முடிவில்லாமல் தொடர்வதால் கோட்பாட்டு ரீதியாக இதற்கு இயற்கையான மரணமே கிடையாது.",
        "visual_prompt": "Cinematic 9:16 vertical underwater photograph of a translucent bioluminescent immortal jellyfish pulsing in deep sapphire ocean waters, glowing tentacles, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical underwater photograph of a translucent bioluminescent immortal jellyfish pulsing in deep sapphire ocean waters, glowing tentacles, 8k",
            "Cinematic 9:16 vertical macro view of delicate glowing bell of Turritopsis dohrnii jellyfish floating gracefully past deep sea coral, 8k"
        ],
        "engagement_question": "மனிதர்களுக்கும் இது போன்ற சாகா வரம் கிடைத்தால் உலகம் எப்படி இருக்கும்?"
    },
    {
        "category": "science",
        "topic_id": "james_webb_first_stars_universe",
        "headline": "ஜேம்ஸ் வெப் தொலைநோக்கி: பிரபஞ்சம் தோன்றிய தொடக்க கால ரகசியங்கள்!",
        "voiceover_script": "பூமியில் இருந்து பதினைந்து லட்சம் கிலோமீட்டர் தொலைவில் உள்ள ஜேம்ஸ் வெப் விண்வெளி தொலைநோக்கி, பிரபஞ்சம் உருவான தொடக்க காலத்து ஒளியைப் படம் பிடித்துள்ளது. பதிமூன்று பில்லியன் ஆண்டுகளுக்கு முன்பு உருவான முதல் விண்மீன் திரள்களைக் காட்டும் இந்த படங்கள், பிரபஞ்சத்தின் தொடக்க ரகசியங்களை மனித குலத்திற்கு வெளிச்சமிட்டுக் காட்டுகின்றன.",
        "visual_prompt": "Astounding 9:16 vertical deep space telescope view showing vibrant cosmic nebulae, swirling golden spiral galaxies, and sparkling birth of ancient stars, 8k",
        "visual_prompts": [
            "Astounding 9:16 vertical deep space telescope view showing vibrant cosmic nebulae, swirling golden spiral galaxies, and sparkling birth of ancient stars, 8k",
            "Cinematic 9:16 vertical view of golden hexagonal mirrors of James Webb space telescope gleaming against dark infinite starry cosmos, 8k"
        ],
        "engagement_question": "பிரபஞ்சத்தில் நாம் மட்டுமே தனியாக வாழ்கிறோமா அல்லது வேறு உயிரினங்கள் இருக்குமா?"
    },
    {
        "category": "science",
        "topic_id": "neutron_star_teaspoon_billion_tons",
        "headline": "நியூட்ரான் விண்மீன்: ஒரு ஸ்பூன் மண்ணின் எடை நூறு கோடி டன்!",
        "voiceover_script": "ஒரு பெரிய நட்சத்திரம் தனது ஆயுட்காலம் முடிந்து வெடித்துச் சிதறும் போது நியூட்ரான் நட்சத்திரமாக மாறுகிறது. வெறும் இருபது கிலோமீட்டர் அகலமுள்ள இந்த விண்மீனின் அடர்த்தி கற்பனைக்கு அப்பாற்பட்டது. இதன் ஒரு தேக்கரண்டி அளவு பொருள் பூமியில் நூறு கோடி டன் எடையைக் கொண்டிருக்கும். இதன் ஈர்ப்பு விசை அதீத வேகத்தில் சுழன்று ஒளியை வீசும்.",
        "visual_prompt": "Epic 9:16 vertical rendering of a spinning neutron star pulsar emitting blinding polar radiation beams across cosmos, extreme gravity distortion, 8k",
        "visual_prompts": [
            "Epic 9:16 vertical rendering of a spinning neutron star pulsar emitting blinding polar radiation beams across cosmos, extreme gravity distortion, 8k",
            "Cinematic 9:16 vertical viewpoint of glowing ultra-dense neutron core with intense magnetic field lines warping space time grid, 8k"
        ],
        "engagement_question": "விண்வெளியின் இந்த அதீத சக்தி பற்றிய தகவல் உங்களுக்கு வியப்பைத் தருகிறதா?"
    },
    {
        "category": "science",
        "topic_id": "aurora_borealis_solar_wind_spectacle",
        "headline": "அரோரா நார்தர்ன் லைட்ஸ்: இரவு வானில் நடனமாடும் மாயாஜால வண்ணங்கள்!",
        "voiceover_script": "பூமியின் துருவப் பகுதிகளில் இரவு வானில் பச்சை, ஊதா மற்றும் இளஞ்சிவப்பு வண்ணங்கள் நடனமாடுவது போல தோன்றும் அரோரா விண்வெளி ஆச்சரியம் ஆகும். சூரியனில் இருந்து வெளிப்படும் மின்னூட்டத் துகள்கள் பூமியின் காந்தப்புலத்துடன் மோதும் போது இந்த அதிசய வண்ண ஒளி உமிழப்படுகிறது. பூமியின் காந்தப்புலம் நம்மை பாதுகாப்பதற்கான வெளிப்படையான காட்சி சான்றாகும்.",
        "visual_prompt": "Breathtaking 9:16 vertical night photography of vivid green and violet Aurora Borealis dancing across snowy Arctic mountain landscape, crystal clear starry sky, 8k",
        "visual_prompts": [
            "Breathtaking 9:16 vertical night photography of vivid green and violet Aurora Borealis dancing across snowy Arctic mountain landscape, crystal clear starry sky, 8k",
            "Cinematic 9:16 vertical reflection of vibrant dancing northern lights in tranquil icy Nordic fjord waters, majestic silhouette, 8k"
        ],
        "engagement_question": "இந்த அதிசய நார்தர்ன் லைட்ஸ் வண்ணங்களை நேரில் பார்க்க உங்களுக்கு ஆசை உள்ளதா?"
    },
    {
        "category": "story",
        "topic_id": "empty_boat_on_river_anger_management",
        "headline": "வெற்றுப் படகு தத்துவம்: உங்கள் கோபத்தை கட்டுப்படுத்தும் ஒரு நிமிட ஞானக் கதை!",
        "voiceover_script": "ஒரு ஞானி நதியின் நடுவே படகில் தியானம் செய்து கொண்டிருந்தார். திடீரென மற்றொரு படகு வேகமாக வந்து இவர் படகில் மோதியது. ஞானி கோபத்துடன் கண்களைத் திறந்து திட்ட முற்பட்டார், ஆனால் எதிரில் மோதிய படகில் யாருமில்லை, அது காற்றில் அடித்து வரப்பட்ட வெற்றுப் படகு. மனிதர்களும் அப்படித்தான், மற்றவர்களின் செயல்களை வெற்றுப் படகாகப் பாருங்கள், கோபம் தானாக மறையும்.",
        "visual_prompt": "Serene 9:16 vertical cinematic photograph of a wooden boat floating on misty tranquil river at dawn, calm water ripples, Zen atmosphere, 8k",
        "visual_prompts": [
            "Serene 9:16 vertical cinematic photograph of a wooden boat floating on misty tranquil river at dawn, calm water ripples, Zen atmosphere, 8k",
            "Cinematic 9:16 vertical peaceful silhouette of a meditating monk in a small wooden skiff surrounded by soft morning fog and lotus flowers, 8k"
        ],
        "engagement_question": "மற்றவர்களின் கோபத்தை உங்களால் வெற்றுப் படகாக புறக்கணிக்க முடிகிறதா?"
    },
    {
        "category": "story",
        "topic_id": "bamboo_tree_five_years_underground",
        "headline": "சீன மூங்கில் தத்துவம்: உங்கள் உழைப்பு வீண் போகாது என்பதற்கான கதை!",
        "voiceover_script": "சீன மூங்கில் விதையை நட்டு தினமும் தண்ணீர் ஊற்றினாலும், முதல் நான்கு ஆண்டுகள் வரை அது நிலத்திற்கு மேலே ஒரு அங்குலம் கூட வளராது. ஆனால் ஐந்தாவது ஆண்டில், வெறும் ஆறு வாரங்களில் அது எண்பது அடி உயரத்திற்கு பிரம்மாண்டமாக வளரும். அந்த நான்கு ஆண்டுகளும் அது நிலத்தின் அடியில் ஆழமாக வேரூன்றிக்கொண்டிருந்தது. உங்கள் முயற்சிகளும் அப்படித்தான், நம்பிக்கை தளரவிடாதீர்கள்.",
        "visual_prompt": "Majestic 9:16 vertical view looking up through towering giant emerald bamboo forest stalks towards morning sunbeams, peaceful green glow, 8k fine art",
        "visual_prompts": [
            "Majestic 9:16 vertical view looking up through towering giant emerald bamboo forest stalks towards morning sunbeams, peaceful green glow, 8k fine art",
            "Cinematic 9:16 vertical macro shot of fresh green bamboo shoot breaking through dark rich soil, morning dew drops glistening, 8k"
        ],
        "engagement_question": "வாழ்க்கையில் உடனடி வெற்றி கிடைக்காத போது நீங்கள் பொறுமையைக் கடைப்பிடிக்கிறீர்களா?"
    },
    {
        "category": "story",
        "topic_id": "king_solomon_ring_this_too_shall_pass",
        "headline": "இதுவும் கடந்து போகும்: வாழ்க்கையின் உச்சகட்ட உண்மை உணர்த்தும் கதை!",
        "voiceover_script": "மகிழ்ச்சியாக இருக்கும் போது கர்வத்தை அடக்கவும், துயரத்தில் இருக்கும் போது தைரியத்தை ஊட்டவும் ஒரு வாசகம் வேண்டும் என்று மன்னன் ஞானியிடம் கேட்டான். ஞானி மன்னனுக்கு ஒரு மோதிரத்தைக் கொடுத்து, இதில் எழுதியுள்ளதை வாசியுங்கள் என்றார். அதில் இதுவும் கடந்து போகும் என்று பொறிக்கப்பட்டிருந்தது. வாழ்க்கையில் இன்பமும் துன்பமும் நிரந்தரமில்லை என்பதை இது நினைவுபடுத்துகிறது.",
        "visual_prompt": "Cinematic 9:16 vertical dramatic photograph of an ancient royal gold signet ring with engraved script resting on worn velvet pillow in royal palace, 8k",
        "visual_prompts": [
            "Cinematic 9:16 vertical dramatic photograph of an ancient royal gold signet ring with engraved script resting on worn velvet pillow in royal palace, 8k",
            "Cinematic 9:16 vertical thoughtful king gazing through arched palace balcony at sunrise over majestic kingdom, dignified atmosphere, 8k"
        ],
        "engagement_question": "இதுவும் கடந்து போகும் என்ற வாசகம் உங்களுக்கு எப்போதாவது மன அமைதியை தந்துள்ளதா?"
    }
]

def load_evergreen_state():
    if os.path.exists(EVERGREEN_STATE_FILE):
        try:
            with open(EVERGREEN_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_category_index": -1, "used_topics": []}

def save_evergreen_state(state):
    try:
        with open(EVERGREEN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save evergreen state: {e}")

def get_used_evergreen_identifiers():
    """Aggregates all used topic IDs and headlines across state, history, and seen files to prevent any repetition."""
    used = set()
    state = load_evergreen_state()
    for t in state.get("used_topics", []):
        used.add(str(t).strip().lower())

    h_file = os.path.join(os.path.dirname(__file__), "reels_history.json")
    if os.path.exists(h_file):
        try:
            with open(h_file, "r", encoding="utf-8") as f:
                hist = json.load(f)
                if isinstance(hist, list):
                    for item in hist:
                        if item.get("headline"):
                            clean_h = re.sub(r'[\W_]+', '', item["headline"].strip().lower())
                            if clean_h:
                                used.add(clean_h)
        except Exception:
            pass

    s_file = os.path.join(os.path.dirname(__file__), "seen_articles.json")
    if os.path.exists(s_file):
        try:
            with open(s_file, "r", encoding="utf-8") as f:
                seen = json.load(f)
                if isinstance(seen, list):
                    for s in seen:
                        if isinstance(s, str) and s.startswith("title:"):
                            used.add(s[6:].strip().lower())
        except Exception:
            pass

    return used

def get_next_category():
    state = load_evergreen_state()
    curr_idx = state.get("last_category_index", -1)
    next_idx = (curr_idx + 1) % len(CATEGORIES)
    state["last_category_index"] = next_idx
    save_evergreen_state(state)
    return CATEGORIES[next_idx]

def generate_evergreen_with_gemini(category_info, recent_topics):
    """
    Prompts Gemini to create a fresh, high-engagement Tamil micro-content Reel.
    Tries gemini-flash-lite-latest first, falling back to gemini-flash-latest.
    """
    if not GEMINI_API_KEY:
        return None

    cat_id = category_info["id"]
    cat_desc = category_info["theme_desc"]

    prompt = f"""
You are an expert Tamil storyteller, historian, and viral content creator for Facebook Reels.
Create an exciting, mind-blowing, and highly shareable 30-40 second micro-Reel in Tamil.

CATEGORY: {category_info['name']} ({cat_id})
THEME INSPIRATION: {cat_desc}

DO NOT repeat any of these recently used topics:
{json.dumps(recent_topics[-25:], ensure_ascii=False)}

REQUIREMENTS:
1. "headline": A punchy, curiosity-inducing Tamil headline (8-12 words max) suitable for a 9:16 broadcast card.
2. "voiceover_script": A captivating, fast-paced narration in pure, spoken Tamil (~40-60 words, ~25-35 seconds of speech).
   - Hook the viewer in the VERY FIRST sentence with an intriguing question or statement.
   - Tell a complete, fascinating story or mind-blowing fact.
   - ABSOLUTELY NO greetings (NO "வணக்கம்", NO "இன்றைய"). Jump directly into the narrative.
   - NO outro CTAs (NO "கமெண்ட் செய்யுங்கள்", NO "லைக் செய்யுங்கள்"). End with a memorable, thought-provoking punchline.
   - CRITICAL PRONUNCIATION / TRANSLITERATION RULE: The neural voice model reads ONLY Tamil script fluently. NEVER write English alphabet words in "voiceover_script"! If any English term, proper noun, technical term, brand, or number name appears (e.g. "7 wonders", "CCTV", "AI", "DNA", "James Webb"), you MUST transliterate its phonetic pronunciation in Tamil script (e.g., write "7 ஒண்டெர்ஸ்", "சிசிடிவி", "ஏஐ", "டிஎன்ஏ", "ஜேம்ஸ் வெப்"). Every word in voiceover_script must be in pure Tamil script!
3. "visual_prompts": A list of 2 distinct, complementary English visual prompts for a 9:16 vertical AI image generator (Flux/SDXL).
   - Each prompt: "Cinematic 9:16 vertical photograph of [detailed scene], [lighting], [mood], 8k, photorealistic documentary style".
   - The 2 prompts must show 2 different visual angles representing this story.
   - NO text, NO words, NO logos in the visuals.
4. "engagement_question": A thoughtful question in Tamil asking viewers for their opinion/perspective.
5. "topic_id": A short unique slug in English (e.g. "keezhadi_pottery_secret", "human_brain_petabytes").

Return ONLY valid JSON matching this schema:
{{
  "headline": "...",
  "voiceover_script": "...",
  "visual_prompts": ["...", "..."],
  "engagement_question": "...",
  "topic_id": "..."
}}
"""
    models_to_try = ["gemini-flash-lite-latest", "gemini-flash-latest"]
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.85,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(url, json=payload, timeout=18)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                res = json.loads(raw_text)
                if res.get("headline") and res.get("voiceover_script"):
                    if res.get("visual_prompts") and isinstance(res["visual_prompts"], list):
                        res["visual_prompt"] = res["visual_prompts"][0]
                    elif res.get("visual_prompt"):
                        res["visual_prompts"] = [res["visual_prompt"]]
                    return res
            elif resp.status_code == 429:
                print(f"Gemini {model_name} rate limited (429), trying next model...")
                continue
        except Exception as e:
            print(f"Notice: Gemini evergreen attempt with {model_name} failed: {e}")
            continue

    return None

def get_evergreen_story():
    """
    Retrieves the next unique evergreen story in rotation:
    - Rotates category: history -> gk -> science -> story
    - Calls Gemini Flash to generate completely fresh, non-repeated content
    - Falls back to 32+ rich curated library topics with strict non-repeating memory
    """
    category = get_next_category()
    state = load_evergreen_state()
    used_identifiers = get_used_evergreen_identifiers()

    # 1. Try Gemini dynamic generation first
    story_data = generate_evergreen_with_gemini(category, list(used_identifiers))
    if story_data:
        topic_id = story_data.get("topic_id") or f"{category['id']}_{int(time.time())}"
        story_data["category_id"] = category["id"]
        story_data["category_info"] = category
        story_data["voiceover_script"] = transliterate_english_to_tamil(story_data.get("voiceover_script", ""))
        
        # Reload state to avoid index overwrite
        current_state = load_evergreen_state()
        current_state["used_topics"].append(topic_id)
        if len(current_state["used_topics"]) > 300:
            current_state["used_topics"] = current_state["used_topics"][-300:]
        save_evergreen_state(current_state)
        return story_data

    # 2. Curated library fallback: filter out ANY previously used topic ID or headline
    available = []
    for item in CURATED_FALLBACK_BANK:
        t_id = item["topic_id"].strip().lower()
        clean_h = re.sub(r'[\W_]+', '', item["headline"].strip().lower())
        if t_id not in used_identifiers and clean_h not in used_identifiers:
            available.append(item)

    if not available:
        # All 32 curated topics used: only retain the most recent 10 to allow older ones to safely recirculate
        current_state = load_evergreen_state()
        current_state["used_topics"] = current_state.get("used_topics", [])[-10:]
        save_evergreen_state(current_state)
        used_identifiers = get_used_evergreen_identifiers()
        available = [item for item in CURATED_FALLBACK_BANK if item["topic_id"].strip().lower() not in used_identifiers]
        if not available:
            available = CURATED_FALLBACK_BANK

    # Prefer a story matching current rotating category if available
    cat_matches = [item for item in available if item["category"] == category["id"]]
    pool = cat_matches if cat_matches else available
    chosen = dict(random.choice(pool))

    cat_match = next((c for c in CATEGORIES if c["id"] == chosen["category"]), CATEGORIES[1])
    chosen["category_id"] = chosen["category"]
    chosen["category_info"] = cat_match
    chosen["voiceover_script"] = transliterate_english_to_tamil(chosen.get("voiceover_script", ""))

    current_state = load_evergreen_state()
    current_state["used_topics"].append(chosen["topic_id"])
    save_evergreen_state(current_state)
    return chosen

def fetch_evergreen_visual(visual_prompt, category_id="gk", suffix=""):
    """
    Downloads or renders a 9:16 vertical image for the evergreen reel:
    1. Tries Pollinations Flux AI generator (1080x1920) with prompt.
    2. Fallback to curated high-resolution category visual.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_filename = f"evergreen_visual_{int(time.time())}{suffix}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    temp_raw = os.path.join(OUTPUT_DIR, f"temp_ev_{int(time.time())}{suffix}.jpg")

    # 1. Try Pollinations Flux (Fast & Free 9:16)
    if visual_prompt:
        try:
            clean_p = visual_prompt.replace("\n", " ").strip()[:200]
            encoded = quote(clean_p)
            ai_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&model=flux"
            resp = _session.get(ai_url, timeout=18)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(temp_raw, "wb") as f:
                    f.write(resp.content)
                create_ambient_vertical_canvas(temp_raw, out_path)
                if os.path.exists(temp_raw):
                    try:
                        os.remove(temp_raw)
                    except Exception:
                        pass
                if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                    print(f"🎨 Successfully generated AI Flux visual for: {clean_p[:40]}...")
                    return out_path
        except Exception as e:
            print(f"Notice: Pollinations Flux visual notice: {e}")

    # 2. Try High-Quality Category Editorial Fallback
    category_fallbacks = {
        "history": "https://images.unsplash.com/photo-1590059390046-5381d6d23192?w=1080&h=1920&fit=crop&q=80",
        "science": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1080&h=1920&fit=crop&q=80",
        "gk": "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=1080&h=1920&fit=crop&q=80",
        "story": "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1080&h=1920&fit=crop&q=80"
    }
    fb_url = category_fallbacks.get(category_id, category_fallbacks["gk"])
    try:
        resp = _session.get(fb_url, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 10000:
            with open(temp_raw, "wb") as f:
                f.write(resp.content)
            create_ambient_vertical_canvas(temp_raw, out_path)
            if os.path.exists(temp_raw):
                try:
                    os.remove(temp_raw)
                except Exception:
                    pass
            return out_path
    except Exception as e:
        print(f"Notice: Category fallback visual notice: {e}")

    return None

def fetch_evergreen_visuals(visual_prompts, category_id="gk"):
    """
    Downloads or renders MULTIPLE 9:16 vertical images for an evergreen reel
    so the video dynamically transitions through multiple scenes.
    """
    if not isinstance(visual_prompts, (list, tuple)):
        visual_prompts = [visual_prompts] if visual_prompts else []

    visual_paths = []
    for idx, prompt_text in enumerate(visual_prompts[:3]):
        vp = fetch_evergreen_visual(prompt_text, category_id, suffix=f"_{idx}")
        if vp and os.path.exists(vp):
            visual_paths.append(vp)

    return visual_paths
