import os
import json
import time
import random
import re
from urllib.parse import quote
import requests
from PIL import Image
from config import GEMINI_API_KEY, OUTPUT_DIR, CHRISTIAN_STATE_FILE, CHRISTIAN_HISTORY_FILE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

_session = requests.Session()
_session.headers.update(HEADERS)

CHRISTIAN_CATEGORIES = [
    {
        "id": "promise",
        "name": "Morning Promise & Grace",
        "badge_tag": "🌅 MORNING PROMISE",
        "time_slot": "06:00 AM",
        "theme_desc": "Morning promise of God, protection, grace, blessing for the day, overcoming fear, standing firm in faith (e.g. Joshua 1:5, Isaiah 41:10, Jeremiah 29:11, Psalm 121).",
        "hashtags": "#JesusHearsYou #MorningPromise #DailyBibleVerse #GodIsGood #FaithOverFear #ChristianReels #Jesus #Faith #DailyDevotional #Blessings #Reels"
    },
    {
        "id": "wisdom",
        "name": "Biblical Wisdom & Guidance",
        "badge_tag": "📖 BIBLICAL WISDOM",
        "time_slot": "12:30 PM",
        "theme_desc": "Practical Biblical wisdom from Proverbs, Psalms, and teachings of Jesus for daily life, patience, gentle speech, family peace, overcoming anxiety.",
        "hashtags": "#JesusHearsYou #BiblicalWisdom #Proverbs #DailyGuidance #InnerPeace #ChristianInspiration #BibleStudy #Wisdom #Faith #Reels"
    },
    {
        "id": "parable",
        "name": "Faith Story & Gospel Parable",
        "badge_tag": "✨ FAITH PARABLE",
        "time_slot": "04:30 PM",
        "theme_desc": "One-minute inspiring Gospel parables (The Lost Sheep, Good Samaritan, Mustard Seed, Prodigal Son) or moving Christian testimonies of God's miraculous help.",
        "hashtags": "#JesusHearsYou #FaithStory #GospelParable #ChristianStories #Grace #JesusLovesYou #Hope #Testimony #Motivation #Reels"
    },
    {
        "id": "mystery",
        "name": "Bible Wonders & History",
        "badge_tag": "🔍 BIBLE WONDERS",
        "time_slot": "07:30 PM",
        "theme_desc": "Fascinating Biblical history, archaeological discoveries (Noah's Ark, Dead Sea Scrolls, Red Sea crossing, ancient Jerusalem, Apostles' footprints).",
        "hashtags": "#JesusHearsYou #BibleFacts #BiblicalHistory #Archaeology #BibleWonders #ChristianHistory #FaithAndScience #Reels"
    },
    {
        "id": "prayer",
        "name": "Night Prayer & Peace",
        "badge_tag": "🕊️ BEDTIME PRAYER",
        "time_slot": "09:30 PM",
        "theme_desc": "Peaceful bedtime prayer, releasing worry and anxiety to Jesus, Psalm 91 and Psalm 23 reflections, blessing for restful sleep and family protection.",
        "hashtags": "#JesusHearsYou #BedtimePrayer #NightPrayer #Psalm91 #PeacefulSleep #RestInGod #SurrenderToJesus #EveningBlessing #Reels"
    }
]

