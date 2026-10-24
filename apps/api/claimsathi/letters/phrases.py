"""Fixed wording of the Stage-1 letter in English, Gujarati and Hindi (FR-024). No model writes these.

Amounts, dates and claim numbers keep ASCII digits in every language, so the number scanner (AI-005) checks them
the same way. Quotes from regulations stay verbatim in English: that is the text the citation verifier checked.
Gujarati and Hindi are DRAFTS pending native-speaker review (NFR-021).
"""

from __future__ import annotations

LETTER_LANGUAGES = ("en", "gu", "hi")

PHRASES: dict[str, dict[str, str]] = {
    "en": {
        "date": "Date: {date}",
        "to": "To: The Grievance Redressal Officer, {insurer}",
        "subject_rejected": "Subject: Request to review the rejection of claim {claim} under policy {policy}",
        "subject_partial": "Subject: Request to review deductions in claim {claim} under policy {policy}",
        "salutation": "Dear Sir or Madam,",
        "facts_rejected_dated": "My claim {claim} was rejected by your letter dated {date}.",
        "facts_rejected": "My claim {claim} was rejected.",
        "facts_settled_dated": "My claim {claim} was settled by your letter dated {date}.",
        "facts_settled": "My claim {claim} was settled.",
        "amounts_both": "The amount claimed was {claimed} and the amount paid was {paid}.",
        "amount_claimed": "The amount claimed was {claimed}.",
        "ground_deductions": (
            "{n}. For the following deductions, {ref} does not cite a specific term or condition of my policy: "
            "{items}. The total of these deductions is {total}."
        ),
        "ground_reasons": (
            "{n}. {Ref} gives the following reason for its decision but does not cite a specific term or condition "
            "of my policy: {quoted}."
        ),
        "quote": "The applicable rule states: “{quote}”",
        "request_intro": "I therefore request that you:",
        "req_a_rejected": "reconsider your decision and settle my claim;",
        "req_a_partial": "reconsider these deductions and pay {total};",
        "req_b_reason": "state, for each reason for rejection, the specific term or condition of the policy relied on;",
        "req_b_deduction": "state, for each deduction, the specific term or condition of the policy relied on;",
        "req_c_committee": "confirm that your claims review committee approved the rejection;",
        "req_reply": "reply to me in writing.",
        "labels": "a b c d",
        "enclosures": "Enclosures: {items}.",
        "enc_decision": "a copy of your decision letter",
        "closing": "Yours faithfully,",
        "disclaimer": (
            "Prepared with ClaimSathi, a self-help drafting tool. This is not legal advice. "
            "You send this letter yourself."
        ),
        "english_copy": "English copy",
    },
    "gu": {
        "date": "તારીખ: {date}",
        "to": "પ્રતિ: ફરિયાદ નિવારણ અધિકારી (Grievance Redressal Officer), {insurer}",
        "subject_rejected": "વિષય: પૉલિસી {policy} હેઠળના દાવા {claim} ના અસ્વીકારની સમીક્ષા કરવા વિનંતી",
        "subject_partial": "વિષય: પૉલિસી {policy} હેઠળના દાવા {claim} માં કરેલી કપાતની સમીક્ષા કરવા વિનંતી",
        "salutation": "આદરણીય સાહેબ/મેડમ,",
        "facts_rejected_dated": "મારો દાવો {claim} આપના તા. {date} ના પત્રથી નામંજૂર કરવામાં આવ્યો હતો.",
        "facts_rejected": "મારો દાવો {claim} નામંજૂર કરવામાં આવ્યો હતો.",
        "facts_settled_dated": "મારો દાવો {claim} આપના તા. {date} ના પત્રથી સેટલ કરવામાં આવ્યો હતો.",
        "facts_settled": "મારો દાવો {claim} સેટલ કરવામાં આવ્યો હતો.",
        "amounts_both": "દાવાની રકમ {claimed} હતી અને ચૂકવેલી રકમ {paid} હતી.",
        "amount_claimed": "દાવાની રકમ {claimed} હતી.",
        "ground_deductions": (
            "{n}. નીચેની કપાતો માટે આપના પત્રમાં મારી પૉલિસીની કોઈ ચોક્કસ શરત કે નિયમનો ઉલ્લેખ નથી: {items}. "
            "આ કપાતોની કુલ રકમ {total} છે."
        ),
        "ground_reasons": (
            "{n}. આપના પત્રમાં નિર્ણય માટે નીચેનું કારણ આપેલું છે, પરંતુ મારી પૉલિસીની કોઈ ચોક્કસ શરત કે નિયમનો ઉલ્લેખ નથી: {quoted}."
        ),
        "quote": "લાગુ પડતો નિયમ જણાવે છે: “{quote}”",
        "request_intro": "તેથી હું આપને વિનંતી કરું છું કે:",
        "req_a_rejected": "આપના નિર્ણય પર પુનર્વિચાર કરો અને મારો દાવો ચૂકવો;",
        "req_a_partial": "આ કપાતો પર પુનર્વિચાર કરો અને {total} ચૂકવો;",
        "req_b_reason": "અસ્વીકારના દરેક કારણ માટે, આપે આધાર લીધેલી પૉલિસીની ચોક્કસ શરત કે નિયમ જણાવો;",
        "req_b_deduction": "દરેક કપાત માટે, આપે આધાર લીધેલી પૉલિસીની ચોક્કસ શરત કે નિયમ જણાવો;",
        "req_c_committee": "પુષ્ટિ કરો કે આપની ક્લેમ્સ રિવ્યૂ કમિટીએ આ અસ્વીકારને મંજૂરી આપી હતી;",
        "req_reply": "મને લેખિતમાં જવાબ આપો.",
        "labels": "ક ખ ગ ઘ",
        "enclosures": "બિડાણ: {items}.",
        "enc_decision": "આપના નિર્ણય પત્રની નકલ",
        "closing": "આપનો વિશ્વાસુ,",
        "disclaimer": (
            "ClaimSathi વડે તૈયાર કરેલ, જે જાતે મદદ મેળવવા માટેનું ડ્રાફ્ટિંગ સાધન છે. આ કાનૂની સલાહ નથી. આ પત્ર તમે જાતે મોકલો છો."
        ),
        "english_copy": "અંગ્રેજી નકલ (English copy)",
    },
    "hi": {
        "date": "दिनांक: {date}",
        "to": "सेवा में: शिकायत निवारण अधिकारी (Grievance Redressal Officer), {insurer}",
        "subject_rejected": "विषय: पॉलिसी {policy} के अंतर्गत दावा {claim} की अस्वीकृति की समीक्षा हेतु अनुरोध",
        "subject_partial": "विषय: पॉलिसी {policy} के अंतर्गत दावा {claim} में की गई कटौतियों की समीक्षा हेतु अनुरोध",
        "salutation": "आदरणीय महोदय/महोदया,",
        "facts_rejected_dated": "मेरा दावा {claim} आपके दिनांक {date} के पत्र द्वारा अस्वीकार किया गया था।",
        "facts_rejected": "मेरा दावा {claim} अस्वीकार किया गया था।",
        "facts_settled_dated": "मेरा दावा {claim} आपके दिनांक {date} के पत्र द्वारा निपटाया गया था।",
        "facts_settled": "मेरा दावा {claim} निपटाया गया था।",
        "amounts_both": "दावा की गई राशि {claimed} थी और भुगतान की गई राशि {paid} थी।",
        "amount_claimed": "दावा की गई राशि {claimed} थी।",
        "ground_deductions": (
            "{n}. निम्नलिखित कटौतियों के लिए आपके पत्र में मेरी पॉलिसी की किसी विशिष्ट शर्त या नियम का उल्लेख नहीं है: "
            "{items}। इन कटौतियों का कुल योग {total} है।"
        ),
        "ground_reasons": (
            "{n}. आपके पत्र में निर्णय का निम्नलिखित कारण दिया गया है, लेकिन मेरी पॉलिसी की किसी विशिष्ट शर्त या नियम "
            "का उल्लेख नहीं है: {quoted}।"
        ),
        "quote": "लागू नियम कहता है: “{quote}”",
        "request_intro": "अतः मेरा आपसे अनुरोध है कि:",
        "req_a_rejected": "अपने निर्णय पर पुनर्विचार करें और मेरे दावे का भुगतान करें;",
        "req_a_partial": "इन कटौतियों पर पुनर्विचार करें और {total} का भुगतान करें;",
        "req_b_reason": "अस्वीकृति के प्रत्येक कारण के लिए, पॉलिसी की वह विशिष्ट शर्त या नियम बताएँ जिस पर आपने भरोसा किया;",
        "req_b_deduction": "प्रत्येक कटौती के लिए, पॉलिसी की वह विशिष्ट शर्त या नियम बताएँ जिस पर आपने भरोसा किया;",
        "req_c_committee": "पुष्टि करें कि आपकी क्लेम्स रिव्यू कमेटी ने इस अस्वीकृति को स्वीकृति दी थी;",
        "req_reply": "मुझे लिखित में उत्तर दें।",
        "labels": "क ख ग घ",
        "enclosures": "संलग्नक: {items}।",
        "enc_decision": "आपके निर्णय पत्र की प्रति",
        "closing": "भवदीय,",
        "disclaimer": (
            "ClaimSathi से तैयार किया गया, जो स्वयं सहायता के लिए एक ड्राफ़्टिंग टूल है। यह कानूनी सलाह नहीं है। यह पत्र आप स्वयं भेजते हैं।"
        ),
        "english_copy": "अंग्रेज़ी प्रति (English copy)",
    },
}

