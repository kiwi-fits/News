import os
import json
import time
import random
import re
from urllib.parse import quote
import requests
from config import GEMINI_API_KEY, OUTPUT_DIR, CHRISTIAN_STATE_FILE, CHRISTIAN_HISTORY_FILE
from media_extractor import create_ambient_vertical_canvas
from tamil_transliteration import transliterate_english_to_tamil

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

_session = requests.Session()
_session.headers.update(HEADERS)

CHRISTIAN_CATEGORIES = [
    {
        "id": "promise",
        "name": "காலை வாக்குத்தத்தம்",
        "badge_tag": "🌅 காலை வாக்குத்தத்தம்",
        "time_slot": "06:00 AM",
        "theme_desc": "Morning promise of God, protection, grace, blessing for the day, removing fear, standing on faith (e.g. Joshua 1:5, Isaiah 41:10, Jeremiah 29:11).",
        "hashtags": "#JesusHearsYou #காலைவாக்குத்தத்தம் #MorningPromise #DailyVerse #Faith #Blessing #Reels"
    },
    {
        "id": "wisdom",
        "name": "நடைமுறை வேத ஞானம்",
        "badge_tag": "📖 நடைமுறை வேத ஞானம்",
        "time_slot": "12:30 PM",
        "theme_desc": "Practical Biblical wisdom from Proverbs, Psalms, or teachings of Jesus for daily life, patience, peaceful speech, family love, overcoming stress.",
        "hashtags": "#JesusHearsYou #வேதஞானம் #BiblicalWisdom #Proverbs #InnerPeace #ChristianQuotes #Reels"
    },
    {
        "id": "parable",
        "name": "விசுவாச சாட்சி & உவமை",
        "badge_tag": "✨ விசுவாச சாட்சி & உவமை",
        "time_slot": "04:30 PM",
        "theme_desc": "One-minute inspiring faith parable, Jesus's parables (Lost Sheep, Good Samaritan, Mustard Seed), or moving Christian testimony of God's miraculous help.",
        "hashtags": "#JesusHearsYou #விசுவாசம் #FaithStory #GospelParable #ChristianStories #Motivation #Reels"
    },
    {
        "id": "mystery",
        "name": "வேதாகம ஆச்சரியங்கள்",
        "badge_tag": "✝️ வேதாகம ஆச்சரியங்கள்",
        "time_slot": "07:30 PM",
        "theme_desc": "Fascinating Biblical history, archaeological discoveries (Noah's Ark, Dead Sea Scrolls, Red Sea crossing, Jerusalem temple, Apostles' footprints).",
        "hashtags": "#JesusHearsYou #வேதாகமவரலாறு #BibleFacts #Archaeology #BibleHistory #Knowledge #Reels"
    },
    {
        "id": "prayer",
        "name": "இரவு அமைதி ஜெபம்",
        "badge_tag": "🌙 இரவு அமைதி ஜெபம்",
        "time_slot": "09:30 PM",
        "theme_desc": "Peaceful bedtime prayer, releasing anxiety to God, Psalm 91/Psalm 23 reflection, blessing for sweet sleep, gratitude for the day.",
        "hashtags": "#JesusHearsYou #இரவுஜெபம் #NightPrayer #PeacefulSleep #Psalm91 #Surrender #Reels"
    }
]