# Rich Curated Devotional Fallback Bank (7 topics per category = 35 topics in English)
CURATED_CHRISTIAN_BANK = [
    # 1. MORNING PROMISE (06:00 AM)
    {
        "category": "promise",
        "topic_id": "joshua_1_5_never_leave_you",
        "headline": "I will never leave you nor forsake you",
        "verse_reference": "Joshua 1:5",
        "voiceover_script": "Whatever mountain stands before you this morning, do not be afraid. People may walk away, but the Lord Almighty promises to never leave you nor forsake you. Place your worries in His hands, take a deep breath, and walk forward in faith. He is fighting your battles today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical view of golden sunrise rays breaking through heavenly clouds over majestic peaceful mountain vista, 8k documentary style",
            "Cinematic 9:16 vertical close up of an open Holy Bible with soft golden morning sunlight illuminating the pages, reverent aesthetic, 8k"
        ],
        "engagement_question": "Type AMEN if you trust God's promises today! 🙏"
    },
    {
        "category": "promise",
        "topic_id": "isaiah_41_10_fear_not_i_am_with_you",
        "headline": "Fear not, for I am with you; do not be dismayed",
        "verse_reference": "Isaiah 41:10",
        "voiceover_script": "Release every heavy thought and anxious fear into God's caring hands right now. He promises to strengthen you, help you, and uphold you with His righteous right hand. When you feel weak, His divine grace is made perfect in you. Be strong, for the Lord is on your side.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouette of a person standing atop a hill gazing at a radiant heavenly sunrise, peaceful breeze, 8k fine art",
            "Cinematic 9:16 vertical macro shot of warm golden light beams falling upon praying hands held peacefully, high resolution 8k"
        ],
        "engagement_question": "Do you believe God is with you right now? Say AMEN! ✨"
    },
    {
        "category": "promise",
        "topic_id": "jeremiah_29_11_plans_to_prosper_you",
        "headline": "For I know the plans I have for you, plans to give you hope",
        "verse_reference": "Jeremiah 29:11",
        "voiceover_script": "Never lose hope about your future. God has declared that His plans for your life are plans of peace and not of harm, to give you an expected end filled with hope. Even when doors close, trust that God is preparing an open heaven for you. His timing is always perfect.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene path winding through tranquil sunlit olive groves towards a glowing horizon, warm gold light, 8k",
            "Cinematic 9:16 vertical view looking up at soaring white dove flying through sunlit morning clouds, heavenly blue sky, 8k"
        ],
        "engagement_question": "Claim this promise in Jesus' name and share it with a friend! 🕊️"
    },
    {
        "category": "promise",
        "topic_id": "philippians_4_13_christ_strengthens_me",
        "headline": "I can do all things through Christ who gives me strength",
        "verse_reference": "Philippians 4:13",
        "voiceover_script": "Do not depend on your own limited strength today. When you rely on Christ living within you, there is no storm you cannot weather and no obstacle you cannot overcome. Step into this day knowing you are crowned with divine favor and supernatural strength.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic view of granite mountain peaks bathed in golden morning sunbeams, eternal steadfastness, 8k",
            "Cinematic 9:16 vertical glowing warm cross standing steadfastly on green hill against dawn horizon, 8k documentary"
        ],
        "engagement_question": "Type AMEN to receive His divine strength today! 💪"
    },
    {
        "category": "promise",
        "topic_id": "matthew_11_28_come_unto_me_rest",
        "headline": "Come to Me, all you who are weary, and I will give you rest",
        "verse_reference": "Matthew 11:28",
        "voiceover_script": "Are you feeling overwhelmed by the pressures of life? Jesus extends an open invitation to your soul today: Come unto Me, and I will give you rest. Lay down your burdens at the foot of the cross and let His gentle love fill your heart with everlasting peace.",
        "visual_prompts": [
            "Cinematic 9:16 vertical tranquil lake with crystal clear reflections of snowcapped peaks at dawn, divine peace atmosphere, 8k",
            "Cinematic 9:16 vertical close up of gentle warm light enveloping praying hands, peaceful serenity, 8k"
        ],
        "engagement_question": "Surrender your heavy burdens to Jesus today. Amen? 🙏"
    },
    {
        "category": "promise",
        "topic_id": "psalm_121_my_help_comes_from_the_lord",
        "headline": "My help comes from the Lord, the Maker of heaven and earth",
        "verse_reference": "Psalm 121:2",
        "voiceover_script": "Lift your eyes above your current circumstances. The God who spoke the stars into existence and formed the oceans is watching over your every step. He who keeps you will not slumber. May His divine protection surround you and your loved ones throughout this day.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic mountain peak under brilliant celestial blue sky with golden sunlight, 8k",
            "Cinematic 9:16 vertical soft sunbeams illuminating green pasture with gentle peaceful stream, 8k"
        ],
        "engagement_question": "Declare: My help comes from the Lord! Amen! ✝️"
    },
    {
        "category": "promise",
        "topic_id": "romans_8_28_all_things_work_together",
        "headline": "All things work together for good to those who love God",
        "verse_reference": "Romans 8:28",
        "voiceover_script": "Even the painful setbacks and unexpected delays are working for your ultimate blessing. God is a master weaver who turns sorrow into joy and tests into testimonies. Trust His loving hand, for He is turning every single thing around for your good.",
        "visual_prompts": [
            "Cinematic 9:16 vertical sunrise over tranquil misty meadow with wildflowers glowing in morning golden hour, 8k",
            "Cinematic 9:16 vertical silhouette of praying hands lifted in worship against breathtaking dawn sky, 8k"
        ],
        "engagement_question": "Do you trust God's plan for your life? Type AMEN! ❤️"
    },

    # 2. BIBLICAL WISDOM (12:30 PM)
    {
        "category": "wisdom",
        "topic_id": "proverbs_15_1_gentle_answer_turns_away_wrath",
        "headline": "A gentle answer turns away wrath, but a harsh word stirs up anger",
        "verse_reference": "Proverbs 15:1",
        "voiceover_script": "In a world filled with arguments and tension, let your words be seasoned with grace and love. A soft, patient response disarms anger and brings healing to hurting hearts. Today, choose to speak words that build up your family and bring peace into your home.",
        "visual_prompts": [
            "Cinematic 9:16 vertical tranquil calm water mirror reflecting gentle blue sky, absolute stillness and peace, 8k",
            "Cinematic 9:16 vertical fresh green olive branch with gentle white blossoms in soft morning sunlight, 8k"
        ],
        "engagement_question": "Will you choose gentle, loving words today? Say Amen! 🌿"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_3_5_trust_in_the_lord_with_all_your_heart",
        "headline": "Trust in the Lord with all your heart and lean not on your own understanding",
        "verse_reference": "Proverbs 3:5-6",
        "voiceover_script": "When life feels confusing and the path ahead seems unclear, remember you don't have to figure it all out alone. Acknowledge God in all your ways, surrender your need to control, and He will make your paths straight and direct your footsteps with divine wisdom.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene forest pathway glowing with warm sunbeams breaking through canopy, 8k",
            "Cinematic 9:16 vertical close up of a lighthouse shining bright beam through gentle coastal mist, 8k"
        ],
        "engagement_question": "Trust God wholeheartedly today. Type AMEN! 📖"
    },
    {
        "category": "wisdom",
        "topic_id": "james_1_5_ask_god_for_wisdom",
        "headline": "If any of you lacks wisdom, let him ask God, who gives generously",
        "verse_reference": "James 1:5",
        "voiceover_script": "Facing tough decisions in your career, finances, or family? Heavenly wisdom is only a prayer away. God never mocks your questions; He promises to give generously to all who ask in faith. Quiet your heart and ask Him to guide your choices today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical celestial library with ancient golden scrolls illuminated by divine light from high window, 8k",
            "Cinematic 9:16 vertical person walking beside peaceful mountain stream in deep prayer, soft afternoon light, 8k"
        ],
        "engagement_question": "Ask God for wisdom and direction today. Amen! 🕊️"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_4_23_guard_your_heart",
        "headline": "Above all else, guard your heart, for everything you do flows from it",
        "verse_reference": "Proverbs 4:23",
        "voiceover_script": "Protect what enters your eyes, ears, and thoughts today. Guard your heart against bitterness, jealousy, and fear. Fill your spirit with the living water of God's Word, forgiveness, and gratitude. A pure heart produces a life overflowing with joy and divine fruit.",
        "visual_prompts": [
            "Cinematic 9:16 vertical pure crystal clear mountain spring bubbling through polished stones, sunlight refraction, 8k",
            "Cinematic 9:16 vertical lush green garden blooming with radiant white lilies under golden sun, 8k"
        ],
        "engagement_question": "Keep your heart pure and full of praise today. Type AMEN! 💖"
    },
    {
        "category": "wisdom",
        "topic_id": "colossians_3_13_forgive_as_the_lord_forgave",
        "headline": "Forgive as the Lord forgave you, bearing with each other in love",
        "verse_reference": "Colossians 3:13",
        "voiceover_script": "Holding onto resentment is like drinking poison and hoping the other person suffers. Forgiveness does not excuse the wrongdoing; it sets your soul free. As Christ has forgiven you so richly, release the offense today and walk in total emotional freedom.",
        "visual_prompts": [
            "Cinematic 9:16 vertical white dove being released from cupped hands into endless blue sky, freedom and peace, 8k",
            "Cinematic 9:16 vertical warm golden sunset over quiet sea, calm waves gently lapping shore, 8k"
        ],
        "engagement_question": "Choose forgiveness and freedom today. Amen! 🕊️"
    },
    {
        "category": "wisdom",
        "topic_id": "philippians_4_6_do_not_be_anxious",
        "headline": "Do not be anxious about anything, but in every situation, pray",
        "verse_reference": "Philippians 4:6-7",
        "voiceover_script": "Turn every worry into a prayer today. Instead of losing sleep over what you cannot change, present your requests to God with thanksgiving. And the peace of God, which surpasses all human understanding, will guard your heart and mind in Christ Jesus.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful field of lavender swaying in gentle afternoon breeze under soft sky, 8k",
            "Cinematic 9:16 vertical open Bible resting on wooden rustic table next to glowing warm candle, 8k"
        ],
        "engagement_question": "Trade your worries for God's peace right now. Type AMEN! ✨"
    },
    {
        "category": "wisdom",
        "topic_id": "galatians_6_9_do_not_grow_weary",
        "headline": "Let us not become weary in doing good, for in due season we will reap",
        "verse_reference": "Galatians 6:9",
        "voiceover_script": "Have you been praying, giving, and doing good without seeing any results? Don't give up just before the breakthrough. The seed you planted is taking root in secret. In God's appointed season, you will reap an abundant harvest if you do not lose heart.",
        "visual_prompts": [
            "Cinematic 9:16 vertical vast golden wheat field ready for harvest under brilliant blue sky, warm sunlight, 8k",
            "Cinematic 9:16 vertical small green seedling sprouting bravely through rich soil into bright sunlight, 8k"
        ],
        "engagement_question": "Your harvest is coming! Type AMEN to claim it! 🌾"
    },

    # 3. FAITH STORY & GOSPEL PARABLE (04:30 PM)
    {
        "category": "parable",
        "topic_id": "parable_lost_sheep_ninety_nine",
        "headline": "The Good Shepherd leaves the ninety-nine to rescue the one",
        "verse_reference": "Luke 15:4-7",
        "voiceover_script": "Even if ninety-nine sheep are safe in the fold, the Good Shepherd leaves everything to search for the one that is lost and hurting. You are never too broken or too far gone for His grace. Jesus knows your name, He is seeking you right now, and He will carry you safely home.",
        "visual_prompts": [
            "Cinematic 9:16 vertical gentle Shepherd holding a rescued lamb in loving arms on a sunlit hillside, 8k fine art",
            "Cinematic 9:16 vertical green rolling pasture with peaceful flock of sheep grazing near still waters, 8k"
        ],
        "engagement_question": "Thank Jesus for His relentless love! Type AMEN! 🐑"
    },
    {
        "category": "parable",
        "topic_id": "parable_prodigal_son_fathers_arms",
        "headline": "The Father ran to embrace his son with tears of joy",
        "verse_reference": "Luke 15:20-24",
        "voiceover_script": "When the prodigal son decided to return home, his father didn't wait with anger or judgment. He ran toward him, fell on his neck, and kissed him. No matter where you have wandered or what mistakes you have made, God's arms are wide open to welcome you home today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical emotional reunion of father embracing son on sunlit dusty path, golden sunset glow, 8k",
            "Cinematic 9:16 vertical open doorway of ancient welcoming home glowing with warm festive light inside, 8k"
        ],
        "engagement_question": "God's mercy is greater than your past! Amen! ❤️"
    },
    {
        "category": "parable",
        "topic_id": "parable_good_samaritan_mercy",
        "headline": "Go and do likewise: Loving our neighbor with compassion",
        "verse_reference": "Luke 10:33-37",
        "voiceover_script": "While others passed by the wounded man on the Jericho road, the Samaritan stopped, bandaged his wounds, and showed unconditional mercy. True religion is seeing someone hurting and choosing to be God's hands and feet. Let your love shine brightly today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone road winding through desert canyon with warm afternoon sun, 8k",
            "Cinematic 9:16 vertical hands gently pouring soothing oil and wine onto a wound, compassionate care, 8k"
        ],
        "engagement_question": "Who can you bless with kindness today? Amen! 🌟"
    },
    {
        "category": "parable",
        "topic_id": "parable_mustard_seed_faith_moves_mountains",
        "headline": "Faith as small as a mustard seed can move mountains",
        "verse_reference": "Matthew 17:20",
        "voiceover_script": "You don't need giant, perfect faith to experience God's power. Even faith as tiny as a mustard seed in the hands of a big God can shatter sickness, open locked doors, and move impossible mountains. Put your small seed of trust in Jesus today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical macro view of tiny mustard seed resting on palm of hand with majestic mountain in background, 8k",
            "Cinematic 9:16 vertical lush sprawling mustard tree full of birds resting in its branches under golden sky, 8k"
        ],
        "engagement_question": "Do you believe God can move your mountain? Type AMEN! 🏔️"
    },
    {
        "category": "parable",
        "topic_id": "parable_house_on_the_rock",
        "headline": "The rain fell and the winds blew, but the house stood firm upon the Rock",
        "verse_reference": "Matthew 7:24-25",
        "voiceover_script": "Storms will come to every life, but the house built upon the solid rock of Christ's teachings never collapses. When you build your family, career, and dreams on the eternal foundation of Jesus, no flood of trouble can ever wash you away.",
        "visual_prompts": [
            "Cinematic 9:16 vertical sturdy stone house built high atop solid seaside cliff withstanding crashing waves, 8k",
            "Cinematic 9:16 vertical glowing warm cross standing unshakeable on immovable granite rock, 8k"
        ],
        "engagement_question": "Is Jesus the rock of your life? Declare AMEN! 🪨"
    },
    {
        "category": "parable",
        "topic_id": "story_calming_the_storm_peace_be_still",
        "headline": "Jesus stood and rebuked the winds: Peace, be still!",
        "verse_reference": "Mark 4:39",
        "voiceover_script": "When ferocious waves battered the disciples' boat, Jesus simply stood up and spoke: Peace, be still. And immediately the storm ceased. Jesus is in your boat today. Whatever turbulent storm is raging around your life, listen to His calm voice whispering peace into your soul.",
        "visual_prompts": [
            "Cinematic 9:16 vertical stormy dark sea suddenly parting for a beam of brilliant golden heavenly light, 8k",
            "Cinematic 9:16 vertical tranquil sea of Galilee at calm sunset, mirror-like water reflecting evening stars, 8k"
        ],
        "engagement_question": "Invite Jesus to calm your storm. Type AMEN! 🌊"
    },
    {
        "category": "parable",
        "topic_id": "parable_pearl_of_great_price",
        "headline": "The kingdom of heaven is like a merchant seeking beautiful pearls",
        "verse_reference": "Matthew 13:45-46",
        "voiceover_script": "When a merchant found one priceless pearl, he joyfully sold everything he had to obtain it. Knowing Jesus, receiving His salvation, and walking in His kingdom is the greatest treasure this universe could ever offer. You are richly blessed in Him.",
        "visual_prompts": [
            "Cinematic 9:16 vertical radiant glowing pearl resting on velvet cloth inside antique ornate box, divine brilliance, 8k",
            "Cinematic 9:16 vertical sunbeams streaming through stained glass window in historic cathedral, 8k"
        ],
        "engagement_question": "Jesus is my greatest treasure! Type AMEN! 💎"
    },

    # 4. BIBLE WONDERS & HISTORY (07:30 PM)
    {
        "category": "mystery",
        "topic_id": "mystery_noahs_ark_mount_ararat",
        "headline": "Noah's Ark rested upon the mountains of Ararat: God remembers His covenant",
        "verse_reference": "Genesis 8:4",
        "voiceover_script": "Centuries before modern naval engineering, God gave Noah the exact dimensions for an ark with a stable three-hundred cubit ratio. Just as the ark safely carried Noah's family through catastrophic floods, Jesus is our eternal ark of safety through every judgment.",
        "visual_prompts": [
            "Cinematic 9:16 vertical massive ancient wooden ark resting on majestic snowcapped mountain peak under rainbow, 8k",
            "Cinematic 9:16 vertical glorious full rainbow stretching across dramatic misty sky over ancient valley, 8k"
        ],
        "engagement_question": "Praise God for His faithfulness through every generation! Amen! 🚢"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_red_sea_crossing_chariots",
        "headline": "The waters were divided, and the children of Israel walked on dry ground",
        "verse_reference": "Exodus 14:21-22",
        "voiceover_script": "When Pharaoh's army trapped Israel against the roaring sea, God parted the deep waters and created a highway through the impossible. Modern ocean discoveries at the Gulf of Aqaba still echo this miraculous deliverance. Where there seems to be no way, God makes a way.",
        "visual_prompts": [
            "Cinematic 9:16 vertical towering walls of parted sea water with dry seabed pathway illuminated by divine pillar of fire, 8k",
            "Cinematic 9:16 vertical golden desert coastline meeting deep azure sea at dramatic sunset, 8k"
        ],
        "engagement_question": "God can make a way where there is no way! Amen! 🌊"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_dead_sea_scrolls_qumran",
        "headline": "The grass withers, the flower fades, but the Word of our God stands forever",
        "verse_reference": "Isaiah 40:8",
        "voiceover_script": "In 1947, Bedouin shepherds discovered ancient jars hidden in Qumran caves containing biblical manuscripts over two thousand years old. Amazingly, the text matched our modern Bibles almost word for word. God has preserved His holy Word throughout all ages for you.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient clay jars holding papyrus scrolls inside sunlit desert cave in Qumran, 8k",
            "Cinematic 9:16 vertical aged Hebrew parchment scroll showing ancient script illuminated by soft warm light, 8k"
        ],
        "engagement_question": "God's Word never fails! Type AMEN if you stand on it! 📜"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_empty_tomb_garden_tomb",
        "headline": "He is not here; He has risen, just as He said!",
        "verse_reference": "Matthew 28:6",
        "voiceover_script": "In Jerusalem stands a first-century garden tomb that bears the greatest archaeological fact in human history: it is empty! Roman guards and heavy stones could not hold the Prince of Life. Because Jesus rose from the dead, you too have living hope and eternal victory.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone garden tomb with stone rolled away, brilliant morning light streaming from within, 8k",
            "Cinematic 9:16 vertical serene peaceful olive garden at sunrise with flowering branches and stone pathway, 8k"
        ],
        "engagement_question": "Jesus is alive! Hallelujah! Type AMEN! ✝️"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_mount_sinai_split_rock",
        "headline": "He split the rocks in the wilderness and gave them water in abundance",
        "verse_reference": "Psalm 78:15",
        "voiceover_script": "In the barren wilderness of Horeb stands a massive split rock showing deep water erosion from ancient springs. When God's people were dying of thirst, living water gushed from the stone. Today, Christ is your spiritual rock who quenches your deepest soul-thirst.",
        "visual_prompts": [
            "Cinematic 9:16 vertical towering monumental split boulder in desert landscape showing smooth water erosion path, 8k",
            "Cinematic 9:16 vertical fresh cold spring water pouring forth from natural stone cliff in desert oasis, 8k"
        ],
        "engagement_question": "Drink from His living water today. Type AMEN! 💧"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_walls_of_jericho_fallen",
        "headline": "When the people shouted with a great shout, the wall fell down flat",
        "verse_reference": "Joshua 6:20",
        "voiceover_script": "Ancient excavations at Jericho reveal massive double city walls that collapsed outward, forming ramps exactly as the Book of Joshua records. Faith and praise shattered impenetrable fortresses without a single weapon. Keep praising God, and your Jericho walls will crumble.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone excavation ramparts under dramatic desert twilight sky, 8k documentary",
            "Cinematic 9:16 vertical silver trumpet and ram's horn shofar resting beside ancient stone altar, warm light, 8k"
        ],
        "engagement_question": "Your praise has the power to bring down walls! Amen! 🎺"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_pool_of_siloam_restored",
        "headline": "Go, wash in the pool of Siloam: The blind man went and returned seeing",
        "verse_reference": "John 9:7",
        "voiceover_script": "Archaeologists in the City of David uncovered the authentic ancient stone steps of the Pool of Siloam, confirming the very site where Jesus healed a man born blind. What seemed biologically impossible was healed by a single touch from Christ. He still heals today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone stepped pool filled with clear shimmering water in historic Jerusalem, 8k",
            "Cinematic 9:16 vertical gentle hands scooping crystal clear pool water in bright sunlit morning, 8k"
        ],
        "engagement_question": "Do you believe in miracles? Say AMEN! 👁️"
    },

    # 5. NIGHT PRAYER & PEACE (09:30 PM)
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_91_abide_in_the_shadow",
        "headline": "He who dwells in the secret place of the Most High shall abide in His shadow",
        "verse_reference": "Psalm 91:1-2",
        "voiceover_script": "As nighttime falls, draw near to the secret place of God's presence. He who watches over you neither slumbers nor sleeps. Under His wings you will find refuge and absolute safety. Lay down all your worries and rest in the assurance that angels are guarding your home.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic dark blue night sky filled with radiant twinkling stars over peaceful sleeping village, 8k",
            "Cinematic 9:16 vertical glowing angel wings silhouette in deep celestial blue night sky with warm golden aura, 8k"
        ],
        "engagement_question": "Claim Psalm 91 protection over your family tonight. Type AMEN! 🕊️"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_23_the_lord_is_my_shepherd",
        "headline": "The Lord is my Shepherd; I shall not want. He restores my soul",
        "verse_reference": "Psalm 23:1-3",
        "voiceover_script": "Lord Jesus, thank You for guiding our steps throughout this day. Even when we walk through the valley of the shadow of death, we fear no evil, for You are with us. Lead our thoughts beside quiet waters tonight, restore our weary souls, and grant us peaceful sleep.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene tranquil lake under twilight sky reflecting crescent moon and evening star, 8k",
            "Cinematic 9:16 vertical warm glowing lantern resting on rustic wooden porch looking out into peaceful night forest, 8k"
        ],
        "engagement_question": "Rest in the Good Shepherd's care tonight. Amen! 🌿"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_4_8_sleep_in_peace",
        "headline": "I will both lie down in peace, and sleep; for You alone make me dwell in safety",
        "verse_reference": "Psalm 4:8",
        "voiceover_script": "Father, we release every unspoken hurt, unfinished task, and racing thought into Your tender care. Cleanse our minds with Your peace that surpasses all understanding. May every home watching this be filled with tranquility, healing, and heavenly rest tonight.",
        "visual_prompts": [
            "Cinematic 9:16 vertical cozy warm bedroom with soft candle glow and starlight visible through window, peaceful sanctuary, 8k",
            "Cinematic 9:16 vertical still waters of mountain lake reflecting glowing moonbeams on gentle ripples, 8k"
        ],
        "engagement_question": "Receive peaceful sleep tonight in Jesus' name. Type AMEN! 🌙"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_john_14_27_peace_i_leave_with_you",
        "headline": "Peace I leave with you; My peace I give to you, not as the world gives",
        "verse_reference": "John 14:27",
        "voiceover_script": "Lord, the world offers fleeting comfort, but You give us everlasting peace. Tonight, silence every voice of fear, regret, and anxiety. Let Your divine tranquility wash over every weary heart. We trust our lives into Your loving hands. In Jesus' name, Amen.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful calm ocean under deep twilight sky with soft celestial glow on horizon, 8k",
            "Cinematic 9:16 vertical praying hands gently illuminated by warm soft candlelight, deep reverent peace, 8k"
        ],
        "engagement_question": "May His peace rest upon your heart tonight. Amen! ✨"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_1_peter_5_7_cast_all_anxieties",
        "headline": "Casting all your anxieties on Him, because He cares for you deeply",
        "verse_reference": "1 Peter 5:7",
        "voiceover_script": "Dear friend, you were never created to carry the weight of tomorrow on your shoulders tonight. Jesus invites you to unload every fear, debt, sickness, and burden into His hands because He cares for you deeply. Rest tonight knowing God is handling tomorrow.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouette of person kneeling in quiet prayer beside window looking at starlit night sky, 8k",
            "Cinematic 9:16 vertical warm golden cross glowing softly against deep velvet midnight blue sky, 8k"
        ],
        "engagement_question": "Give your worries to God and sleep in peace. Type AMEN! 💖"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_121_keeper_will_not_slumber",
        "headline": "Behold, He who keeps you shall neither slumber nor sleep",
        "verse_reference": "Psalm 121:4-8",
        "voiceover_script": "Close your eyes in total peace tonight. The Maker of heaven and earth is staying awake to protect your home. The sun shall not strike you by day, nor the moon by night. The Lord shall preserve your going out and your coming in from this time forth and forevermore.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful family home bathed in gentle moonlight with stars shining bright above, safe sanctuary, 8k",
            "Cinematic 9:16 vertical protective celestial light beam shining down from heaven onto peaceful sleeping valley, 8k"
        ],
        "engagement_question": "God is watching over your home tonight. Say AMEN! 🛡️"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_numbers_6_the_lord_bless_you_and_keep_you",
        "headline": "The Lord bless you and keep you; the Lord make His face shine upon you",
        "verse_reference": "Numbers 6:24-26",
        "voiceover_script": "Before you sleep, receive this eternal priestly blessing: The Lord bless you and keep you. The Lord make His face shine upon you and be gracious to you. The Lord lift up His countenance upon you, and give you peace. Sleep in His love tonight. Amen.",
        "visual_prompts": [
            "Cinematic 9:16 vertical divine radiant light shining from heaven with soft glowing dust motes floating peacefully, 8k",
            "Cinematic 9:16 vertical calm night sky adorned with milky way galaxy over tranquil silhouetted hills, 8k"
        ],
        "engagement_question": "Receive this divine blessing for your household! Type AMEN! 🌟"
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
    Generates a fresh, spirit-filled English devotional Reel using Google Gemini:
    - Tailored for global Christian audiences across Philippines, Nigeria, South Africa, USA, and India
    - Dedicated to 'Jesus Hears You'
    - NO mentions of 'AI'
    - NO '24/7 daily'
    - NO cheesy greetings
    - Uplifting scripture promise, warm pastoral narration, and inspiring peaceful ending
    """
    if not GEMINI_API_KEY:
        return None

    cat_id = category_info["id"]
    cat_desc = category_info["theme_desc"]

    prompt = f"""