# Stage-1 ground paragraphs for rule findings in Gujarati and Hindi (English is RULE_GROUND_TEXT in the service).
RULE_GROUNDS: dict[str, dict[str, str]] = {
    "gu": {
        "RULE-MC-02": "મારો દાવો સંપૂર્ણપણે નામંજૂર કરવામાં આવ્યો હતો. લાગુ પડતા નિયમ મુજબ સંપૂર્ણ અસ્વીકાર માટે આપની "
        "ક્લેમ્સ રિવ્યૂ કમિટીની મંજૂરી જરૂરી છે.",
        "RULE-MC-03": "આ દાખલ થવા પહેલાં મારી પૉલિસીમાં 60 મહિનાથી વધુ સતત કવર હતું, તેથી સ્થાપિત છેતરપિંડી સિવાય "
        "માહિતી ન જણાવવાના (non-disclosure) કારણે આ દાવાને પડકારી શકાય નહીં.",
        "RULE-MC-05": "જો હૉસ્પિટલના કોઈ દસ્તાવેજો ખૂટતા હોય, તો લાગુ પડતા નિયમ મુજબ આપે તે સીધા હૉસ્પિટલ પાસેથી મેળવવા જોઈએ.",
    },
    "hi": {
        "RULE-MC-02": "मेरा दावा पूरी तरह अस्वीकार किया गया था। लागू नियम के अनुसार पूर्ण अस्वीकृति के लिए आपकी क्लेम्स "
        "रिव्यू कमेटी की स्वीकृति आवश्यक है।",
        "RULE-MC-03": "इस भर्ती से पहले मेरी पॉलिसी में 60 महीने से अधिक का निरंतर कवर था, इसलिए स्थापित धोखाधड़ी के "
        "अलावा जानकारी न देने (non-disclosure) के आधार पर इस दावे पर आपत्ति नहीं की जा सकती।",
        "RULE-MC-05": "यदि अस्पताल के कोई दस्तावेज़ कम हैं, तो लागू नियम के अनुसार आपको उन्हें सीधे अस्पताल से प्राप्त करना चाहिए।",
    },
}

