"""
Default schema templates for each crisis nature.
Used by seed_default_schema.py and by admin/events.py when auto-seeding new events.

All option labels carry all 6 UN languages. Where a translation was not available
at authoring time the English value is used as a safe fallback — coordinators can
update labels via the admin schema editor once deployed.
"""

from __future__ import annotations


def _mk_label(**kwargs: str) -> dict[str, str]:
    """Return a label dict with all 6 UN languages, falling back to English."""
    en = kwargs.get("en", "")
    return {
        "en": en,
        "fr": kwargs.get("fr", en),
        "ar": kwargs.get("ar", en),
        "sw": kwargs.get("sw", en),
        "es": kwargs.get("es", en),
        "zh": kwargs.get("zh", en),
    }


# ---------------------------------------------------------------------------
# System fields (shared across all crisis types)
# ---------------------------------------------------------------------------

SYSTEM_FIELDS: dict = {
    "damage_level": {
        "values_locked": True,
        "type": "select",
        "labels": _mk_label(
            en="What is the damage level?",
            fr="Quel est le niveau de dommages ?",
            ar="ما مستوى الضرر؟",
            sw="Kiwango cha uharibifu ni kipi?",
            es="¿Cuál es el nivel de daño?",
            zh="损坏程度如何？",
        ),
        "options": {
            "minimal": _mk_label(
                en="Minimal — structurally sound, cosmetic damage only",
                fr="Minimal — structure solide, dommages cosmétiques uniquement",
                ar="أدنى — الهيكل سليم، أضرار شكلية فقط",
                sw="Kidogo — muundo imara, uharibifu wa nje tu",
                es="Mínimo — estructuralmente sólido, solo daños cosméticos",
                zh="轻微——结构完好，仅外观损坏",
            ),
            "partial": _mk_label(
                en="Partial — repairable, remains usable with caution",
                fr="Partiel — réparable, reste utilisable avec précaution",
                ar="جزئي — قابل للإصلاح، لا يزال صالحاً للاستخدام بحذر",
                sw="Sehemu — inaweza kukarabatiwa, bado inaweza kutumika kwa tahadhari",
                es="Parcial — reparable, sigue siendo utilizable con precaución",
                zh="部分——可修复，谨慎使用仍可使用",
            ),
            "complete": _mk_label(
                en="Complete — structurally unsafe or destroyed",
                fr="Complet — structurellement dangereux ou détruit",
                ar="كامل — غير آمن هيكلياً أو مدمر",
                sw="Kamili — si salama kimuundo au imeharibiwa kabisa",
                es="Completo — estructuralmente inseguro o destruido",
                zh="完全——结构不安全或已被摧毁",
            ),
        },
    },
    "infrastructure_type": {
        "values_locked": False,
        "type": "multiselect",
        "min_selections": 1,
        "labels": _mk_label(
            en="What type of infrastructure is affected? (select all that apply)",
            fr="Quel type d'infrastructure est affecté ? (sélectionnez tout ce qui s'applique)",
            ar="ما نوع البنية التحتية المتضررة؟ (حدد كل ما ينطبق)",
            sw="Miundombinu ya aina gani imeathiriwa? (chagua yote yanayohusika)",
            es="¿Qué tipo de infraestructura está afectada? (seleccione todo lo que corresponda)",
            zh="哪类基础设施受到影响？（选择所有适用项）",
        ),
        "options": [
            {"value": "residential",  "labels": _mk_label(en="Residential",                         fr="Résidentiel",                ar="سكني",         sw="Makazi",                 es="Residencial",             zh="住宅")},
            {"value": "commercial",   "labels": _mk_label(en="Commercial",                          fr="Commercial",                 ar="تجاري",        sw="Biashara",               es="Comercial",               zh="商业")},
            {"value": "government",   "labels": _mk_label(en="Government / public administration",  fr="Gouvernement / adm. pub.",   ar="حكومي / إدارة", sw="Serikali / utawala",     es="Gobierno / adm. pública", zh="政府/公共行政")},
            {"value": "utility",      "labels": _mk_label(en="Utility (water, power, telecoms)",    fr="Infrastructure (eau, élec.)", ar="مرافق (مياه، طاقة)", sw="Huduma (maji, umeme)", es="Servicios (agua, energía)", zh="公用设施（水、电、通信）")},
            {"value": "transport",    "labels": _mk_label(en="Transport (roads, bridges, ports)",   fr="Transport (routes, ponts)",  ar="نقل (طرق، جسور)", sw="Usafiri (barabara)",   es="Transporte (carreteras)", zh="交通（道路、桥梁）")},
            {"value": "community",    "labels": _mk_label(en="Community (school, clinic, worship)", fr="Communauté (école, clinique)", ar="مجتمعي (مدرسة، عيادة)", sw="Jamii (shule, kliniki)", es="Comunidad (escuela, clínica)", zh="社区（学校、诊所）")},
            {"value": "public_space", "labels": _mk_label(en="Public space (park, market, square)", fr="Espace public (parc, marché)", ar="فضاء عام (حديقة، سوق)", sw="Nafasi ya umma",  es="Espacio público",         zh="公共空间（公园、市场）")},
            {"value": "other",        "labels": _mk_label(en="Other",                               fr="Autre",                      ar="أخرى",         sw="Nyingine",               es="Otro",                    zh="其他")},
        ],
    },
}

