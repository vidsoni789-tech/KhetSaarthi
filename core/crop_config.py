"""Agronomic Crop Configuration, FAO-56 Parameters, and Regulatory Label Registry.

Sources and Citations:
1. FAO Irrigation and Drainage Paper No. 56: "Crop Evapotranspiration - Guidelines for computing
   crop water requirements", Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998), Table 12.
2. FAO Irrigation and Drainage Paper No. 33: "Yield response to water", Doorenbos, J. and Kassam, A.H. (1979).
3. Central Insecticides Board & Registration Committee (CIBRC), Ministry of Agriculture & Farmers Welfare,
   Government of India: "Major Uses of Pesticides Registered Under the Insecticides Act, 1968".
4. Indian Council of Agricultural Research (ICAR) & State Agricultural Universities (MPKV Rahuri, VNMKV Parbhani).
"""
from __future__ import annotations

from typing import Any

# =====================================================================
# 1. CROP METADATA, FAO-56 Kc, AND STAGE-SENSITIVITY PARAMETERS
# =====================================================================

CROP_AGRONOMY_REGISTRY: dict[str, dict[str, Any]] = {
    "Soybean": {
        "scientific_name": "Glycine max",
        "local_names": {"en": "Soybean", "hi": "सोयाबीन", "mr": "सोयाबीन"},
        # FAO-56 Table 12: Kc ini = 0.40, Kc mid = 1.15, Kc end = 0.50
        "kc": {
            "Sowing": 0.40,
            "Vegetative": 0.80,
            "Flowering": 1.15,
            "Maturity / Harvest": 0.50,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12 (Allen et al., 1998)",
        # FAO-33 Yield response factor Ky: overall = 0.85, flowering = 1.3 (very high sensitivity to water deficit)
        "ky_water_stress": {
            "Sowing": 0.4,
            "Vegetative": 0.6,
            "Flowering": 1.3,
            "Maturity / Harvest": 0.3,
        },
        "stage_warnings": {
            "Flowering": {
                "en": "CRITICAL POLLINATOR WINDOW: Crop is in active flowering. Foliar insecticide sprays present severe bee mortality risk. Avoid daylight spraying (9 AM - 4 PM). Water stress during flowering causes massive flower and pod abortion.",
                "hi": "संवेदनशील फूल अवस्था: फसल में फूल आ रहे हैं। दिन में कीटनाशक छिड़काव से मधुमक्खियां मरती हैं, जिससे पैदावार गिरती है। दिन के समय (सुबह 9 से शाम 4) छिड़काव न करें। इस अवस्था में पानी की कमी से फूल झड़ते हैं।",
                "mr": "अतिसंवेदनशील फुलोरा अवस्था: पिकात मधमाशा परागीभवन करत आहेत. दिवसा कीटकनाशक फवारणी केल्यास मधमाशा मरून फुलगळ होते व उत्पादनात मोठी घट येते. सकाळी ९ ते दुपारी ४ दरम्यान फवारणी पूर्णपणे टाळा. फुलोऱ्यात पाण्याचा ताण पडू देऊ नका.",
            },
            "Maturity / Harvest": {
                "en": "PRE-HARVEST INTERVAL (PHI) & DRAINAGE: Stop chemical applications to observe statutory PHI residues. Cease irrigation 10-15 days before harvest to facilitate uniform ripening and prevent pod shattering or mold.",
                "hi": "कटाई पूर्व सावधानी (PHI): कीटनाशक अवशेष से बचने के लिए कटाई से पहले दवा न डालें। कटाई से 10-15 दिन पहले सिंचाई बंद करें ताकि फलियां समान रूप से पकें और फफूंद न लगे।",
                "mr": "कापणीपूर्व खबरदारी (PHI): काढणी जवळ आल्याने रासायनिक औषध फवारणी थांबवा जेणेकरून अन्नात अंश राहणार नाहीत. शेंगा काळ्या पडणे व बुरशी टाळण्यासाठी काढणीपूर्वी १०-१५ दिवस पाणी देणे बंद करा.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Spodoptera / Tobacco Caterpillar (Spodoptera litura)",
            "Semilooper / Pod Borer (Helicoverpa armigera)",
            "Girdle Beetle (Obereopsis brevis)",
            "Anthracnose / Pod Blight (Colletotrichum truncatum)",
            "Yellow Mosaic Virus (Whitefly vector)",
        ],
    },
    "Cotton": {
        "scientific_name": "Gossypium hirsutum",
        "local_names": {"en": "Cotton", "hi": "कपास", "mr": "कापूस"},
        # FAO-56 Table 12: Kc ini = 0.45, Kc mid = 1.20, Kc end = 0.65
        "kc": {
            "Sowing": 0.45,
            "Vegetative": 0.75,
            "Flowering": 1.20,
            "Maturity / Harvest": 0.65,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12",
        "ky_water_stress": {
            "Sowing": 0.5,
            "Vegetative": 0.7,
            "Flowering": 1.25,
            "Maturity / Harvest": 0.4,
        },
        "stage_warnings": {
            "Flowering": {
                "en": "SQUARE & BOLL FORMATION: High moisture stress causes shedding of squares and young bolls. Protect honeybees; avoid broad-spectrum insecticides during peak bloom.",
                "hi": "फूल व बोंड बनने की अवस्था: नमी की कमी से कलियां और बोंड गिर जाते हैं। मधुमक्खियों को बचाएं; दोपहर में कीटनाशक छिड़काव से बचें।",
                "mr": "पाती व बोंड धरण्याची अवस्था: पाण्याच्या ताणामुळे पातेगळ व बोंडगळ होते. फुलोऱ्यात मधमाशांचे रक्षण करा; दुपारी विषारी कीटकनाशकांची फवारणी टाळा.",
            },
            "Maturity / Harvest": {
                "en": "BOLL BURSTING: Excessive soil moisture delays boll opening and stains lint. Terminate irrigation when 10% bolls open.",
                "hi": "बोंड खिलने की अवस्था: अत्यधिक नमी से बोंड सड़ते हैं और रुई खराब होती है। 10% बोंड खुलने पर सिंचाई बंद करें।",
                "mr": "बोंडे फुटण्याची अवस्था: जमिनीत जास्त ओलावा राहिल्यास बोंडे कुजतात व कापूस डागाळतो. बोंडे फुटू लागताच सिंचन थांबवा.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Pink Bollworm (Pectinophora gossypiella)",
            "American Bollworm (Helicoverpa armigera)",
            "Whitefly & Jassids (Sucking pest complex)",
            "Aphids & Thrips",
            "Bacterial Blight / Boll Rot",
        ],
    },
    "Onion": {
        "scientific_name": "Allium cepa",
        "local_names": {"en": "Onion", "hi": "प्याज", "mr": "कांदा"},
        # FAO-56 Table 12: Kc ini = 0.50, Kc mid = 1.05, Kc end = 0.75
        "kc": {
            "Sowing": 0.50,
            "Vegetative": 0.70,
            "Flowering": 1.05,
            "Maturity / Harvest": 0.75,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12",
        "ky_water_stress": {
            "Sowing": 0.6,
            "Vegetative": 0.8,
            "Flowering": 1.1,
            "Maturity / Harvest": 0.4,
        },
        "stage_warnings": {
            "Vegetative": {
                "en": "THRIPS & PURPLE BLOTCH WATCH: Humid overcast weather accelerates purple blotch fungal spread. Scout leaf axils for thrips.",
                "hi": "थ्रिप्स व बैंगनी धब्बा रोग: बादलों वाले आर्द्र मौसम में थ्रिप्स और परपल ब्लॉच तेजी से फैलता है। नियमित निगरानी करें।",
                "mr": "थ्रिप्स (फुलकिडे) व करपा सावधगिरी: ढगाळ व दमट हवामानात कांद्यावर करपा व थ्रिप्सचा प्रादुर्भाव वेगाने वाढतो. शेतात सतत फेरफटका मारा.",
            },
            "Maturity / Harvest": {
                "en": "NECK FALL & CURING: Withhold irrigation 10-15 days prior to harvest when 50% tops fall. Wet soil causes bulb rot and ruins storage life.",
                "hi": "गर्दन झुकने व खुदाई अवस्था: 50% पत्तियां झुकने पर सिंचाई पूरी तरह बंद करें। गीली मिट्टी से कांदा भंडारण में सड़ जाता है।",
                "mr": "कांदा काढणी व माना पडणे: ५०% माना पडताच पाणी देणे पूर्णपणे बंद करा. काढणीवेळी शेतात ओल असल्यास साठवणुकीत कांदा सडतो.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Onion Thrips (Thrips tabaci)",
            "Purple Blotch (Alternaria porri)",
            "Stemphyllium Blight",
            "Basal Rot (Fusarium oxysporum)",
            "Collar Rot / Damping Off",
        ],
    },
    "Wheat": {
        "scientific_name": "Triticum aestivum",
        "local_names": {"en": "Wheat", "hi": "गेहूं", "mr": "गहू"},
        "kc": {
            "Sowing": 0.40,
            "Vegetative": 0.75,
            "Flowering": 1.15,
            "Maturity / Harvest": 0.40,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12",
        "ky_water_stress": {"Sowing": 0.4, "Vegetative": 0.6, "Flowering": 1.15, "Maturity / Harvest": 0.3},
        "stage_warnings": {
            "Flowering": {
                "en": "HEADING & FLOWERING: Crown root initiation and flowering are most critical stages. Moisture stress causes grain shriveling.",
                "hi": "फूल व बाली बनने की अवस्था: यह सबसे संवेदनशील अवस्था है। पानी की कमी से दाने सिकुड़ जाते हैं।",
                "mr": "ओंबी व फुलोरा अवस्था: ही पाण्याची अत्यंत संवेदनशील अवस्था आहे. ताण पडल्यास दाणे बारीक व चपटे राहतात.",
            },
            "Maturity / Harvest": {
                "en": "GRAIN HARDENING: Cease irrigation once grain turns hard dough. Prevent lodging from high winds on wet soil.",
                "hi": "दाना पकने की अवस्था: दाना सख्त होने पर सिंचाई रोकें। तेज हवा में फसल गिरने से बचाएं।",
                "mr": "दाणे भरण्याची अंतिम अवस्था: दाणे घट्ट होताच पाणी बंद करा. ओल्या जमिनीत जोराचा वारा सुटल्यास पीक लोळण्याची भीती असते.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Wheat Rust (Puccinia spp.)",
            "Loose Smut",
            "Aphids (Rhopalosiphum padi)",
            "Termites",
        ],
    },
    "Rice": {
        "scientific_name": "Oryza sativa",
        "local_names": {"en": "Rice (Paddy)", "hi": "धान / चावल", "mr": "भात (धान)"},
        "kc": {
            "Sowing": 1.10,  # Flooded field evaporation
            "Vegetative": 1.15,
            "Flowering": 1.25,
            "Maturity / Harvest": 0.90,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12 (Wetland Paddy)",
        "ky_water_stress": {"Sowing": 0.7, "Vegetative": 0.9, "Flowering": 1.3, "Maturity / Harvest": 0.5},
        "stage_warnings": {
            "Flowering": {
                "en": "PANICLE INITIATION & FLOWERING: Maintain 2-5 cm shallow standing water. Never allow soil drying during anthesis.",
                "hi": "बाली निकलने व फूल की अवस्था: खेत में 2-5 सेमी पानी बनाए रखें। इस समय खेत सूखना नहीं चाहिए।",
                "mr": "पोंगा व फुलोरा अवस्था: खाचरात २ ते ५ सेंमी पाणी कायम ठेवा. या अवस्थेत खाचर कधीही कोरडे पडू देऊ नका.",
            },
            "Maturity / Harvest": {
                "en": "GRAIN RIPENING: Drain water completely 10 days before harvest to facilitate mechanical harvesting and firm grains.",
                "hi": "कटाई पूर्व अवस्था: कटाई से 10 दिन पहले खेत का पानी निकाल दें ताकि कटाई आसान हो और दाने मजबूत बनें।",
                "mr": "कापणी पूर्व अवस्था: दाणे पक्व होताच कापणीच्या १० दिवस आधी खाचरातील पाणी काढून टाका.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Yellow Stem Borer (Scirpophaga incertulas)",
            "Brown Plant Hopper (Nilaparvata lugens)",
            "Bacterial Leaf Blight (Xanthomonas oryzae)",
            "Rice Blast (Pyricularia oryzae)",
            "Leaf Folder",
        ],
    },
    "Maize": {
        "scientific_name": "Zea mays",
        "local_names": {"en": "Maize / Corn", "hi": "मक्का", "mr": "मका"},
        "kc": {
            "Sowing": 0.40,
            "Vegetative": 0.85,
            "Flowering": 1.20,
            "Maturity / Harvest": 0.55,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12",
        "ky_water_stress": {"Sowing": 0.4, "Vegetative": 0.7, "Flowering": 1.25, "Maturity / Harvest": 0.4},
        "stage_warnings": {
            "Flowering": {
                "en": "TASSELING & SILKING: Maize is exceptionally vulnerable to moisture deficit during silking, which prevents kernel pollination.",
                "hi": "नर व मादा फूल (सिल्क) अवस्था: सिल्क निकलते समय पानी की कमी से भुट्टे में दाने नहीं भरते। पर्याप्त नमी रखें।",
                "mr": "तुरा व कणसाला चवऱ्या फुटणे: या काळात पाण्याचा ताण पडल्यास परागीभवन अपूर्ण राहून कणसात दाणे भरत नाहीत.",
            },
            "Maturity / Harvest": {
                "en": "BLACK LAYER / MATURITY: Reduce irrigation as husk dries. High rainfall on mature cobs risks fungal ear rot and aflatoxins.",
                "hi": "भुट्टा पकने की अवस्था: भुट्टे सूखने पर सिंचाई बंद करें। अत्यधिक बारिश से दानों में फफूंद का खतरा रहता है।",
                "mr": "कणीस पक्वता: कणसे वाळू लागल्यावर पाणी बंद करा. पक्व कणसांवर पाऊस पडल्यास दाण्यांवर बुरशी वाढते.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Fall Armyworm (Spodoptera frugiperda)",
            "Maize Stem Borer (Chilo partellus)",
            "Turcicum Leaf Blight",
            "Downy Mildew",
        ],
    },
    "Sugarcane": {
        "scientific_name": "Saccharum officinarum",
        "local_names": {"en": "Sugarcane", "hi": "गन्ना", "mr": "ऊस"},
        "kc": {
            "Sowing": 0.50,
            "Vegetative": 1.00,
            "Flowering": 1.25,
            "Maturity / Harvest": 0.75,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12",
        "ky_water_stress": {"Sowing": 0.4, "Vegetative": 0.8, "Flowering": 1.0, "Maturity / Harvest": 0.5},
        "stage_warnings": {
            "Flowering": {
                "en": "GRAND GROWTH PERIOD: High water demand. Maintain optimal soil moisture to maximize cane length and girth.",
                "hi": "तीव्र वृद्धि अवस्था: गन्ने की लंबाई और मोटाई के लिए इस समय पानी की भरपूर आवश्यकता होती है।",
                "mr": "मोठी वाढीची अवस्था: उसाची कांडी भरण्यासाठी व लांबीसाठी या काळात भरपूर पाण्याची गरज असते. ओलावा टिकवून ठेवा.",
            },
            "Maturity / Harvest": {
                "en": "SUGAR ACCUMULATION: Mild water stress 3-4 weeks prior to harvest promotes sucrose maturation and brix level.",
                "hi": "शर्करा संचयन (परिपक्वता): कटाई से 3-4 सप्ताह पहले हल्का सूखा गन्ने में मिठास (सुक्रोज) बढ़ाता है।",
                "mr": "साखर पक्वता: तोडणीपूर्वी ३-४ आठवडे थोडे पाणी तोडल्यास उसात साखरेचे प्रमाण (सुक्रोज) वाढते.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Early Shoot Borer",
            "White Grub (Holotrichia serrata)",
            "Red Rot (Colletotrichum falcatum)",
            "Woolly Aphid",
            "Pyrilla",
        ],
    },
    "Groundnut": {
        "scientific_name": "Arachis hypogaea",
        "local_names": {"en": "Groundnut / Peanut", "hi": "मूंगफली", "mr": "भुईमूग"},
        "kc": {
            "Sowing": 0.40,
            "Vegetative": 0.75,
            "Flowering": 1.10,
            "Maturity / Harvest": 0.55,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12",
        "ky_water_stress": {"Sowing": 0.4, "Vegetative": 0.6, "Flowering": 1.15, "Maturity / Harvest": 0.3},
        "stage_warnings": {
            "Flowering": {
                "en": "PEGGING & POD DEVELOPMENT: Soil must remain loose and friable. Hard dry crust prevents pegs from entering soil.",
                "hi": "आर्या (सुई) जमीन में जाने की अवस्था: मिट्टी भुरभुरी और नम रखें ताकि आर्या आसानी से जमीन में प्रवेश कर सकें।",
                "mr": "आऱ्या जमिनीत जाणे (पेगिंग): आऱ्या सहज जमिनीत घुसण्यासाठी जमीन भुसभुशीत व ओलसर असणे आवश्यक आहे.",
            },
            "Maturity / Harvest": {
                "en": "POD MATURITY: Excessive soil moisture at maturity induces in-situ seed germination and aflatoxin contamination.",
                "hi": "शेंग परिपक्वता: कटाई के समय अधिक नमी से फलियां खेत में ही अंकुरित होने लगती हैं। सिंचाई रोकें।",
                "mr": "शेंगा पक्वता: काढणीच्या सुमारास जास्त पाणी राहिल्यास शेंगांना शेतातच कोंब फुटतात व बुरशी लागते.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Tikka Leaf Spot (Cercospora arachidicola)",
            "Spodoptera / Leaf Miner",
            "White Grub",
            "Collar Rot (Aspergillus niger)",
        ],
    },
    "Tomato": {
        "scientific_name": "Solanum lycopersicum",
        "local_names": {"en": "Tomato", "hi": "टमाटर", "mr": "टोमॅटो"},
        "kc": {
            "Sowing": 0.45,
            "Vegetative": 0.80,
            "Flowering": 1.15,
            "Maturity / Harvest": 0.70,
        },
        "kc_source": "FAO Irrigation and Drainage Paper 56, Table 12",
        "ky_water_stress": {"Sowing": 0.5, "Vegetative": 0.8, "Flowering": 1.2, "Maturity / Harvest": 0.5},
        "stage_warnings": {
            "Flowering": {
                "en": "FLOWERING & FRUIT SET: Fluctuating moisture causes blossom end rot and heavy flower drop. Maintain steady root moisture.",
                "hi": "फूल व फल लगने की अवस्था: नमी में उतार-चढ़ाव से फूल गिरते हैं और फल सड़ने लगते हैं। नियमित हल्की सिंचाई करें।",
                "mr": "फुलोरा व फळधारणा: जमिनीत पाण्याचा चढ-उतार झाल्यास फुलगळ होते व फळांवर चट्टे पडतात. एकसारखा ओलावा ठेवा.",
            },
            "Maturity / Harvest": {
                "en": "FRUIT RIPENING: Heavy rain or over-irrigation on dry beds causes severe fruit cracking and splitting.",
                "hi": "फल पकने की अवस्था: सूखे के बाद अचानक पानी देने या भारी बारिश से टमाटर फटने लगते हैं।",
                "mr": "फळे पिकणे: कोरड्या वाफ्याला अचानक जास्त पाणी दिल्यास किंवा मुसळधार पाऊस झाल्यास टोमॅटो तडकतात (क्रॅकिंग).",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Tomato Leaf Curl Virus (Whitefly)",
            "Early Blight & Late Blight",
            "Fruit Borer (Helicoverpa armigera)",
            "Tuta absoluta (Tomato Pinworm)",
            "Bacterial Wilt",
        ],
    },
    "Tur / Pigeon Pea": {
        "scientific_name": "Cajanus cajan",
        "local_names": {"en": "Tur / Pigeon Pea", "hi": "अरहर / तुअर", "mr": "तूर (अरहर)"},
        "kc": {
            "Sowing": 0.40,
            "Vegetative": 0.75,
            "Flowering": 1.15,
            "Maturity / Harvest": 0.50,
        },
        "kc_source": "ICRISAT / FAO Pulses Agronomy Guideline",
        "ky_water_stress": {"Sowing": 0.4, "Vegetative": 0.6, "Flowering": 1.2, "Maturity / Harvest": 0.3},
        "stage_warnings": {
            "Flowering": {
                "en": "POD BORER & WILT WATCH: Deep root system; waterlogging causes phytophthora stem blight. Protect honeybee pollination.",
                "hi": "फूल व फली अवस्था: खेत में पानी जमा न होने दें, इससे उकठा (विल्ट) रोग होता है। परागण के लिए मधुमक्खियों को बचाएं।",
                "mr": "फुलोरा व शेंगा भरणे: शेतात पाणी साचू देऊ नका, साचलेल्या पाण्याने मर व फायटोप्थोरा करपा होतो. मधमाशांचे रक्षण करा.",
            },
            "Maturity / Harvest": {
                "en": "POD MATURATION: Cease watering to allow uniform pod browning and drying.",
                "hi": "फली पकने की अवस्था: फलियां भूरी होने पर सिंचाई पूरी तरह बंद करें।",
                "mr": "शेंगा पक्वता: शेंगा वाळू लागल्यावर सिंचन बंद करा जेणेकरून डाळ तयार होणे सुलभ होईल.",
            },
        },
        "common_pests": [
            "None / Preventive Scouting",
            "Gram Pod Borer (Helicoverpa armigera)",
            "Pod Fly (Melanagromyza obtusa)",
            "Fusarium Wilt",
            "Phytophthora Stem Blight",
            "Sterility Mosaic Disease",
        ],
    },
}

# =====================================================================
# 2. SOIL TEXTURE CHARACTERISTICS & AVAILABLE WATER CAPACITY (AWC)
# =====================================================================

SOIL_CHARACTERISTICS: dict[str, dict[str, Any]] = {
    "Black Cotton / Clayey (Vertisol)": {
        "local_names": {"en": "Black Cotton / Clayey", "hi": "काली मिट्टी / भारी", "mr": "काळी / भारी जमीन (रेगूर)"},
        # Available Water Capacity (mm of water per meter of soil depth)
        "awc_mm_per_m": 190.0,
        "effective_rain_factor": 0.70,  # Higher surface runoff due to slow infiltration
        "max_effective_rain_mm_day": 40.0,
        "waterlogging_risk": "High",
        "description": "High water-retention capacity; prone to surface waterlogging and deep cracks when dry.",
    },
    "Loamy / Medium Alluvial": {
        "local_names": {"en": "Loamy / Medium", "hi": "दोमट / मध्यम मिट्टी", "mr": "मध्यम / गाळाची जमीन"},
        "awc_mm_per_m": 150.0,
        "effective_rain_factor": 0.80,  # Balanced infiltration and drainage
        "max_effective_rain_mm_day": 50.0,
        "waterlogging_risk": "Moderate",
        "description": "Ideal agricultural soil with balanced aeration and moisture holding capacity.",
    },
    "Sandy / Light Murrum": {
        "local_names": {"en": "Sandy / Light Murrum", "hi": "रेतीली / हल्की मिट्टी", "mr": "हलकी / मुरमाड जमीन"},
        "awc_mm_per_m": 80.0,
        "effective_rain_factor": 0.65,  # High percolation loss below root zone
        "max_effective_rain_mm_day": 30.0,
        "waterlogging_risk": "Low",
        "description": "Drains rapidly; low moisture retention requires frequent light water applications.",
    },
}

# =====================================================================
# 3. VERIFIED CIBRC REGISTRATION DATABASE FOR REGISTERED PESTICIDES
# =====================================================================
# Source: Central Insecticides Board & Registration Committee (CIBRC), GoI
# Only contains genuine, verified label-approved combinations.
# If a query does not match an entry here, dosage is STRICTLY UNVERIFIED.

VERIFIED_CIBRC_REGISTRY: dict[str, dict[str, Any]] = {
    ("Soybean", "Spodoptera / Tobacco Caterpillar (Spodoptera litura)", "Chlorantraniliprole 18.5% SC"): {
        "cibrc_approved": True,
        "active_ingredient": "Chlorantraniliprole 18.5% w/w SC",
        "registration_authority": "CIBRC Registered Under Section 9(3)",
        "label_dosage_ha": "150 ml in 500 liters water/ha",
        "label_dosage_acre": "60 ml in 200 liters water/acre",
        "water_volume_liters_acre": 200,
        "phi_days": 22,
        "hazard_class": "Class III (Slightly hazardous)",
        "pollinator_safety": "Toxic to aquatic life; apply during early morning or late evening when bees are not active.",
    },
    ("Soybean", "Semilooper / Pod Borer (Helicoverpa armigera)", "Emamectin Benzoate 5% SG"): {
        "cibrc_approved": True,
        "active_ingredient": "Emamectin Benzoate 5% SG",
        "registration_authority": "CIBRC Label Claim",
        "label_dosage_ha": "220 g in 500 liters water/ha",
        "label_dosage_acre": "88 g in 200 liters water/acre",
        "water_volume_liters_acre": 200,
        "phi_days": 14,
        "hazard_class": "Class II (Moderately hazardous)",
        "pollinator_safety": "Harmful to honeybees. Do not apply during full bloom.",
    },
    ("Onion", "Onion Thrips (Thrips tabaci)", "Spinetoram 11.7% SC"): {
        "cibrc_approved": True,
        "active_ingredient": "Spinetoram 11.7% SC",
        "registration_authority": "CIBRC Registered Label Claim",
        "label_dosage_ha": "400-450 ml in 500 liters water/ha",
        "label_dosage_acre": "160-180 ml in 200 liters water/acre",
        "water_volume_liters_acre": 200,
        "phi_days": 30,
        "hazard_class": "Class III",
        "pollinator_safety": "Toxic to bees exposed to direct treatment. Spray late evening.",
    },
    ("Onion", "Purple Blotch (Alternaria porri)", "Mancozeb 75% WP"): {
        "cibrc_approved": True,
        "active_ingredient": "Mancozeb 75% WP (Fungicide)",
        "registration_authority": "CIBRC Registered Product",
        "label_dosage_ha": "1500-2000 g in 750 liters water/ha",
        "label_dosage_acre": "600-800 g in 250-300 liters water/acre",
        "water_volume_liters_acre": 250,
        "phi_days": 7,
        "hazard_class": "Class U (Unlikely to present acute hazard)",
        "pollinator_safety": "Low hazard to pollinators, toxic to aquatic organisms.",
    },
    ("Cotton", "Whitefly & Jassids (Sucking pest complex)", "Flonicamid 50% WG"): {
        "cibrc_approved": True,
        "active_ingredient": "Flonicamid 50% WG",
        "registration_authority": "CIBRC Registered Label Claim",
        "label_dosage_ha": "150-200 g in 500 liters water/ha",
        "label_dosage_acre": "60-80 g in 200 liters water/acre",
        "water_volume_liters_acre": 200,
        "phi_days": 25,
        "hazard_class": "Class III",
        "pollinator_safety": "Relatively safe to beneficial insects once spray deposits dry.",
    },
    ("Tomato", "Fruit Borer (Helicoverpa armigera)", "Flubendiamide 39.35% SC"): {
        "cibrc_approved": True,
        "active_ingredient": "Flubendiamide 39.35% SC",
        "registration_authority": "CIBRC Registered Label Claim",
        "label_dosage_ha": "100-120 ml in 500 liters water/ha",
        "label_dosage_acre": "40-50 ml in 200 liters water/acre",
        "water_volume_liters_acre": 200,
        "phi_days": 5,
        "hazard_class": "Class III",
        "pollinator_safety": "Avoid contamination of flowering weeds bordering tomato beds.",
    },
}

SUPPORTED_CROPS: list[str] = list(CROP_AGRONOMY_REGISTRY.keys())
SUPPORTED_SOIL_TYPES: list[str] = list(SOIL_CHARACTERISTICS.keys())
SOIL_MOISTURE_STATES: list[str] = ["dry", "moist", "wet"]
IRRIGATION_METHODS: list[str] = [
    "Drip Irrigation (ठिबक सिंचन / ड्रिप)",
    "Sprinkler (तुषार सिंचन / स्प्रिंकलर)",
    "Furrow / Flood (पाटपाणी / खुला प्रवाह)",
]


def get_crop_config(crop: str) -> dict[str, Any]:
    """Retrieve agronomic registry for a given crop, with case-insensitive fallback."""
    for c_name, data in CROP_AGRONOMY_REGISTRY.items():
        if c_name.lower() == (crop or "").strip().lower():
            return data
    return CROP_AGRONOMY_REGISTRY.get("Soybean", {})


def get_kc(crop: str, growth_stage: str) -> float | None:
    """Retrieve FAO-56 Table 12 crop coefficient Kc for a crop and stage."""
    cfg = get_crop_config(crop)
    kc_dict = cfg.get("kc", {})
    for stage_key, val in kc_dict.items():
        if stage_key.lower() == (growth_stage or "").strip().lower():
            return val
    # Fallback to general default if exact stage not found
    return kc_dict.get("Vegetative", 0.80)


def get_ky(crop: str, growth_stage: str) -> float | None:
    """Retrieve FAO-33 water stress yield response factor Ky."""
    cfg = get_crop_config(crop)
    ky_dict = cfg.get("ky_water_stress", {})
    for stage_key, val in ky_dict.items():
        if stage_key.lower() == (growth_stage or "").strip().lower():
            return val
    return ky_dict.get("Vegetative", 0.80)


def get_cibrc_label(crop: str, pest: str, chemical: str) -> dict[str, Any] | None:
    """Retrieve verified CIBRC registration label data if exact or partial match exists."""
    c_lower = (crop or "").strip().lower()
    p_lower = (pest or "").strip().lower()
    ch_lower = (chemical or "").strip().lower()

    for (c, p, ch), data in VERIFIED_CIBRC_REGISTRY.items():
        if c.lower() in c_lower or c_lower in c.lower():
            if (p.lower() in p_lower or p_lower in p.lower()) and (ch.lower() in ch_lower or ch_lower in ch.lower()):
                return data
    return None