# Enclosure names in Gujarati and Hindi; keys match EVIDENCE_LABELS_EN.
EVIDENCE_LABELS: dict[str, dict[str, str]] = {
    "gu": {
        "decision_letter": "વીમા કંપનીનો નિર્ણય પત્ર",
        "policy_schedule": "મારું પૉલિસી શેડ્યૂલ",
        "policy_wording": "પૉલિસીની શરતો (પૉલિસી વર્ડિંગ)",
        "discharge_summary": "ડિસ્ચાર્જ સારાંશ",
        "final_bill": "હૉસ્પિટલનું અંતિમ બિલ",
        "doctor_certificate_first_diagnosis": "પહેલા નિદાનની તારીખ દર્શાવતું મારા સારવાર કરનાર ડૉક્ટરનું પ્રમાણપત્ર",
        "previous_policy_schedules": "સતત કવર દર્શાવતા મારા અગાઉના પૉલિસી શેડ્યૂલ",
        "hospital_tariff_sheet": "હૉસ્પિટલની ટેરિફ શીટ",
        "room_category_record": "મારી રૂમ કેટેગરીનો રેકોર્ડ",
        "itemised_hospital_bill": "વિગતવાર હૉસ્પિટલ બિલ",
        "treating_doctor_note_necessity": "સારવાર શા માટે જરૂરી હતી તે અંગે મારા સારવાર કરનાર ડૉક્ટરની નોંધ",
        "proof_documents_submitted": "મેં જમા કરાવેલા દસ્તાવેજોનો પુરાવો",
        "intimation_proof": "મેં વીમા કંપનીને ક્યારે જાણ કરી તેનો પુરાવો",
        "premium_payment_receipts": "મારી પ્રીમિયમ ચુકવણીની રસીદો",
    },
    "hi": {
        "decision_letter": "बीमा कंपनी का निर्णय पत्र",
        "policy_schedule": "मेरा पॉलिसी शेड्यूल",
        "policy_wording": "पॉलिसी की शर्तें (पॉलिसी वर्डिंग)",
        "discharge_summary": "डिस्चार्ज सारांश",
        "final_bill": "अस्पताल का अंतिम बिल",
        "doctor_certificate_first_diagnosis": "पहले निदान की तारीख बताने वाला मेरे इलाज करने वाले डॉक्टर का प्रमाणपत्र",
        "previous_policy_schedules": "निरंतर कवर दिखाने वाले मेरे पिछले पॉलिसी शेड्यूल",
        "hospital_tariff_sheet": "अस्पताल की टैरिफ़ शीट",
        "room_category_record": "मेरी रूम श्रेणी का रिकॉर्ड",
        "itemised_hospital_bill": "मदवार अस्पताल बिल",
        "treating_doctor_note_necessity": "इलाज क्यों ज़रूरी था, इस पर मेरे इलाज करने वाले डॉक्टर का नोट",
        "proof_documents_submitted": "मेरे द्वारा जमा किए गए दस्तावेज़ों का प्रमाण",
        "intimation_proof": "मैंने बीमा कंपनी को कब सूचित किया, इसका प्रमाण",
        "premium_payment_receipts": "मेरी प्रीमियम भुगतान रसीदें",
    },
}