# ---------------------------------------------------------------------------
# Custom fields per crisis nature
# ---------------------------------------------------------------------------

_CRISIS_NATURE_FIELD: dict = {
    "id": "crisis_nature",
    "type": "select",
    "required": True,
    "order": 1,
    "labels": _mk_label(
        en="What type of crisis is this?",
        fr="De quel type de crise s'agit-il ?",
        ar="ما نوع هذه الأزمة؟",
        sw="Hii ni aina gani ya msiba?",
        es="¿Qué tipo de crisis es esta?",
        zh="这是哪种类型的危机？",
    ),
    "options": [
        {"value": "flood",      "labels": _mk_label(en="Flood",     fr="Inondation",  ar="فيضان",  sw="Mafuriko",  es="Inundación",  zh="洪水")},
        {"value": "earthquake", "labels": _mk_label(en="Earthquake", fr="Séisme",      ar="زلزال",  sw="Tetemeko",  es="Terremoto",   zh="地震")},
        {"value": "hurricane",  "labels": _mk_label(en="Hurricane",  fr="Ouragan",     ar="إعصار",  sw="Kimbunga",  es="Huracán",     zh="飓风")},
        {"value": "wildfire",   "labels": _mk_label(en="Wildfire",   fr="Incendie",    ar="حريق",   sw="Moto",      es="Incendio",    zh="野火")},
        {"value": "conflict",   "labels": _mk_label(en="Conflict",   fr="Conflit",     ar="نزاع",   sw="Mzozo",     es="Conflicto",   zh="冲突")},
        {"value": "other",      "labels": _mk_label(en="Other",      fr="Autre",       ar="أخرى",   sw="Nyingine",  es="Otro",        zh="其他")},
    ],
}

_DEBRIS_FIELD: dict = {
    "id": "requires_debris_clearing",
    "type": "boolean",
    "required": True,
    "order": 2,
    "labels": _mk_label(
        en="Does this site require debris clearing?",
        fr="Ce site nécessite-t-il un déblayage ?",
        ar="هل يحتاج هذا الموقع إلى إزالة الحطام؟",
        sw="Je, eneo hili linahitaji kusafisha uchafu?",
        es="¿Este sitio requiere limpieza de escombros?",
        zh="该地点是否需要清理废墟？",
    ),
}