You are a warm, compassionate Christian pastor and devotional scriptwriter for the global page "Jesus Hears You".
Your audience spans devoted believers in the Philippines, Nigeria, South Africa, the United States, and India.
Create a deeply moving, faith-strengthening, and uplifting 30-40 second devotional Reel in clear, accessible English.

CATEGORY: {category_info['name']} ({cat_id})
THEME: {cat_desc}

DO NOT repeat any of these recently used topics/verses:
{json.dumps(used_topics[-25:], ensure_ascii=False)}

CRITICAL INSTRUCTIONS:
1. "headline": A powerful, uplifting scripture promise or core takeaway in clear English (8-14 words max).
2. "verse_reference": The exact Bible book, chapter and verse (e.g. "Joshua 1:5", "Philippians 4:13").
3. "voiceover_script": A deeply comforting, inspiring narration in natural spoken English (45-65 words, ~25-30 seconds of speech).
   - Hook the listener with God's unfailing love in the VERY FIRST sentence.
   - Speak with warmth, gentle encouragement, and unshakeable peace.
   - ABSOLUTELY NO greetings (NO "Hello friends", NO "Welcome back").
   - NEVER mention the word "AI" anywhere!
   - NEVER mention "24/7 daily" anywhere!
   - End with a heartfelt blessing or promise (e.g. "May His peace rest upon your heart today. God bless you.").