# Rich Curated Devotional Fallback Bank (7 topics per category = 35 topics)
CURATED_CHRISTIAN_BANK = [
    # 1. MORNING PROMISE (06:00 AM)
    {
        "category": "promise",
        "topic_id": "joshua_1_5_never_leave_you",
        "headline": "நான் உன்னை விட்டு விலகுவதுமில்லை, உன்னை கைவிடுவதுமில்லை",
        "verse_reference": "யோசுவா 1:5 (Joshua 1:5)",
        "voiceover_script": "இன்றைய புதிய நாளில் நீங்கள் எதிர்கொள்ளும் எந்த சவாலையும் கண்டு அஞ்சாதீர்கள். மனிதர்கள் கைவிட்டாலும், சர்வவல்லமையுள்ள கர்த்தர் உங்களை ஒருபோதும் கைவிடமாட்டார். அவர் உங்கள் முன்பாகச் சென்று கோணலான வழிகளைச் செவ்வையாக்குவார். உங்கள் பாரங்களை அவரிடம் ஒப்புக்கொடுத்து நம்பிக்கையோடு உங்கள் நாளைத் தொடங்குங்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical view of golden sunrise rays breaking through heavenly clouds over majestic peaceful mountain vista, 8k documentary style",
            "Cinematic 9:16 vertical close up of an open Holy Bible with soft golden morning sunlight illuminating the pages, reverent aesthetic, 8k"
        ],
        "engagement_question": "இந்த வாக்குத்தத்தத்தை உங்கள் விசுவாசத்தோடு ஆமென் என்று கமெண்ட் செய்யுங்கள்!"
    },
    {
        "category": "promise",
        "topic_id": "isaiah_41_10_fear_not_i_am_with_you",
        "headline": "பயப்படாதே, நான் உன்னுடனே இருக்கிறேன்; திகையாதே, நான் உன் தேவன்",
        "verse_reference": "ஏசாயா 41:10 (Isaiah 41:10)",
        "voiceover_script": "உங்கள் மனதில் எழும் கவலைகள் மற்றும் பயங்களை இன்றே தேவனிடம் விட்டுவிடுங்கள். அவர் தம்முடைய நீதியின் வலதுகரத்தினால் உங்களைத் தாங்கி நடத்துவார். நீங்கள் பலவீனமாக இருக்கும் தருணங்களில் அவருடைய பலம் உங்கள் வாழ்வில் பரிபூரணமாக விளங்கும். திடமனதாயிருங்கள், கர்த்தர் உங்கள் பட்சத்தில் இருக்கிறார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouette of a person standing atop a hill gazing at a radiant heavenly sunrise, peaceful breeze, 8k fine art",
            "Cinematic 9:16 vertical macro shot of warm golden light beams falling upon praying hands held peacefully, high resolution 8k"
        ],
        "engagement_question": "கர்த்தர் உங்களோடு இருக்கிறார் என்பதை நீங்கள் முழுமையாக விசுவாசிக்கிறீர்களா?"
    },
    {
        "category": "promise",
        "topic_id": "jeremiah_29_11_thoughts_of_peace",
        "headline": "நீங்கள் எதிர்பார்த்திருக்கும் முடிவை உங்களுக்குத் தரும்படிக்கு நான் உங்கள்மேல் நினைத்திருக்கிறேன்",
        "verse_reference": "எரேமியா 29:11 (Jeremiah 29:11)",
        "voiceover_script": "உங்கள் எதிர்காலத்தைக் குறித்து ஒருபோதும் கலங்காதீர்கள். கர்த்தர் உங்கள் வாழ்வில் தீமைக்கல்ல, உங்களுக்கு சமாதானத்தையும் நல்வாழ்வையும் அருளும் திட்டங்களையே வைத்துள்ளார். இப்போது நடக்கும் தடைகள் அனைத்தும் உங்களை ஆசீர்வதிக்கப் போகும் பெரிய திட்டத்தின் ஒரு பகுதியே. தேவனுடைய நேரம் மிகச் சரியானது.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene path winding through tranquil sunlit olive groves towards a glowing horizon, warm gold light, 8k",
            "Cinematic 9:16 vertical view looking up at soaring white dove flying through sunlit morning clouds, heavenly blue sky, 8k"
        ],
        "engagement_question": "தேவனின் நல்வழியை நம்பி ஆமென் என்று பகிருங்கள்!"
    },
    {
        "category": "promise",
        "topic_id": "philippians_4_13_christ_strengthens_me",
        "headline": "என்னைப் பெலப்படுத்துகிற கிறிஸ்துவினாலே எல்லாவற்றையுஞ்செய்ய எனக்குப் பெலனுண்டு",
        "verse_reference": "பிலிப்பியர் 4:13 (Philippians 4:13)",
        "voiceover_script": "உங்கள் சொந்த பலத்தில் நம்பிக்கை வைப்பதை விட, உங்களுக்குள் வாழும் கிறிஸ்துவின் பலத்தில் சார்ந்து இருங்கள். உங்கள் முன்னிருக்கும் எந்தப் பெரிய மலையையும் விசுவாசத்தினால் தகர்க்க முடியும். இன்றைய நாளில் உங்கள் ஒவ்வொரு காரியத்திலும் தெய்வீக ஞானமும் வெற்றியும் உங்களுக்கு உண்டாவதாக.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic view of granite mountain peaks bathed in golden morning sunbeams, eternal steadfastness, 8k",
            "Cinematic 9:16 vertical glowing warm cross standing steadfastly on green hill against dawn horizon, 8k documentary"
        ],
        "engagement_question": "கிறிஸ்துவின் பலத்தை நம்பி இன்றைய நாளைத் தொடங்குகிறீர்களா?"
    },
    {
        "category": "promise",
        "topic_id": "matthew_11_28_come_unto_me_rest",
        "headline": "வருத்தப்பட்டுப் பாரஞ்சுமக்கிறவர்களே! நீங்கள் எல்லாரும் என்னிடத்தில் வாருங்கள், நான் உங்களுக்கு இளைப்பாறுதல் தருவேன்",
        "verse_reference": "மத்தேயு 11:28 (Matthew 11:28)",
        "voiceover_script": "வாழ்வின் சுமைகள் உங்களை அழுத்துகிறதா? உங்கள் குடும்ப, பொருளாதார, மனப் போராட்டங்களை இயேசுவின் பாதத்தில் இறக்கி வையுங்கள். உலகம் தராத மெய்யான அமைதியையும் விடுதலையையும் அவர் உங்கள் இதயத்திற்குத் தருவார். அவருடைய நுகம் மெதுவாயும், அவருடைய சுமை இலகுவாயும் இருக்கிறது.",
        "visual_prompts": [
            "Cinematic 9:16 vertical tranquil lake with crystal clear reflections of snowcapped peaks at dawn, divine peace atmosphere, 8k",
            "Cinematic 9:16 vertical close up of gentle warm light enveloping praying hands, peaceful serenity, 8k"
        ],
        "engagement_question": "உங்கள் பாரங்களை இயேசுவிடம் கொடுத்து மன அமைதி பெற விரும்புகிறீர்களா?"
    },
    {
        "category": "promise",
        "topic_id": "psalm_121_1_2_my_help_comes_from_the_lord",
        "headline": "எனக்கு ஒத்தாசை வரும் பர்வதங்களுக்கு நேராக என் கண்களை ஏறெடுக்கிறேன்",
        "verse_reference": "சங்கீதம் 121:1-2 (Psalm 121:1-2)",
        "voiceover_script": "வானத்தையும் பூமியையும் படைத்த கர்த்தரிடமிருந்தே உங்களுக்கு உதவி வரும். அவர் உங்கள் காலைத் தள்ளாடவொட்டார்; உங்களைக் காக்கிறவர் ஒருபோதும் உறங்கவுமாட்டார், தூங்கவுமாட்டார். இன்றைய நாளில் உங்கள் போக்கையும் உங்கள் வரத்தையும் அவர் இப்போதும் என்றென்றைக்கும் பாதுகாப்பாராக.",
        "visual_prompts": [
            "Cinematic 9:16 vertical grand mountain landscape beneath a starry heaven turning into dawn, awe-inspiring creator majesty, 8k",
            "Cinematic 9:16 vertical open Bible resting beside a peaceful window looking out onto sunrise over misty valley, 8k"
        ],
        "engagement_question": "கர்த்தருடைய பாதுகாப்பை விசுவாசிக்கிறீர்களா? ஆமென் சொல்லுங்கள்!"
    },
    {
        "category": "promise",
        "topic_id": "romans_8_28_all_things_work_together_for_good",
        "headline": "தேவனிடத்தில் அன்புகூருகிறவர்களுக்குச் சகலமும் நன்மைக்கு ஏதுவாக நடக்கிறது",
        "verse_reference": "ரோமர் 8:28 (Romans 8:28)",
        "voiceover_script": "இன்று நடக்கும் காரியங்கள் உங்களுக்குப் புரியாமல் போகலாம். ஆனால் தேவனை நேசிக்கும் உங்களுக்கு எல்லாவற்றையும் நன்மையாக மாற்றித் தரும் சர்வவல்லவர் அவர். கண்ணீரை மகிழ்ச்சியாகவும், வேதனையை ஆசீர்வாதமாகவும் மாற்றும் தேவனுடைய அற்புத கரம் உங்கள் மேல் விளங்குகிறது.",
        "visual_prompts": [
            "Cinematic 9:16 vertical dramatic golden light ray illuminating a fresh blooming lily in a lush green valley, 8k realism",
            "Cinematic 9:16 vertical serene reflection of golden morning clouds in calm ocean water, divine restoration, 8k"
        ],
        "engagement_question": "உங்கள் வாழ்வில் கர்த்தர் நன்மை செய்வார் என்பதை நம்புகிறீர்களா?"
    },

    # 2. BIBLICAL WISDOM (12:30 PM)
    {
        "category": "wisdom",
        "topic_id": "proverbs_15_1_soft_answer_turns_wrath",
        "headline": "மெதுவான பிரதியுத்தரம் உக்கிரத்தை மாற்றும்; கடுஞ்சொல்லோ கோபத்தை எழுப்பும்",
        "verse_reference": "நீதிமொழிகள் 15:1 (Proverbs 15:1)",
        "voiceover_script": "கோபம் எழும் சூழல்களில் உங்கள் நாவைக் கட்டுப்படுத்துங்கள். மென்மையான ஒரு வார்த்தை கடுமையான பகையையும் சமாதானப்படுத்தும் ஆற்றல் கொண்டது. பிறர் கடுமையாகப் பேசினாலும், நீங்கள் பொறுமையையும் அன்பையும் வெளிப்படுத்துங்கள். தேவனுடைய ஞானம் உங்கள் வாயின் வார்த்தைகளை வழிநடத்தட்டும்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful zen-like water droplets falling onto a calm reflective pond, ripple effects, 8k aesthetic",
            "Cinematic 9:16 vertical warm sunbeams filtering through ancient olive tree branches, tranquil wisdom atmosphere, 8k"
        ],
        "engagement_question": "கோபத்தை வெல்லும் இந்த ஞானம் உங்கள் வாழ்க்கைக்கு அவசியமா?"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_3_5_trust_in_the_lord_with_all_heart",
        "headline": "உன் சுயபுத்தியின்மேல் சாயாமல், உன் முழு இருதயத்தோடும் கர்த்தரில் நம்பிக்கையாயிரு",
        "verse_reference": "நீதிமொழிகள் 3:5-6 (Proverbs 3:5-6)",
        "voiceover_script": "மனித அறிவு ஒரு குறிப்பிட்ட எல்லை வரை மட்டுமே பார்க்க முடியும். ஆனால் கர்த்தரோ ஆதியையும் அந்தத்தையும் அறிந்தவர். உங்கள் எல்லா வழிகளிலும் அவரை நினைத்துக் கொள்ளுங்கள், அப்பொழுது அவர் உங்கள் பாதைகளைச் செவ்வைப்படுத்துவார். கர்த்தரிடம் ஆலோசனை கேட்காமல் எந்த முடிவையும் எடுக்காதீர்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical old wooden compass and open Scripture on weathered rustic table, soft lantern glow, 8k",
            "Cinematic 9:16 vertical clear path cutting straight through lush green forest, morning sunlight leading forward, 8k"
        ],
        "engagement_question": "உங்கள் வாழ்க்கையின் முடிவுகளில் தேவனுடைய வழிகாட்டுதலை நாடுகிறீர்களா?"
    },
    {
        "category": "wisdom",
        "topic_id": "colossians_3_13_forgive_as_lord_forgave",
        "headline": "கர்த்தர் உங்களுக்கு மன்னித்ததுபோல, நீங்களும் ஒருவருக்கொருவர் மன்னியுங்கள்",
        "verse_reference": "கொலோசெயர் 3:13 (Colossians 3:13)",
        "voiceover_script": "மன்னிப்பு என்பது பிறருக்காக நீங்கள் செய்யும் உபகாரம் அல்ல; உங்கள் சொந்த இதயத்தின் அமைதிக்காக நீங்கள் எடுக்கும் தெய்வீக முடிவு. கசப்பையும் பகையையும் மனதில் சுமப்பது விஷத்தைக் குடிப்பது போன்றது. கிறிஸ்து உங்கள் பாவங்களை மன்னித்தது போல, மற்றவர்களின் தவறுகளை மனதார மன்னித்து விடுதலையோடு வாழுங்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical single glowing candle flame dispelling deep darkness, warm golden illumination, 8k",
            "Cinematic 9:16 vertical open hands releasing a white dove into crystal clear azure sky, freedom and peace, 8k"
        ],
        "engagement_question": "மன்னிக்கும் குணம் உங்களுக்கு மன அமைதியைத் தந்துள்ளதா?"
    },
    {
        "category": "wisdom",
        "topic_id": "matthew_6_33_seek_first_kingdom_of_god",
        "headline": "முதலாவது தேவனுடைய ராஜ்யத்தையும் அவருடைய நீதியையும் தேடுங்கள்",
        "verse_reference": "மத்தேயு 6:33 (Matthew 6:33)",
        "voiceover_script": "உணவு, உடை, செல்வம் என்று உலகப் பொருட்களுக்காக அதிகம் கவலைப்படாதீர்கள். இவைகளெல்லாம் உங்களுக்குத் தேவை என்பதை உங்கள் பரமபிதா அறிந்திருக்கிறார். உங்கள் முன்னுரிமைகளில் தேவனுக்கு முதலிடம் கொடுங்கள், அப்பொழுது இவை அனைத்தும் உங்களுக்குக் கூடக் கொடுக்கப்படும்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical wild lilies blooming radiantly in morning sunlight, dew drops sparkling, 8k nature realism",
            "Cinematic 9:16 vertical small colorful birds resting peacefully on flowering almond branch, divine care, 8k"
        ],
        "engagement_question": "உங்கள் அன்றாட வாழ்வில் தேவனுக்கு முதலிடம் கொடுக்கிறீர்களா?"
    },
    {
        "category": "wisdom",
        "topic_id": "james_1_19_quick_to_listen_slow_to_speak",
        "headline": "யாவரும் கேட்கிறதற்குத் தீவிரமாயும், பேசுகிறதற்குப் பொறுமையாயும் இருக்கக்கடவர்கள்",
        "verse_reference": "யாக்கோபு 1:19 (James 1:19)",
        "voiceover_script": "அதிகமாகப் பேசுகிறவன் தவறிழைப்பது எளிது, ஆனால் பிறர் சொல்வதைக் கேட்கிறவன் ஞானவான் ஆகிறான். ஒருவரை நியாயந்தீர்ப்பதற்கு முன்பாக அவருடைய உணர்வுகளைப் புரிந்து கொள்ளக் கற்றுக்கொள்ளுங்கள். உங்கள் நாவு காயப்படுத்துவதற்குப் பதிலாக, தேற்றுவதற்கும் ஆசீர்வதிப்பதற்கும் பயன்படட்டும்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene ancient monastery library illuminated by warm afternoon window light, holy books, 8k",
            "Cinematic 9:16 vertical calm stream flowing gently over smooth river stones, serene woodland atmosphere, 8k"
        ],
        "engagement_question": "பேசுவதை விட கேட்பது உறவுகளை பலப்படுத்தும் என்று நம்புகிறீர்களா?"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_4_23_keep_your_heart_with_diligence",
        "headline": "எல்லாக் காவலோடும் உன் இருதயத்தைக் காத்துக்கொள், அதினிடத்தினின்று ஜீவஊற்று புறப்படும்",
        "verse_reference": "நீதிமொழிகள் 4:23 (Proverbs 4:23)",
        "voiceover_script": "உங்கள் மனதில் நீங்கள் என்ன சிந்தனைகளை அனுமதிக்கிறீர்களோ, அதுவே உங்கள் வாழ்க்கையின் போக்கைத் தீர்மானிக்கிறது. பொறாமை, சந்தேகம், அவநம்பிக்கை போன்ற நச்சு எண்ணங்கள் உங்கள் உள்ளத்திற்குள் நுழைய விடாதீர்கள். தேவனுடைய வார்த்தைகளால் உங்கள் இதயத்தை நிரப்புங்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical pure crystal freshwater spring bubbling up from mossy rocks in pristine sunlit mountain, 8k",
            "Cinematic 9:16 vertical glowing warm heart motif formed by golden morning light and open Scripture, 8k"
        ],
        "engagement_question": "உங்கள் மனதை தூய்மையாக வைத்துக்கொள்ள தேவ வார்த்தைகளை தியானிக்கிறீர்களா?"
    },
    {
        "category": "wisdom",
        "topic_id": "philippians_4_6_be_anxious_for_nothing",
        "headline": "நீங்கள் ஒன்றுக்குங் கவலைப்படாமல், எல்லாவற்றையுங்குறித்து விண்ணப்பங்களை தேவனுக்குத் தெரியப்படுத்துங்கள்",
        "verse_reference": "பிலிப்பியர் 4:6-7 (Philippians 4:6-7)",
        "voiceover_script": "கவலைப்படுவதால் உங்கள் வாழ்க்கையின் ஒரு முழத்தையும் கூட்ட முடியாது. ஆனால் நன்றியறிதலோடு ஜெபிக்கும் போது, எல்லாப் புத்திக்கும் மேலான தேவ சமாதானம் உங்கள் இருதயங்களையும் சிந்தைகளையும் கிறிஸ்து இயேசுவுக்குள் காத்துக் கொள்ளும். கவலையை ஜெபமாக மாற்றுங்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical dramatic golden sunset casting gentle reflections across peaceful tide pools, 8k",
            "Cinematic 9:16 vertical rustic wooden altar in simple chapel, warm soft sunlight shining on cross, 8k"
        ],
        "engagement_question": "கவலைகளை ஜெபமாக மாற்றும்போது உங்களுக்கு அமைதி கிடைக்கிறதா?"
    },

    # 3. FAITH STORY & PARABLE (04:30 PM)
    {
        "category": "parable",
        "topic_id": "parable_lost_sheep_ninety_nine",
        "headline": "தொலைந்துபோன ஒரு ஆடு: உங்களைத் தேடி வரும் தேவ அன்பு!",
        "verse_reference": "லூக்கா 15:4-7 (Luke 15:4-7)",
        "voiceover_script": "தொண்ணூற்றொன்பது ஆடுகள் பத்திரமாக இருந்தாலும், வழிதவறிப் போன ஒரே ஒரு ஆட்டைத் தேடி மேய்ப்பன் கொடிய காடுகளிலும் அலைந்து திரிவான். அதைக் கண்டுபிடித்தவுடன் தோளின்மேல் சுமந்து மகிழ்வான். மனிதர்கள் உங்களைக் கைவிட்டாலும், உலகம் உங்களை ஒதுக்கி வைத்தாலும், இயேசுவின் கண்களில் நீங்கள் அவ்வளவு விலையேறப்பெற்றவர்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouette of a loving shepherd holding a lost lamb on grassy hillside at warm dusk, 8k",
            "Cinematic 9:16 vertical wide scenic view of gentle flock resting by still green pastures under golden evening sky, 8k"
        ],
        "engagement_question": "இயேசுவின் இந்த விலைமதிப்பில்லா அன்பை நீங்கள் உணர்ந்திருக்கிறீர்களா?"
    },
    {
        "category": "parable",
        "topic_id": "parable_house_built_on_rock",
        "headline": "கன்மலையின்மேல் கட்டப்பட்ட வீடு: சோதனைகளைத் தாங்கும் விசுவாசம்!",
        "verse_reference": "மத்தேயு 7:24-25 (Matthew 7:24-25)",
        "voiceover_script": "மணலின்மேல் கட்டப்பட்ட வீடு அமைதியான காலத்தில் அழகாகத் தெரியலாம், ஆனால் பெருமழை பெய்து பெருவெள்ளம் வரும் போது அது தரைமட்டமாகும். கன்மலையாகிய கிறிஸ்துவின் வார்த்தையின்மேல் தன் விசுவாசத்தை நிறுவுகிற மனிதன் எப்பேர்ப்பட்ட புயல் வீசினாலும் அசைக்கப்படாமல் நிலைத்து நிற்பான். உங்கள் அஸ்திபாரம் கிறிஸ்துவின் மேல் இருக்கட்டும்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone house standing firm upon towering coastal rock cliff against stormy ocean waves, 8k",
            "Cinematic 9:16 vertical majestic beam of golden sunlight breaking through dark storm clouds onto solid rock foundation, 8k"
        ],
        "engagement_question": "உங்கள் விசுவாசம் கன்மலையாகிய கிறிஸ்துவின் மேல் உறுதியாக உள்ளதா?"
    },
    {
        "category": "parable",
        "topic_id": "parable_mustard_seed_mountain_moving",
        "headline": "கடுகு விதையளவு விசுவாசம்: மலையையும் பெயர்க்கும் மகா சக்தி!",
        "verse_reference": "மத்தேயு 17:20 (Matthew 17:20)",
        "voiceover_script": "விதைகளிலேயே மிகச் சிறியதான கடுகு விதை, நிலத்தில் விழுந்து முளைக்கும் போது பெரிய மரமாகி ஆகாயத்துப் பறவைகளுக்கு நிழல் தருகிறது. உங்கள் விசுவாசம் இன்று சிறியதாகத் தோன்றலாம், ஆனால் ஜீவனுள்ள தேவனை நோக்கிய அந்த சிறு விசுவாசம் உங்கள் வாழ்வின் மிகப்பெரிய தடைகளையும் அப்புறப்படுத்தும் ஆற்றல் கொண்டது. நம்பிக்கையை இழக்காதீர்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical macro shot of tiny golden seed in palm of hand against sunlit green field, 8k",
            "Cinematic 9:16 vertical grand ancient oak tree spreading vast lush leafy branches into golden radiant sky, 8k"
        ],
        "engagement_question": "சிறு விசுவாசமும் தேவ கரத்தினால் பெரிதாகும் என்று விசுவாசிக்கிறீர்களா?"
    },
    {
        "category": "parable",
        "topic_id": "parable_good_samaritan_neighbor_love",
        "headline": "நல்ல சமாரியன்: நிபந்தனையற்ற அன்பு எங்கே தொடங்குகிறது?",
        "verse_reference": "லூக்கா 10:33-35 (Luke 10:33-35)",
        "voiceover_script": "காயப்பட்டு விழுந்து கிடந்த மனிதனைக் கண்டு மதத் தலைவர்களும் அதிகாரிகளும் விலகிச் சென்றனர். ஆனால் ஒரு சமாரியன் இரக்கமடைந்து அவன் காயங்களைக் கட்டி, தன் சொந்தப் பணத்தை செலவழித்துக் கவனித்தான். உண்மையான பக்தி என்பது வழிபாட்டுத் தலங்களில் மட்டுமல்ல, துன்பப்படுபவர்களுக்கு நீட்டும் இரக்கமுள்ள கரங்களிலேயே வாழ்கிறது.",
        "visual_prompts": [
            "Cinematic 9:16 vertical evocative scene of a traveler gently helping wounded person on dusty desert mountain road at sunset, 8k",
            "Cinematic 9:16 vertical warm vintage lantern resting on stone path beside caring hands, compassionate lighting, 8k"
        ],
        "engagement_question": "பிறருக்கு உதவும் இரக்கமுள்ள இதயம் நமக்கிருக்க வேண்டும் என்று ஏற்கிறீர்களா?"
    },
    {
        "category": "parable",
        "topic_id": "parable_prodigal_son_fathers_arms",
        "headline": "மனந்திரும்பிய மைந்தன்: மன்னிக்கத் தயாராகக் காத்திருக்கும் தகப்பன்!",
        "verse_reference": "லூக்கா 15:20-24 (Luke 15:20-24)",
        "voiceover_script": "தன் சொத்துக்களை அழித்து பாவியாகத் திரும்பி வந்த மகனைக் கண்ட தகப்பன், அவனைக் கண்டிக்கவில்லை; ஓடிவந்து கட்டித்தழுவி முத்தமிட்டு புதிய ஆடைகளை அணிவித்தான். நீங்கள் எவ்வளவு தூரம் தவறிச் சென்றிருந்தாலும், தேவனிடம் திரும்ப ஒருபோதும் தாமதமாகாது. அவர் உங்களை அன்போடு ஏற்றுக்கொள்ளக் காத்திருக்கிறார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouette of a father embracing returning son against warm golden sunset on open rustic field, 8k",
            "Cinematic 9:16 vertical golden welcoming open door of a warm country home glowing in gentle evening twilight, 8k"
        ],
        "engagement_question": "தேவனுடைய அளவிட முடியாத மன்னிக்கும் அன்பை நீங்கள் உணர்ந்திருக்கிறீர்களா?"
    },
    {
        "category": "parable",
        "topic_id": "faith_story_peter_walking_on_water",
        "headline": "தண்ணீரின் மேல் நடந்த பேதுரு: இயேசுவை நோக்கும் வரை மூழ்குவதில்லை!",
        "verse_reference": "மத்தேயு 14:28-31 (Matthew 14:28-31)",
        "voiceover_script": "கொந்தளிக்கும் கடலின் நடுவே இயேசுவின் வார்த்தையைக் கேட்டு பேதுரு தண்ணீரின் மேல் நடந்தான். ஆனால் அவன் புயலின் வேகத்தைப் பார்த்த போது மூழ்கத் தொடங்கினான். உங்கள் கண்களை சூழ்நிலைகளின் மேல் வைக்காதீர்கள்; இயேசுவின் மேல் வையுங்கள். அவர் உடனடியாகத் தம் கையை நீட்டி உங்களைத் தூக்கி நிறுத்துவார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical dramatic seascape of moonlit storm clouds with divine golden light beam illuminating water path, 8k",
            "Cinematic 9:16 vertical close up of a divine outstretched hand reaching into turbulent dark water to lift someone, 8k"
        ],
        "engagement_question": "சூழ்நிலைகளை விட இயேசுவை நோக்கிப் பார்க்கும்போது பயம் விலகுகிறதா?"
    },
    {
        "category": "parable",
        "topic_id": "faith_story_david_and_goliath_giant",
        "headline": "தாவீதும் கோலியாத்தும்: உங்கள் முன்னிருக்கும் ராட்சதர்களை எப்படி வீழ்த்துவது?",
        "verse_reference": "1 சாமுவேல் 17:45 (1 Samuel 17:45)",
        "voiceover_script": "ராட்சத உருவம் கொண்ட கோலியாத்தை எதிர்த்து சிறுவன் தாவீது வாளோடும் ஈட்டியோடும் செல்லவில்லை; சேனைகளின் கர்த்தருடைய நாமத்திலே சென்றான். உங்கள் வாழ்க்கையின் எதிரில் நிற்கும் எந்தப் பெரிய பிரச்சனையும் தேவனை விடப் பெரியதல்ல. யுத்தம் கர்த்தருடையது, அவர் உங்களுக்கு நிச்சயம் வெற்றி தருவார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient Valley of Elah with dramatic clouds, single slingshot stone resting on sunlit riverbed, 8k",
            "Cinematic 9:16 vertical silhouette of humble shepherd boy holding sling gazing fearlessly towards dawn horizon, 8k"
        ],
        "engagement_question": "உங்கள் வாழ்க்கையின் பிரச்சனைகளை தேவ நாமம் ஜெயிக்கும் என்று நம்புகிறீர்களா?"
    },

    # 4. BIBLE FACTS & HISTORY (07:30 PM)
    {
        "category": "mystery",
        "topic_id": "noahs_ark_mount_ararat_dimensions",
        "headline": "நோவாவின் பேழை: நவீன கப்பல் பொறியியலை மிஞ்சிய வேதாகம அற்புதம்!",
        "verse_reference": "ஆதியாகமம் 6:15 (Genesis 6:15)",
        "voiceover_script": "ஆயிரக்கணக்கான ஆண்டுகளுக்கு முன்பு நோவா கட்டிய பேழையின் நீள, அகல, உயர விகிதங்கள் நவீன காலத்தின் மாபெரும் சரக்குக் கப்பல்களுக்கு இணையான நிலைப்புத்தன்மை கொண்டது என கடல்சார் பொறியாளர்கள் ஆச்சரியப்படுகின்றனர். கொந்தளிக்கும் பெருவெள்ளத்திலும் கவிழாமல் இருக்கத் தேவையான துல்லியமான அளவுகளை தேவன் தாமே நோவாவுக்கு வெளிப்படுத்தியிருந்தார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic ancient wooden ark resting atop snowcapped mountain peaks under rainbow and breaking sun, 8k",
            "Cinematic 9:16 vertical detailed aerial view of giant timber hull enduring mountain crest under clearing sky, 8k"
        ],
        "engagement_question": "வேதாகமத்தின் இந்த அறிவியல் துல்லியம் உங்களுக்கு ஆச்சரியத்தை அளிக்கிறதா?"
    },
    {
        "category": "mystery",
        "topic_id": "dead_sea_scrolls_qumran_caves",
        "headline": "சாக்கடல் சுருள்கள்: இரண்டாயிரம் ஆண்டுகள் பாதுகாக்கப்பட்ட வேத வார்த்தைகள்!",
        "verse_reference": "ஏசாயா 40:8 (Isaiah 40:8)",
        "voiceover_script": "1947 ஆம் ஆண்டு கும்ரான் குகைகளில் கண்டெடுக்கப்பட்ட சாக்கடல் சுருள்கள், வேதாகமம் இரண்டாயிரத்திற்கும் மேற்பட்ட ஆண்டுகளாக எவ்வித மாற்றமும் இன்றி துல்லியமாகப் பாதுகாக்கப்பட்டு வந்துள்ளதை உலகிற்கு நிரூபித்தன. புல் உலர்ந்து பூ உதிரும், ஆனால் நம்முடைய தேவனுடைய வசனமோ என்றென்றைக்கும் நிலைநிற்கும் என்பதற்கு இது கண்கண்ட சான்றாகும்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical dramatic view of arid Qumran desert cliff caves under starry evening sky, historical documentary, 8k",
            "Cinematic 9:16 vertical close up of ancient parchment scroll fragments with Hebrew script in museum exhibition lighting, 8k"
        ],
        "engagement_question": "தேவ வார்த்தைகளின் இந்த அழியாத உண்மைத் தன்மை உங்களை வியப்பில் ஆழ்த்துகிறதா?"
    },
    {
        "category": "mystery",
        "topic_id": "mount_sinai_red_sea_crossing_miracle",
        "headline": "செங்கடல் பிளந்த அதிசயம்: இயற்கை விதிகளை மாற்றிய தேவ வல்லமை!",
        "verse_reference": "யாத்திராகமம் 14:21-22 (Exodus 14:21-22)",
        "voiceover_script": "முன்னே ஆழமான செங்கடல், பின்னே எகிப்தியப் படை என வழியே இல்லாத சூழலில், மோசே தன் கோலை நீட்டிய போது சமுத்திரம் இரண்டாகப் பிளந்து வழிவிட்டது. உங்கள் வாழ்க்கையிலும் முன்னே செல்ல வழியில்லை என்று நீங்கள் நினைக்கும் போது, தேவன் புதிய பாதையைத் திறக்க வல்லவராக இருக்கிறார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical epic dramatic rendering of towering walls of ocean water parted on both sides revealing dry seafloor, 8k",
            "Cinematic 9:16 vertical golden pillar of fire illuminating night sky over rocky desert mountains, majestic biblical realism, 8k"
        ],
        "engagement_question": "வழியில்லாத இடத்தில் வழியை உண்டாக்கும் தேவன் உங்களுடன் இருக்கிறார் என்பதை ஏற்பீர்களா?"
    },
    {
        "category": "mystery",
        "topic_id": "ark_of_covenant_acacia_gold_mystery",
        "headline": "உடன்படிக்கைப் பெட்டி: தூய பொன்னால் செய்யப்பட்ட தேவ பிரசன்னத்தின் சின்னம்!",
        "verse_reference": "யாத்திராகமம் 25:10-22 (Exodus 25:10-22)",
        "voiceover_script": "சீத்தீம் மரத்தினால் செய்யப்பட்டு உள்ளும் புறமும் பசும்பொன்னால் மூடப்பட்ட உடன்படிக்கைப் பெட்டியின் மேல், இரண்டு கேருபீன்கள் தங்கள் செட்டைகளை விரித்திருந்தன. அதன் நடுவே தேவன் பிரசன்னமாகி தம் மக்களோடு பேசினார். இன்று கிறிஸ்துவின் மூலமாக நாமே தேவனுடைய ஜீவனுள்ள ஆலயமாக விளங்குகிறோம் என்பது எத்தனை பெரிய பாக்கியம்!",
        "visual_prompts": [
            "Cinematic 9:16 vertical golden Ark of the Covenant with sculpted cherubim wings glowing under sacred heavenly light in tabernacle, 8k",
            "Cinematic 9:16 vertical close up of pure polished gold mercy seat adorned with divine radiance and smoke of incense, 8k"
        ],
        "engagement_question": "தேவனுடைய பிரசன்னம் உங்கள் வீட்டில் எப்போதும் இருக்க விரும்புகிறீர்களா?"
    },
    {
        "category": "mystery",
        "topic_id": "city_of_jerusalem_western_wall_history",
        "headline": "எருசலேம் நகரம்: மூவாயிரம் ஆண்டுகள் கடந்தும் நிலைக்கும் பரிசுத்த பூமி!",
        "verse_reference": "சங்கீதம் 122:6 (Psalm 122:6)",
        "voiceover_script": "தாவீது மன்னனால் தலைநகராக நிறுவப்பட்ட எருசலேம் நகரம், எண்ணற்ற போர்களையும் அழிவுகளையும் சந்தித்தும் இன்றும் உலகின் ஆன்மீக மையமாகத் திகழ்கிறது. எருசலேமின் சமாதானத்திற்காக வேண்டிக்கொள்ளுங்கள்; உன்னை நேசிக்கிறவர்கள் சுகித்திருப்பார்களாக என்று வேதம் கூறுகிறது. எருசலேமின் மீட்பர் சீக்கிரம் வருவார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical golden hour aerial view over ancient stone city of Jerusalem at sunset, olive trees and ancient walls, 8k",
            "Cinematic 9:16 vertical ancient massive limestone stones of the historic Western Wall glowing under warm dusk lamps, 8k"
        ],
        "engagement_question": "எருசலேமின் சமாதானத்திற்காகவும் உலக அமைதிக்காகவும் நாம் ஜெபிப்போம்!"
    },
    {
        "category": "mystery",
        "topic_id": "mount_carmel_elijah_fire_from_heaven",
        "headline": "கர்மேல் மலையில் இறங்கிய அக்கினி: ஜீவனுள்ள ஒரே மெய்த்தேவன்!",
        "verse_reference": "1 இராஜாக்கள் 18:38 (1 Kings 18:38)",
        "voiceover_script": "பாகாலின் நானூற்று ஐம்பது பொய் தீர்க்கதரிசிகளுக்கு முன்பாக எலியா தீர்க்கதரிசி தனியாளாக நின்றான். தண்ணீரை ஊற்றி நனைக்கப்பட்ட பலிபீடத்தின் மேல் எலியா ஜெபித்த போது, வானத்திலிருந்து தேவ அக்கினி இறங்கி பலியையும் தண்ணீரையும் சுட்டெரித்தது. கர்த்தரே தேவன், கர்த்தரே மெய்யான தேவன்!",
        "visual_prompts": [
            "Cinematic 9:16 vertical dramatic lightning and golden fire from dark thunderous sky falling onto simple stone altar on Mount Carmel, 8k",
            "Cinematic 9:16 vertical silhouette of prophet Elijah with outstretched arms against awe-inspiring heavenly lightning, 8k"
        ],
        "engagement_question": "ஜெபத்திற்கு அக்கினியாய் பதிலளிக்கும் தேவனை நீங்கள் விசுவாசிக்கிறீர்களா?"
    },
    {
        "category": "mystery",
        "topic_id": "solomons_temple_grand_architecture",
        "headline": "சாலொமோனின் ஆலயம்: உலகையே வியப்பில் ஆழ்த்திய மாபெரும் தேவ ஆலயம்!",
        "verse_reference": "1 இராஜாக்கள் 6:14-22 (1 Kings 6:14-22)",
        "voiceover_script": "லெபனோனின் கேதுரு மரங்கள், செதுக்கப்பட்ட வெண்கலத் தூண்கள் மற்றும் பசும்பொன் தகடுகளால் சாலொமோன் மன்னன் கட்டிய ஆலயம் பண்டைய உலகின் கட்டிடக்கலை விந்தையாகத் திகழ்ந்தது. ஆலயம் பிரதிஷ்டை செய்யப்பட்ட போது தேவ மகிமை மேகமாய் ஆலயத்தை நிரப்பியது. தேவனின் பிரசன்னமே எல்லாவற்றையும் விட மேன்மையானது.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic golden temple columns glowing in morning sunlight under clear blue sky, regal historical architecture, 8k",
            "Cinematic 9:16 vertical warm interior view of cedar wood carved reliefs covered in pure gold leaf, sacred atmosphere, 8k"
        ],
        "engagement_question": "தேவனின் பிரசன்னம் உங்கள் உள்ளத்திலும் இல்லத்திலும் தங்கட்டும், ஆமென்!"
    },

    # 5. NIGHT PRAYER (09:30 PM)
    {
        "category": "prayer",
        "topic_id": "psalm_91_he_that_dwelleth_secret_place",
        "headline": "உன்னதமானவரின் மறைவில் இருக்கிறவன் சர்வவல்லவருடைய நிழலில் தங்குவான்",
        "verse_reference": "சங்கீதம் 91:1-4 (Psalm 91:1-4)",
        "voiceover_script": "இந்த இரவு வேளையில் நீங்கள் படுக்கைக்குச் செல்லும்போது எவ்வித பயமும் இன்றி படுத்துக்கொள்ளுங்கள். அவர் தம்முடைய சிறகுகளாலே உங்களை மூடுவார், அவருடைய செட்டைகளின் கீழே நீங்கள் அடைக்கலம் புகுவீர்கள். இரவின் பயங்கரத்திற்கும், பகலில் பறக்கும் அம்புக்கும் நீங்கள் பயப்படமாட்டீர்கள். கர்த்தர் உங்கள் குடும்பத்திற்கு இனிமையான நித்திரையைத் தருவாராக.",
        "visual_prompts": [
            "Cinematic 9:16 vertical tranquil starry night sky with gentle silver moonbeams illuminating calm mountain valley, deep peaceful rest, 8k",
            "Cinematic 9:16 vertical warm glowing lantern beside open Bible in cozy room with window showing quiet starry night, 8k"
        ],
        "engagement_question": "இந்த இரவு ஜெபத்தை உங்கள் குடும்பத்தோடு சேர்ந்து ஆமென் என்று சொல்லி ஏற்றுக்கொள்ளுங்கள்!"
    },
    {
        "category": "prayer",
        "topic_id": "psalm_23_the_lord_is_my_shepherd",
        "headline": "கர்த்தர் என் மேய்ப்பராயிருக்கிறார்; நான் தாழ்ச்சியடையேன்",
        "verse_reference": "சங்கீதம் 23:1-3 (Psalm 23:1-3)",
        "voiceover_script": "அவர் உங்களைப் புல்லுள்ள இடங்களில் படுக்கப்பண்ணி, அமர்ந்த தண்ணீர்கள் அண்டையில் உங்களை வழிநடத்துகிறார். இந்த நாளில் உங்கள் மனதை அலைக்கழித்த குழப்பங்கள் அனைத்தும் நீங்கி, தேவனின் தெய்வீக சமாதானம் உங்கள் ஆத்துமாவைத் தேற்றட்டும். தூங்குவதற்கு முன் உங்கள் இதயத்தின் நன்றிகளை தேவனுக்குச் செலுத்துங்கள்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful moonlit stream winding softly through misty lush pastures under starlight, 8k fine art",
            "Cinematic 9:16 vertical gentle silhouetted cross on tranquil hill with radiant silver moonlight outlining the horizon, 8k"
        ],
        "engagement_question": "கர்த்தர் உங்கள் மேய்ப்பராய் இருக்கிறார் என்பதை முழுமையாக விசுவாசிக்கிறீர்களா?"
    },
    {
        "category": "prayer",
        "topic_id": "psalm_4_8_in_peace_i_will_sleep",
        "headline": "சமாதானத்தோடே படுத்துக்கொண்டு உடனே தூங்குவேன்; கர்த்தாவே, நீர் ஒருவரே என்னைச் சுகமாய்த் தங்கப்பண்ணுகிறீர்",
        "verse_reference": "சங்கீதம் 4:8 (Psalm 4:8)",
        "voiceover_script": "இன்றைய நாளின் வேலைகள் முடிந்துவிட்டன. எதைப் பற்றியும் யோசித்து தூக்கத்தை இழக்காதீர்கள். நாளைய தினத்தைக் குறித்து கர்த்தர் ஏற்கனவே திட்டமிட்டுள்ளார். உங்கள் மனபாரம், நோய்நொடிகள், சோர்வுகள் யாவற்றையும் தேவனிடம் கொடுத்துவிட்டு நிம்மதியாக உறங்குங்கள். அவர் உங்களுக்குப் புத்துணர்ச்சியூட்டுவார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful quiet lake reflecting twilight stars and crescent moon, calm soothing water, 8k",
            "Cinematic 9:16 vertical single warm candle burning gently beside Bible, peaceful shadow casting serene warmth, 8k"
        ],
        "engagement_question": "தேவனின் அமைதியை உங்கள் மனதில் உணர்ந்து நிம்மதியாய் தூங்குங்கள், ஆமென்!"
    },
    {
        "category": "prayer",
        "topic_id": "psalm_121_7_the_lord_shall_preserve_thee",
        "headline": "கர்த்தர் உன்னை எல்லாத் தீங்குக்கும் விலக்கிக் காப்பார்; அவர் உன் ஆத்துமாவைக் காப்பார்",
        "verse_reference": "சங்கீதம் 121:7-8 (Psalm 121:7-8)",
        "voiceover_script": "இந்த இரவு நேரத்தில் தேவ தூதர்களின் பாதுகாப்பு உங்கள் வீட்டையும் உங்கள் பிள்ளைகளையும் சூழ்ந்திருப்பதாக. எந்தத் தீங்கும் உங்கள் கூடாரத்தை அணுகாது. நீங்கள் உறங்கும் வேளையிலும் தேவனின் அன்பும் இரக்கமும் உங்களை அரவணைத்துக் கொண்டிருக்கும். நல்ல தூக்கமும் அமைதியும் உங்களுக்கு உண்டாவதாக.",
        "visual_prompts": [
            "Cinematic 9:16 vertical warm luminous cottage window glowing softly in quiet midnight forest under starry sky, 8k",
            "Cinematic 9:16 vertical majestic guardian angel wings formed by soft golden starlight in peaceful night sky, 8k"
        ],
        "engagement_question": "இந்த தெய்வீக பாதுகாப்பை நம்பி ஆமென் என்று சொல்லி உறங்குங்கள்!"
    },
    {
        "category": "prayer",
        "topic_id": "matthew_6_12_forgive_us_our_debts",
        "headline": "எங்கள் கடனாளிகளுக்கு நாங்கள் மன்னிக்கிறதுபோல எங்கள் கடன்களை எங்களுக்கு மன்னியும்",
        "verse_reference": "மத்தேயு 6:12 (Matthew 6:12)",
        "voiceover_script": "இன்றைய நாளில் யார் மீதாவது மனக்கசப்பு அல்லது கோபம் ஏற்பட்டிருந்தால், தூங்குவதற்கு முன்பே அதை முழுமையாக மன்னித்து விடுங்கள். சூரியன் அஸ்தமிக்கிறதற்கு முன் உங்கள் கோபம் தணியக்கடவது. உங்கள் இருதயத்தை லேசாக்கி தேவ மன்னிப்பைப் பெற்றுக்கொள்ளுங்கள். பரிசுத்த ஆவியானவர் உங்கள் உள்ளத்தை அமைதியாக்குவார்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene purple and gold twilight over calm ocean, waves gently kissing the shoreline, 8k",
            "Cinematic 9:16 vertical hands gently releasing floating paper lantern with warm light into midnight starry sky, 8k"
        ],
        "engagement_question": "மனதில் உள்ள கசப்புகளை இறக்கி வைத்துவிட்டு சமாதானத்தோடு உறங்குங்கள்!"
    },
    {
        "category": "prayer",
        "topic_id": "psalm_63_6_when_i_remember_thee_upon_my_bed",
        "headline": "என் படுக்கையின்மேல் நான் உம்மை நினைத்து, இராச்சாமங்களில் உம்மைத் தியானிக்கிறேன்",
        "verse_reference": "சங்கீதம் 63:6 (Psalm 63:6)",
        "voiceover_script": "இன்று கர்த்தர் உங்களுக்குச் செய்த நன்மைகளை ஒவ்வொன்றாக நினைத்துப் பார்த்து நன்றி சொல்லுங்கள். நீங்கள் விழித்திருந்த நேரமெல்லாம் உங்களை வழிநடத்திய தேவன், நீங்கள் உறங்கும் இந்த இரவிலும் உங்கள் ஆத்துமாவைப் பாதுகாப்பார். அவருடைய கிருபை காலையில்தோறும் புதிதாயிருக்கும்.",
        "visual_prompts": [
            "Cinematic 9:16 vertical calm starlit landscape with glowing Milky Way arching over tranquil hill chapel, 8k",
            "Cinematic 9:16 vertical serene close up of open Bible illuminated by soft bedside lamp, tranquil night, 8k"
        ],
        "engagement_question": "இன்றைய நாளுக்காக தேவனுக்கு மனதார நன்றி கூறி ஆமென் சொல்லுங்கள்!"
    },
    {
        "category": "prayer",
        "topic_id": "numbers_6_24_the_lord_bless_thee_keep_thee",
        "headline": "கர்த்தர் உன்னை ஆசீர்வதித்து, உன்னைக் காக்கக்கடவர்",
        "verse_reference": "எண்ணாகமம் 6:24-26 (Numbers 6:24-26)",
        "voiceover_script": "கர்த்தர் தம்முடைய முகத்தை உங்கள்மேல் பிரகாசிக்கப்பண்ணி, உங்கள்மேல் கிருபையாயிருக்கக்கடவர். கர்த்தர் தம்முடைய முகத்தை உங்கள்மேல் பிரசன்னமாக்கி, உங்களுக்கு சமாதானம் கட்டளையிடக்கடவர். இந்த ஆசீர்வாதம் உங்கள் வாழ்விலும், உங்கள் குடும்பத்திலும் என்றென்றைக்கும் தங்கி இருப்பதாக.",
        "visual_prompts": [
            "Cinematic 9:16 vertical divine radiant golden blessing light descending from starry heaven upon quiet sleeping earth, 8k",
            "Cinematic 9:16 vertical gentle silhouetted church cross beneath starry sky, serene peaceful evening atmosphere, 8k"
        ],
        "engagement_question": "இந்த ஆசாரிய ஆசீர்வாதத்தை முழு விசுவாசத்தோடு ஆமென் என்று ஏற்றுக்கொள்ளுங்கள்!"
    }
]