_ELECTRICITY_FIELD: dict = {
    "id": "electricity_status",
    "type": "select",
    "required": True,
    "order": 5,
    "labels": _mk_label(
        en="What is the current condition of electricity infrastructure?",
        fr="Quel est l'état actuel des infrastructures électriques ?",
        ar="ما الحال الراهن للبنية التحتية للكهرباء؟",
        sw="Hali ya sasa ya miundombinu ya umeme ni ipi?",
        es="¿Cuál es el estado actual de la infraestructura eléctrica?",
        zh="目前电力基础设施的状况如何？",
    ),
    "options": [
        {"value": "no_damage",  "labels": _mk_label(en="No damage observed",                                  fr="Aucun dommage observé",          ar="لا ضرر ملحوظ",          sw="Hakuna uharibifu",           es="Sin daños observados",           zh="未发现损坏")},
        {"value": "minor",      "labels": _mk_label(en="Minor damage (disruptions, quickly repairable)",       fr="Dommages mineurs",               ar="أضرار طفيفة",           sw="Uharibifu mdogo",            es="Daño menor (reparable)",         zh="轻微损坏（可快速修复）")},
        {"value": "moderate",   "labels": _mk_label(en="Moderate damage (partial outages, needs repairs)",     fr="Dommages modérés",               ar="أضرار معتدلة",          sw="Uharibifu wa wastani",       es="Daño moderado (cortes parciales)", zh="中度损坏（需要维修）")},
        {"value": "severe",     "labels": _mk_label(en="Severe damage (major infrastructure damaged)",         fr="Dommages graves",                ar="أضرار شديدة",           sw="Uharibifu mkubwa",           es="Daño grave",                     zh="严重损坏")},
        {"value": "destroyed",  "labels": _mk_label(en="Completely destroyed (no electricity functioning)",   fr="Complètement détruit",           ar="مدمر تماماً",           sw="Imeharibiwa kabisa",         es="Completamente destruido",        zh="完全摧毁")},
        {"value": "unknown",    "labels": _mk_label(en="Unknown / cannot be assessed",                        fr="Inconnu",                        ar="غير معروف",             sw="Haijulikani",                es="Desconocido",                    zh="未知")},
    ],
}

_HEALTH_FIELD: dict = {
    "id": "health_services",
    "type": "select",
    "required": True,
    "order": 6,
    "labels": _mk_label(
        en="How are health services functioning in your community?",
        fr="Comment fonctionnent les services de santé dans votre communauté ?",
        ar="كيف تعمل الخدمات الصحية في مجتمعك؟",
        sw="Huduma za afya zinafanya kazi vipi katika jamii yako?",
        es="¿Cómo funcionan los servicios de salud en su comunidad?",
        zh="您所在社区的卫生服务运作情况如何？",
    ),
    "options": [
        {"value": "fully_functional",     "labels": _mk_label(en="Fully functional",       fr="Pleinement fonctionnels",    ar="تعمل بالكامل",          sw="Kikamilifu",          es="Plenamente funcionales",   zh="完全正常运行")},
        {"value": "partially_functional", "labels": _mk_label(en="Partially functional",   fr="Partiellement fonctionnels", ar="تعمل جزئياً",           sw="Kwa kiasi",           es="Parcialmente funcionales", zh="部分正常运行")},
        {"value": "largely_disrupted",    "labels": _mk_label(en="Largely disrupted",      fr="Largement perturbés",        ar="مضطربة كبيرة",          sw="Zimevunjika sana",    es="Mayormente interrumpidos", zh="基本中断")},
        {"value": "not_functioning",      "labels": _mk_label(en="Not functioning at all", fr="Ne fonctionnent pas du tout", ar="لا تعمل على الإطلاق",  sw="Hazifanyi kazi",      es="Sin funcionamiento",       zh="完全停止运行")},
        {"value": "unknown",              "labels": _mk_label(en="Unknown",                fr="Inconnu",                    ar="غير معروف",             sw="Haijulikani",         es="Desconocido",              zh="未知")},
    ],
}