4. "visual_prompts": A list of 2 distinct, complementary English visual prompts for high-resolution 9:16 photorealistic imagery.
   - e.g. "Cinematic 9:16 vertical view of golden sunlight breaking through heavenly clouds over tranquil ocean, 8k"
   - e.g. "Cinematic 9:16 vertical close up of open Holy Bible glowing with soft divine light, 8k"
   - NO text, NO watermarks in the prompts.
5. "engagement_question": An uplifting faith question or call-to-action (e.g. "Type AMEN if you receive this promise today! 🙏", "Share this blessing with someone who needs peace ✨").
6. "topic_id": A short unique English slug (e.g. "joshua_1_5_never_leave_you").

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
                    res["caption"] = format_christian_caption(res, category_info)
                    return res
            elif resp.status_code == 429:
                print(f"Gemini {model_name} rate limited (429), trying fallback model...")
                continue
        except Exception as e:
            print(f"Notice: Gemini Christian generation notice ({model_name}): {e}")
            continue

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
                    res["caption"] = format_christian_caption(res, category_info)
                    return res
            elif resp.status_code == 429:
                print(f"Gemini {model_name} rate limited (429), trying fallback model...")
                continue
        except Exception as e:
            print(f"Notice: Gemini Christian generation notice ({model_name}): {e}")
            continue

    return None