def load_christian_state():
    if os.path.exists(CHRISTIAN_STATE_FILE):
        try:
            with open(CHRISTIAN_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"used_topics": [], "last_category_index": -1}

def save_christian_state(state):
    try:
        with open(CHRISTIAN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save Christian state: {e}")

def get_used_christian_identifiers():
    used = set()
    state = load_christian_state()
    for t in state.get("used_topics", []):
        used.add(str(t).strip().lower())

    if os.path.exists(CHRISTIAN_HISTORY_FILE):
        try:
            with open(CHRISTIAN_HISTORY_FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
                if isinstance(hist, list):
                    for item in hist:
                        if item.get("headline"):
                            clean_h = re.sub(r'[\W_]+', '', item["headline"].strip().lower())
                            if clean_h:
                                used.add(clean_h)
        except Exception:
            pass
    return used

def get_category_by_id(cat_id):
    for c in CHRISTIAN_CATEGORIES:
        if c["id"] == cat_id:
            return c
    return CHRISTIAN_CATEGORIES[0]

def get_scheduled_category_for_now():
    """
    Selects the appropriate Christian devotional category based on current local time:
    - 04:00 - 09:59 -> 'promise' (Morning Promise, 06:00 AM slot)
    - 10:00 - 14:29 -> 'wisdom'  (Biblical Wisdom, 12:30 PM slot)
    - 14:30 - 18:29 -> 'parable' (Faith Parable, 04:30 PM slot)
    - 18:30 - 20:59 -> 'mystery' (Bible History/Facts, 07:30 PM slot)
    - 21:00 - 03:59 -> 'prayer'  (Night Prayer, 09:30 PM slot)
    """
    hour = time.localtime().tm_hour
    minute = time.localtime().tm_min
    time_float = hour + (minute / 60.0)

    if 4.0 <= time_float < 10.0:
        return get_category_by_id("promise")
    elif 10.0 <= time_float < 14.5:
        return get_category_by_id("wisdom")
    elif 14.5 <= time_float < 18.5:
        return get_category_by_id("parable")
    elif 18.5 <= time_float < 21.0:
        return get_category_by_id("mystery")
    else:
        return get_category_by_id("prayer")

def generate_christian_story_with_gemini(category_info, used_topics):
    """
    Generates a fresh, spirit-filled Tamil devotional Reel using Google Gemini:
    - Dedicated to 'Jesus Hears You'
    - NO mentions of 'AI'
    - NO '24/7 daily'
    - NO greetings like 'வணக்கம்'
    - Captivating biblical promise/story and peaceful ending
    """
    if not GEMINI_API_KEY:
        return None

    cat_id = category_info["id"]
    cat_desc = category_info["theme_desc"]

    prompt = f"""
You are a loving Tamil Christian pastor, gospel storyteller, and devotional scriptwriter for the page "Jesus Hears You".
Create a deeply moving, faith-strengthening, and uplifting 30-40 second devotional Reel in Tamil.

CATEGORY: {category_info['name']} ({cat_id})
THEME: {cat_desc}

DO NOT repeat any of these recently used topics/verses:
{json.dumps(used_topics[-25:], ensure_ascii=False)}

CRITICAL INSTRUCTIONS:
1. "headline": A powerful, uplifting scripture promise or message in pure Tamil (8-12 words max).
2. "verse_reference": The exact Bible book, chapter and verse (e.g. "யோசுவா 1:5 (Joshua 1:5)").
3. "voiceover_script": A deeply comforting, inspiring narration in spoken Tamil (~40-60 words, ~25-30 seconds of speech).
   - Hook the listener with God's unfailing love in the VERY FIRST sentence.
   - Speak with warmth, assurance, and divine peace.
   - ABSOLUTELY NO greetings (NO "வணக்கம்", NO "இன்றைய").
   - NEVER mention the word "AI" anywhere!
   - NEVER mention "24/7 daily" anywhere!
   - NO aggressive outro CTAs. End with a heartfelt blessing or promise.
   - CRITICAL TRANSLITERATION: Transliterate any English/Hebrew proper names into phonetic Tamil script (e.g. "ஜீசஸ்", "ஜோசுவா", "ஜெருசலேம்").
4. "visual_prompts": A list of 2 distinct, complementary English visual prompts for high-resolution photorealistic imagery.
   - e.g. "Cinematic 9:16 vertical view of golden sunlight breaking through heavenly clouds over tranquil ocean, 8k"
   - e.g. "Cinematic 9:16 vertical close up of open Holy Bible glowing with soft divine light, 8k"
   - NO text, NO watermarks in the prompts.
5. "engagement_question": A thoughtful faith-filled question in Tamil (e.g. "இந்த வாக்குத்தத்தத்தை விசுவாசித்து ஆமென் சொல்லுங்கள்!").
6. "topic_id": A short unique English slug (e.g. "psalm_23_shepherd_peace").

Return ONLY valid JSON matching this schema:
{{
  "headline": "...",
  "verse_reference": "...",
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
                    "temperature": 0.80,
                    "responseMimeType": "application/json"
                }
            }
            resp = _session.post(url, json=payload, timeout=18)
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
                print(f"Gemini {model_name} rate limited (429), trying fallback model...")
                continue
        except Exception as e:
            print(f"Notice: Gemini Christian generation notice ({model_name}): {e}")
            continue

    return None

def get_christian_story(category_id=None):
    """
    Retrieves the next devotional story for 'Jesus Hears You':
    - If category_id is specified (e.g. 'promise', 'prayer'), uses that.
    - Otherwise, auto-selects based on current clock time.
    - Attempts Gemini generation with multi-model failover.
    - Falls back to 35+ curated rich devotional bank with strict non-repeating memory.
    """
    category = get_category_by_id(category_id) if category_id else get_scheduled_category_for_now()
    used_identifiers = get_used_christian_identifiers()

    # 1. Try Gemini generation first
    story_data = generate_christian_story_with_gemini(category, list(used_identifiers))
    if story_data:
        topic_id = story_data.get("topic_id") or f"{category['id']}_{int(time.time())}"
        story_data["category_id"] = category["id"]
        story_data["category_info"] = category
        script = transliterate_english_to_tamil(story_data.get("voiceover_script", "") or story_data.get("tamil_script", ""))
        story_data["voiceover_script"] = script
        story_data["tamil_script"] = script

        current_state = load_christian_state()
        current_state["used_topics"].append(topic_id)
        if len(current_state["used_topics"]) > 300:
            current_state["used_topics"] = current_state["used_topics"][-300:]
        save_christian_state(current_state)
        return story_data

    # 2. Curated library fallback
    available = []
    for item in CURATED_CHRISTIAN_BANK:
        t_id = item["topic_id"].strip().lower()
        clean_h = re.sub(r'[\W_]+', '', item["headline"].strip().lower())
        if t_id not in used_identifiers and clean_h not in used_identifiers:
            available.append(item)

    if not available:
        # Recycle older topics if all exhausted
        current_state = load_christian_state()
        current_state["used_topics"] = current_state.get("used_topics", [])[-10:]
        save_christian_state(current_state)
        used_identifiers = get_used_christian_identifiers()
        available = [item for item in CURATED_CHRISTIAN_BANK if item["topic_id"].strip().lower() not in used_identifiers]
        if not available:
            available = CURATED_CHRISTIAN_BANK

    cat_matches = [item for item in available if item["category"] == category["id"]]
    pool = cat_matches if cat_matches else available
    chosen = dict(random.choice(pool))

    cat_match = next((c for c in CHRISTIAN_CATEGORIES if c["id"] == chosen["category"]), category)
    chosen["category_id"] = chosen["category"]
    chosen["category_info"] = cat_match
    script = transliterate_english_to_tamil(chosen.get("voiceover_script", "") or chosen.get("tamil_script", ""))
    chosen["voiceover_script"] = script
    chosen["tamil_script"] = script

    current_state = load_christian_state()
    current_state["used_topics"].append(chosen["topic_id"])
    save_christian_state(current_state)
    return chosen

# Aliases for pipeline compatibility
get_scheduled_christian_category = get_scheduled_category_for_now
generate_christian_story = get_christian_story


def fetch_christian_visual(visual_prompt, category_id="promise", suffix=""):
    """
    Downloads or renders a 9:16 vertical image for the Christian devotional reel:
    1. Tries Pollinations Flux AI generator (1080x1920) with prompt.
    2. Fallback to serene, divine high-resolution category images.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_filename = f"christian_visual_{int(time.time())}{suffix}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    temp_raw = os.path.join(OUTPUT_DIR, f"temp_cv_{int(time.time())}{suffix}.jpg")

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
                    print(f"🎨 Successfully generated Divine Visual for: {clean_p[:40]}...")
                    return out_path
        except Exception as e:
            print(f"Notice: Pollinations Christian visual notice: {e}")

    # 2. High-Quality Divine Unsplash Fallback
    category_fallbacks = {
        "promise": "https://images.unsplash.com/photo-1509021436665-8f07dbf5bf1d?w=1080&h=1920&fit=crop&q=85", # Divine sunbeams through clouds
        "wisdom": "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=1080&h=1920&fit=crop&q=85",  # Peaceful olive trees & light
        "parable": "https://images.unsplash.com/photo-1470240731273-7821a6eeb6bd?w=1080&h=1920&fit=crop&q=85", # Sunlit green pastures & mountains
        "mystery": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1080&h=1920&fit=crop&q=85", # Ancient earth & heavens
        "prayer": "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1080&h=1920&fit=crop&q=85"   # Peaceful sunset rays & starlight
    }
    fb_url = category_fallbacks.get(category_id, category_fallbacks["promise"])
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
        print(f"Notice: Divine category fallback visual notice: {e}")

    return None

def fetch_christian_visuals(visual_prompts, category_id="promise"):
    """
    Downloads or renders MULTIPLE 9:16 vertical images for a Christian reel
    so the video dynamically transitions through multiple peaceful scenes with Ken Burns zoom.
    """
    if not isinstance(visual_prompts, (list, tuple)):
        visual_prompts = [visual_prompts] if visual_prompts else []

    visual_paths = []
    for idx, prompt_text in enumerate(visual_prompts[:2]):
        vp = fetch_christian_visual(prompt_text, category_id, suffix=f"_{idx}")
        if vp and os.path.exists(vp):
            visual_paths.append(vp)

    if not visual_paths:
        fb = fetch_christian_visual(None, category_id, suffix="_fb")
        if fb:
            visual_paths.append(fb)

    return visual_paths