_PRESSING_NEEDS_FIELD: dict = {
    "id": "pressing_needs",
    "type": "multiselect",
    "required": True,
    "order": 7,
    "labels": _mk_label(
        en="What are the most pressing needs? (select all that apply)",
        fr="Quels sont les besoins les plus urgents ? (sélectionnez tout ce qui s'applique)",
        ar="ما الاحتياجات الأكثر إلحاحاً؟ (حدد كل ما ينطبق)",
        sw="Mahitaji ya haraka zaidi ni yapi? (chagua yote yanayohusika)",
        es="¿Cuáles son las necesidades más urgentes? (seleccione todo lo que corresponda)",
        zh="最迫切的需求是什么？（选择所有适用项）",
    ),
    "options": [
        {"value": "food_water",        "labels": _mk_label(en="Food and safe drinking water",           fr="Nourriture et eau potable",     ar="الغذاء والمياه الآمنة",      sw="Chakula na maji salama",        es="Alimentos y agua potable",       zh="食物和安全饮用水")},
        {"value": "cash_financial",    "labels": _mk_label(en="Cash or financial assistance",           fr="Aide financière",               ar="مساعدة مالية",               sw="Fedha au msaada wa kifedha",    es="Asistencia económica",           zh="现金或经济援助")},
        {"value": "healthcare",        "labels": _mk_label(en="Healthcare and medicines",               fr="Soins de santé et médicaments", ar="الرعاية الصحية والأدوية",    sw="Huduma za afya na dawa",        es="Atención médica y medicamentos", zh="医疗保健和药品")},
        {"value": "shelter",           "labels": _mk_label(en="Shelter or housing repair",             fr="Abri ou réparation du logement", ar="مأوى أو إصلاح المسكن",      sw="Makazi au ukarabati wa nyumba", es="Refugio o reparación de vivienda", zh="庇护所或住房修缮")},
        {"value": "livelihoods",       "labels": _mk_label(en="Livelihoods and income",                fr="Moyens de subsistance",         ar="سبل المعيشة والدخل",         sw="Riziki na mapato",              es="Medios de vida e ingresos",      zh="生计和收入")},
        {"value": "wash",              "labels": _mk_label(en="Water, sanitation and hygiene",         fr="Eau, assainissement et hygiène", ar="المياه والصرف الصحي",        sw="Maji, usafi wa mazingira",      es="Agua, saneamiento e higiene",    zh="水、卫生和个人卫生")},
        {"value": "basic_services",    "labels": _mk_label(en="Basic services (electricity, roads, schools)", fr="Services de base",         ar="الخدمات الأساسية",           sw="Huduma za msingi",              es="Servicios básicos",              zh="基本服务（电力、道路、学校）")},
        {"value": "protection",        "labels": _mk_label(en="Protection and psychosocial support",   fr="Protection et soutien psychosocial", ar="الحماية والدعم النفسي",  sw="Ulinzi na msaada",              es="Protección y apoyo psicosocial", zh="保护和社会心理支持")},
        {"value": "community_support", "labels": _mk_label(en="Support from authorities / community orgs", fr="Soutien des autorités",     ar="الدعم من السلطات",           sw="Msaada wa mamlaka",             es="Apoyo de autoridades",           zh="来自当局和社区组织的支持")},
        {"value": "other",             "labels": _mk_label(en="Other (please specify)",                fr="Autre (précisez)",              ar="أخرى (يرجى التحديد)",        sw="Nyingine (tafadhali eleza)",    es="Otro (especifique)",             zh="其他（请注明）")},
    ],
}

# ---------------------------------------------------------------------------
# Per-crisis-nature custom field sets
# ---------------------------------------------------------------------------