def format_christian_caption(story, cat_info):
    """
    Formats a faith-filled, engaging devotional Facebook caption for 'Jesus Hears You'
    tailored for global Christian audiences across Philippines, Nigeria, South Africa, USA, and India:
    - Devotional Category Header
    - Scripture Verse & Bible Reference
    - Heartfelt Devotional Message
    - Call to Faith & Prayer ("Type AMEN", "Share this blessing")
    - Follow prompt (@JesusHearsYou)
    - Curated global Christian hashtags
    """
    badge = cat_info.get("badge_tag") or cat_info.get("name", "✝️ Jesus Hears You")
    headline = story.get("headline", "")
    verse_ref = story.get("verse_reference", "")
    script = (story.get("voiceover_script") or story.get("english_script") or story.get("script") or "").strip()
    question = story.get("engagement_question") or "Type 'AMEN' to claim this blessing today! 🕊️"
    hashtags = cat_info.get("hashtags") or "#JesusHearsYou #Jesus #DailyBibleVerse #GodIsGood #FaithOverFear #ChristianReels #Reels"

    verse_block = ""
    if verse_ref:
        verse_block = f"📖 Scripture:\n\"{headline}\"\n— {verse_ref}\n\n"
    elif headline:
        verse_block = f"✨ {headline}\n\n"

    thought_block = ""
    if script:
        thought_block = f"🕊️ Devotional Message:\n{script}\n\n"

    caption = (
        f"✝️ Jesus Hears You • {badge}\n\n"
        f"{verse_block}"
        f"{thought_block}"
        f"💬 {question}\n\n"
        f"🔔 Follow @JesusHearsYou for daily uplifting Bible verses and Christian prayers! ✝️\n\n"
        f"{hashtags}"
    )
    return caption.strip()

def crop_to_exact_9_16_vertical(source_image_path, output_path, target_width=1080, target_height=1920):
    """
    Ensures the image is true full-bleed 9:16 vertical (1080x1920):
    - Completely fills the 1080x1920 screen with the image itself (no blurred letterboxing, no bars).
    - Uses high-quality LANCZOS resampling and center cropping.
    """
    with Image.open(source_image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        target_ratio = target_width / target_height  # 9/16 = 0.5625
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Image is wider than 9:16: fit height, crop width
            new_h = target_height
            new_w = int(w * (target_height / h))
        else:
            # Image is narrower or equal: fit width, crop height
            new_w = target_width
            new_h = int(h * (target_width / w))

        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_width) // 2
        top = (new_h - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        cropped = resized.crop((left, top, right, bottom))
        cropped.save(output_path, "JPEG", quality=95)
        return output_path

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
        script = (story_data.get("voiceover_script") or story_data.get("english_script") or "").strip()
        story_data["voiceover_script"] = script
        story_data["tamil_script"] = script
        story_data["caption"] = format_christian_caption(story_data, category)

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
    script = (chosen.get("voiceover_script") or chosen.get("english_script") or "").strip()
    chosen["voiceover_script"] = script
    chosen["tamil_script"] = script
    chosen["caption"] = format_christian_caption(chosen, cat_match)

    current_state = load_christian_state()
    current_state["used_topics"].append(chosen["topic_id"])
    save_christian_state(current_state)
    return chosen

# Aliases for pipeline compatibility
get_scheduled_christian_category = get_scheduled_category_for_now
generate_christian_story = get_christian_story


def fetch_christian_visual(visual_prompt, category_id="promise", scene_idx=0, suffix=""):
    """
    Downloads or renders a 9:16 vertical image for the Christian devotional reel:
    1. Tries Pollinations Flux AI generator (1080x1920) with prompt.
    2. Fallback to serene, divine high-resolution category images.
    Always produces a true full-bleed 1080x1920 vertical canvas (no letterbox bars).
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_filename = f"christian_visual_{int(time.time())}{suffix}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    temp_raw = os.path.join(OUTPUT_DIR, f"temp_cv_{int(time.time())}{suffix}.jpg")

    # 1. Try Pollinations Flux (Fast & Free 9:16)
    if visual_prompt:
        try:
            clean_p = visual_prompt.replace("\n", " ").strip()[:200]
            # Ensure prompt specifies full-bleed 9:16 vertical composition
            enhanced_p = f"{clean_p}, vertical 9:16 aspect ratio portrait orientation, full frame mobile vertical video background 1080x1920, photorealistic 8k, divine cinematic light"
            encoded = quote(enhanced_p)
            ai_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&model=flux"
            resp = _session.get(ai_url, timeout=18)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(temp_raw, "wb") as f:
                    f.write(resp.content)
                crop_to_exact_9_16_vertical(temp_raw, out_path)
                if os.path.exists(temp_raw):
                    try:
                        os.remove(temp_raw)
                    except Exception:
                        pass
                if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                    print(f"🎨 Successfully generated 9:16 Divine Visual for: {clean_p[:40]}...")
                    return out_path
        except Exception as e:
            print(f"Notice: Pollinations Christian visual notice: {e}")

    # 2. High-Quality Divine 9:16 Unsplash Fallback Bank (Multi-scene support)
    category_fallbacks = {
        "promise": [
            "https://images.unsplash.com/photo-1509021436665-8f07dbf5bf1d?w=1080&h=1920&fit=crop&q=85", # Divine sunbeams through clouds
            "https://images.unsplash.com/photo-1519817650390-64a93db51149?w=1080&h=1920&fit=crop&q=85", # Heavenly golden sunrise mountain
            "https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=1080&h=1920&fit=crop&q=85"  # Radiant morning light
        ],
        "wisdom": [
            "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=1080&h=1920&fit=crop&q=85", # Peaceful ancient olive grove
            "https://images.unsplash.com/photo-1499209974431-9dddcece7f88?w=1080&h=1920&fit=crop&q=85", # Open Bible peaceful morning
            "https://images.unsplash.com/photo-1516796181074-bf453fbfa3e6?w=1080&h=1920&fit=crop&q=85"  # Peaceful path golden light
        ],
        "parable": [
            "https://images.unsplash.com/photo-1470240731273-7821a6eeb6bd?w=1080&h=1920&fit=crop&q=85", # Green pastures & sunlit mountains
            "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=1080&h=1920&fit=crop&q=85", # Majestic peaceful sunrise
            "https://images.unsplash.com/photo-1448375240586-882707db888b?w=1080&h=1920&fit=crop&q=85"  # Serene green valley
        ],
        "mystery": [
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1080&h=1920&fit=crop&q=85", # Heavenly earth and celestial sky
            "https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=1080&h=1920&fit=crop&q=85", # Ancient misty dawn
            "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1080&h=1920&fit=crop&q=85"  # Ancient tranquil waters
        ],
        "prayer": [
            "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1080&h=1920&fit=crop&q=85", # Peaceful sunset rays
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1080&h=1920&fit=crop&q=85", # Calm sunset sea
            "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1080&h=1920&fit=crop&q=85"  # Peaceful starry night sky
        ]
    }
    fb_list = category_fallbacks.get(category_id, category_fallbacks["promise"])
    fb_url = fb_list[scene_idx % len(fb_list)]

    try:
        resp = _session.get(fb_url, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 10000:
            with open(temp_raw, "wb") as f:
                f.write(resp.content)
            crop_to_exact_9_16_vertical(temp_raw, out_path)
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
    Downloads or renders MULTIPLE true 9:16 vertical images for a Christian reel
    so the video dynamically transitions through multiple peaceful full-screen scenes with Ken Burns zoom.
    """
    if not isinstance(visual_prompts, (list, tuple)):
        visual_prompts = [visual_prompts] if visual_prompts else []

    visual_paths = []
    for idx, prompt_text in enumerate(visual_prompts[:2]):
        vp = fetch_christian_visual(prompt_text, category_id, scene_idx=idx, suffix=f"_{idx}")
        if vp and os.path.exists(vp):
            visual_paths.append(vp)

    if not visual_paths:
        fb = fetch_christian_visual(None, category_id, scene_idx=0, suffix="_fb")
        if fb:
            visual_paths.append(fb)

    return visual_paths