_FLOOD_CUSTOM_FIELDS: list[dict] = [
    _CRISIS_NATURE_FIELD,
    _DEBRIS_FIELD,
    {
        "id": "water_level",
        "type": "select",
        "required": True,
        "order": 3,
        "labels": _mk_label(
            en="What is the estimated water level at the site?",
            fr="Quel est le niveau d'eau estimé sur le site ?",
            ar="ما مستوى الماء المقدر في الموقع؟",
            sw="Kiwango cha maji kinachofikiriwa kwenye eneo hilo ni kipi?",
            es="¿Cuál es el nivel de agua estimado en el sitio?",
            zh="该地点的估计水位是多少？",
        ),
        "options": [
            {"value": "ankle",   "labels": _mk_label(en="Ankle deep (< 0.5 m)",  fr="À la cheville (< 0,5 m)", ar="مستوى الكاحل",  sw="Kina cha kifundo", es="Hasta el tobillo (< 0,5 m)", zh="踝深（< 0.5 米）")},
            {"value": "knee",    "labels": _mk_label(en="Knee deep (0.5–1 m)",   fr="Au genou (0,5–1 m)",      ar="مستوى الركبة",  sw="Kina cha goti",    es="Hasta la rodilla (0,5–1 m)", zh="膝深（0.5–1 米）")},
            {"value": "waist",   "labels": _mk_label(en="Waist deep (1–2 m)",    fr="À la taille (1–2 m)",     ar="مستوى الخصر",   sw="Kina cha kiuno",   es="Hasta la cintura (1–2 m)",   zh="腰深（1–2 米）")},
            {"value": "above",   "labels": _mk_label(en="Above head (> 2 m)",    fr="Au-dessus de la tête",    ar="فوق الرأس",     sw="Juu ya kichwa",    es="Por encima de la cabeza",    zh="超过头顶（> 2 米）")},
            {"value": "receded", "labels": _mk_label(en="Water has receded",      fr="L'eau s'est retirée",    ar="تراجعت المياه", sw="Maji yamepungua",  es="El agua ha retrocedido",     zh="水已退去")},
        ],
    },
    {
        "id": "road_passable",
        "type": "boolean",
        "required": False,
        "order": 4,
        "labels": _mk_label(
            en="Is the nearest road passable?",
            fr="La route la plus proche est-elle praticable ?",
            ar="هل الطريق الأقرب صالح للمرور؟",
            sw="Je, barabara iliyo karibu inapitika?",
            es="¿Es transitable la carretera más cercana?",
            zh="最近的道路是否可通行？",
        ),
    },
    _ELECTRICITY_FIELD,
    _HEALTH_FIELD,
    _PRESSING_NEEDS_FIELD,
]

_EARTHQUAKE_CUSTOM_FIELDS: list[dict] = [
    _CRISIS_NATURE_FIELD,
    _DEBRIS_FIELD,
    {
        "id": "people_trapped",
        "type": "boolean",
        "required": False,
        "order": 3,
        "labels": _mk_label(
            en="Are people trapped in or near the structure?",
            fr="Des personnes sont-elles piégées dans ou près de la structure ?",
            ar="هل توجد أشخاص محاصرون في البنية أو بالقرب منها؟",
            sw="Je, kuna watu waliokwama ndani au karibu na muundo?",
            es="¿Hay personas atrapadas en o cerca de la estructura?",
            zh="有人被困在建筑物内或附近吗？",
        ),
    },
    {
        "id": "aftershock_damage",
        "type": "boolean",
        "required": False,
        "order": 4,
        "labels": _mk_label(
            en="Has aftershock damage been observed?",
            fr="Des dommages dus aux répliques ont-ils été observés ?",
            ar="هل لوحظ ضرر من الهزات الارتدادية؟",
            sw="Je, uharibifu wa mshtuko wa pili umeonekana?",
            es="¿Se han observado daños por réplicas?",
            zh="是否观察到余震造成的损害？",
        ),
    },
    _ELECTRICITY_FIELD,
    _HEALTH_FIELD,
    _PRESSING_NEEDS_FIELD,
]

_CONFLICT_CUSTOM_FIELDS: list[dict] = [
    _CRISIS_NATURE_FIELD,
    _DEBRIS_FIELD,
    {
        "id": "area_accessible",
        "type": "boolean",
        "required": False,
        "order": 3,
        "labels": _mk_label(
            en="Is the affected area accessible?",
            fr="La zone touchée est-elle accessible ?",
            ar="هل المنطقة المتضررة في متناول الوصول؟",
            sw="Je, eneo lililoathiriwa linaweza kufikiwa?",
            es="¿Es accesible el área afectada?",
            zh="受影响地区是否可进入？",
        ),
    },
    {
        "id": "civilian_displacement",
        "type": "select",
        "required": False,
        "order": 4,
        "labels": _mk_label(
            en="Estimate of civilian displacement",
            fr="Estimation du déplacement de civils",
            ar="تقدير نزوح المدنيين",
            sw="Tathmini ya uhamishaji wa raia",
            es="Estimación del desplazamiento civil",
            zh="平民流离失所估计",
        ),
        "options": [
            {"value": "none",     "labels": _mk_label(en="None observed",       fr="Aucun observé",        ar="لم يُلاحظ أي",    sw="Hakuna iliyoonekana", es="Ninguno observado",    zh="未观察到")},
            {"value": "few",      "labels": _mk_label(en="A few families",      fr="Quelques familles",    ar="عائلات قليلة",    sw="Familia chache",      es="Algunas familias",     zh="少数家庭")},
            {"value": "dozens",   "labels": _mk_label(en="Dozens of people",    fr="Des dizaines",         ar="عشرات الأشخاص",  sw="Watu kadhaa",         es="Decenas de personas",  zh="数十人")},
            {"value": "hundreds", "labels": _mk_label(en="Hundreds of people",  fr="Des centaines",        ar="مئات الأشخاص",   sw="Mamia ya watu",       es="Cientos de personas",  zh="数百人")},
        ],
    },
    _ELECTRICITY_FIELD,
    _HEALTH_FIELD,
    _PRESSING_NEEDS_FIELD,
]

# Generic / hurricane / wildfire get the same base UNDP fields
_GENERIC_CUSTOM_FIELDS: list[dict] = [
    _CRISIS_NATURE_FIELD,
    _DEBRIS_FIELD,
    _ELECTRICITY_FIELD,
    _HEALTH_FIELD,
    _PRESSING_NEEDS_FIELD,
]

# ---------------------------------------------------------------------------
# Public mapping: crisis_nature → full schema body
# ---------------------------------------------------------------------------

SCHEMAS_BY_NATURE: dict[str, dict] = {
    "flood":     {"system_fields": SYSTEM_FIELDS, "custom_fields": _FLOOD_CUSTOM_FIELDS},
    "earthquake": {"system_fields": SYSTEM_FIELDS, "custom_fields": _EARTHQUAKE_CUSTOM_FIELDS},
    "conflict":  {"system_fields": SYSTEM_FIELDS, "custom_fields": _CONFLICT_CUSTOM_FIELDS},
    "hurricane": {"system_fields": SYSTEM_FIELDS, "custom_fields": _GENERIC_CUSTOM_FIELDS},
    "wildfire":  {"system_fields": SYSTEM_FIELDS, "custom_fields": _GENERIC_CUSTOM_FIELDS},
    "generic":   {"system_fields": SYSTEM_FIELDS, "custom_fields": _GENERIC_CUSTOM_FIELDS},
    "other":     {"system_fields": SYSTEM_FIELDS, "custom_fields": _GENERIC_CUSTOM_FIELDS},
}


def get_default_schema(crisis_nature: str) -> dict:
    """Return the default schema body for the given crisis nature."""
    return SCHEMAS_BY_NATURE.get(crisis_nature.lower(), SCHEMAS_BY_NATURE["generic"])
