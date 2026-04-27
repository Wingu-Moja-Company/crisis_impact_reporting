"""All user-facing bot strings in the 6 official UN languages."""

STRINGS: dict[str, dict[str, str]] = {
    "welcome": {
        "en": "Welcome to the Crisis Damage Reporter. Send a photo of the damage to begin.",
        "ar": "مرحبًا بك في نظام الإبلاغ عن أضرار الأزمات. أرسل صورة للضرر للبدء.",
        "fr": "Bienvenue sur le système de signalement des dommages de crise. Envoyez une photo des dégâts pour commencer.",
        "zh": "欢迎使用危机损害报告系统。请发送一张受损照片以开始报告。",
        "ru": "Добро пожаловать в систему отчётов об ущербе в кризисных ситуациях. Отправьте фото повреждений, чтобы начать.",
        "es": "Bienvenido al sistema de reporte de daños en crisis. Envíe una foto del daño para comenzar.",
    },
    "send_photo": {
        "en": "Please send a photo of the damaged structure.",
        "ar": "يرجى إرسال صورة للهيكل المتضرر.",
        "fr": "Veuillez envoyer une photo de la structure endommagée.",
        "zh": "请发送受损建筑的照片。",
        "ru": "Пожалуйста, отправьте фото повреждённого строения.",
        "es": "Por favor envíe una foto de la estructura dañada.",
    },
    "photo_received": {
        "en": "Photo received. Now select the location of the damage.",
        "ar": "تم استلام الصورة. الآن حدد موقع الضرر.",
        "fr": "Photo reçue. Sélectionnez maintenant l'emplacement des dommages.",
        "zh": "照片已收到。请选择受损位置。",
        "ru": "Фото получено. Теперь укажите местоположение повреждений.",
        "es": "Foto recibida. Ahora seleccione la ubicación del daño.",
    },
    "send_location": {
        "en": (
            "📍 Where is the damage?\n\n"
            "Best: tap the 📎 attachment button → Location to share your GPS.\n\n"
            "Or type a street address, landmark, or neighbourhood "
            "(e.g. \"Near Mathare Market\").\n\n"
            "Have a 3-word location code? Type it like: filled.count.soap"
        ),
        "ar": (
            "📍 أين الضرر؟\n\n"
            "الأفضل: اضغط على زر المرفقات 📎 ← الموقع لمشاركة نظام تحديد المواقع.\n\n"
            "أو اكتب عنوانًا أو معلمًا أو حيًا (مثال: \"بالقرب من سوق ماثاري\").\n\n"
            "هل لديك رمز موقع من ثلاث كلمات؟ اكتبه هكذا: filled.count.soap"
        ),
        "fr": (
            "📍 Où se trouvent les dégâts ?\n\n"
            "Idéal : appuyez sur 📎 Pièce jointe → Localisation pour partager votre GPS.\n\n"
            "Ou tapez une adresse, un lieu repère ou un quartier "
            "(ex. « Près du marché de Mathare »).\n\n"
            "Vous avez un code à 3 mots ? Tapez-le ainsi : filled.count.soap"
        ),
        "zh": (
            "📍 损坏在哪里？\n\n"
            "最佳方式：点击 📎 附件按钮 → 位置，分享您的 GPS 位置。\n\n"
            "或输入街道地址、地标或社区名称（例如：马萨雷市场附近）。\n\n"
            "有三词定位码？请这样输入：filled.count.soap"
        ),
        "ru": (
            "📍 Где находится ущерб?\n\n"
            "Лучший способ: нажмите 📎 Вложения → Геолокация, чтобы поделиться GPS.\n\n"
            "Или введите адрес, ориентир или район "
            "(например: «Рядом с рынком Матаре»).\n\n"
            "Есть код из трёх слов? Введите его так: filled.count.soap"
        ),
        "es": (
            "📍 ¿Dónde están los daños?\n\n"
            "Lo mejor: toque el botón 📎 adjuntar → Ubicación para compartir su GPS.\n\n"
            "O escriba una dirección, punto de referencia o barrio "
            "(ej. \"Cerca del Mercado Mathare\").\n\n"
            "¿Tiene un código de 3 palabras? Escríbalo así: filled.count.soap"
        ),
    },
    "select_damage_level": {
        "en": "Select the level of damage:",
        "ar": "حدد مستوى الضرر:",
        "fr": "Sélectionnez le niveau de dommage :",
        "zh": "请选择损坏程度：",
        "ru": "Выберите уровень повреждения:",
        "es": "Seleccione el nivel de daño:",
    },
    "select_infra_type": {
        "en": "Select the type of infrastructure (choose all that apply):",
        "ar": "حدد نوع البنية التحتية (اختر كل ما ينطبق):",
        "fr": "Sélectionnez le type d'infrastructure (choisissez tout ce qui s'applique) :",
        "zh": "请选择基础设施类型（可多选）：",
        "ru": "Выберите тип инфраструктуры (выберите все подходящие):",
        "es": "Seleccione el tipo de infraestructura (elija todas las que correspondan):",
    },
    "select_crisis_nature": {
        "en": "What is the nature of the crisis?",
        "ar": "ما طبيعة الأزمة؟",
        "fr": "Quelle est la nature de la crise ?",
        "zh": "危机的性质是什么？",
        "ru": "Какова природа кризиса?",
        "es": "¿Cuál es la naturaleza de la crisis?",
    },
    "debris_question": {
        "en": "Is there debris requiring clearing?",
        "ar": "هل توجد حطام يحتاج إلى إزالة؟",
        "fr": "Y a-t-il des débris à déblayer ?",
        "zh": "是否有需要清理的废墟？",
        "ru": "Требуется ли расчистка завалов?",
        "es": "¿Hay escombros que requieran limpieza?",
    },
    "location_found": {
        "en": "📍 Located: {place}. Continuing…",
        "ar": "📍 تم تحديد الموقع: {place}. جارٍ المتابعة…",
        "fr": "📍 Localisé : {place}. Poursuite…",
        "zh": "📍 已定位：{place}。继续…",
        "ru": "📍 Местоположение найдено: {place}. Продолжаем…",
        "es": "📍 Ubicado: {place}. Continuando…",
    },
    "location_not_found": {
        "en": "📍 Couldn't find \"{query}\" on the map — saved as a text description. Continuing…",
        "ar": "📍 لم يتم العثور على \"{query}\" على الخريطة — تم حفظه كوصف نصي. جارٍ المتابعة…",
        "fr": "📍 \"{query}\" introuvable sur la carte — enregistré comme description. Poursuite…",
        "zh": "📍 在地图上找不到 {query} — 已保存为文字描述。继续…",
        "ru": "📍 \"{query}\" не найдено на карте — сохранено как текстовое описание. Продолжаем…",
        "es": "📍 No se encontró \"{query}\" en el mapa — guardado como descripción. Continuando…",
    },
    "yes": {
        "en": "Yes", "ar": "نعم", "fr": "Oui", "zh": "是", "ru": "Да", "es": "Sí",
    },
    "no": {
        "en": "No", "ar": "لا", "fr": "Non", "zh": "否", "ru": "Нет", "es": "No",
    },
    "confirm": {
        "en": "✅ Report submitted! ID: {report_id}\nView on map: {map_url}",
        "ar": "✅ تم إرسال التقرير! المعرّف: {report_id}\nعرض على الخريطة: {map_url}",
        "fr": "✅ Rapport soumis ! ID : {report_id}\nVoir sur la carte : {map_url}",
        "zh": "✅ 报告已提交！编号：{report_id}\n在地图上查看：{map_url}",
        "ru": "✅ Отчёт отправлен! ID: {report_id}\nПосмотреть на карте: {map_url}",
        "es": "✅ ¡Informe enviado! ID: {report_id}\nVer en el mapa: {map_url}",
    },
    "badge_awarded": {
        "en": "🏅 New badge earned: {badge_name}",
        "ar": "🏅 تم كسب شارة جديدة: {badge_name}",
        "fr": "🏅 Nouveau badge obtenu : {badge_name}",
        "zh": "🏅 获得新徽章：{badge_name}",
        "ru": "🏅 Получена новая награда: {badge_name}",
        "es": "🏅 ¡Nueva insignia obtenida: {badge_name}!",
    },
    "confirm_no_url": {
        "en": "✅ Report submitted! ID: {report_id}",
        "ar": "✅ تم إرسال التقرير! المعرّف: {report_id}",
        "fr": "✅ Rapport soumis ! ID : {report_id}",
        "zh": "✅ 报告已提交！编号：{report_id}",
        "ru": "✅ Отчёт отправлен! ID: {report_id}",
        "es": "✅ ¡Informe enviado! ID: {report_id}",
    },
    # Dynamic schema navigation keys (added for schema-driven form)
    "schema_unavailable": {
        "en": "⚠️ Form schema could not be loaded — using simplified form. Some questions may be missing.",
        "ar": "⚠️ تعذّر تحميل نموذج الاستمارة — سيتم استخدام نموذج مبسّط. قد تكون بعض الأسئلة مفقودة.",
        "fr": "⚠️ Le schéma du formulaire n'a pas pu être chargé — formulaire simplifié utilisé. Certaines questions peuvent manquer.",
        "zh": "⚠️ 无法加载表单架构——将使用简化表单。部分问题可能缺失。",
        "ru": "⚠️ Схема формы не загружена — используется упрощённая форма. Некоторые вопросы могут отсутствовать.",
        "es": "⚠️ No se pudo cargar el esquema del formulario — usando formulario simplificado. Algunas preguntas pueden faltar.",
    },
    "field_skip": {
        "en": "This question is optional — tap Skip to continue without answering.",
        "ar": "هذا السؤال اختياري — اضغط تخطى للمتابعة دون الإجابة.",
        "fr": "Cette question est facultative — appuyez sur Passer pour continuer sans répondre.",
        "zh": "此问题为可选项——点击「跳过」可不作回答直接继续。",
        "ru": "Этот вопрос необязателен — нажмите «Пропустить», чтобы продолжить без ответа.",
        "es": "Esta pregunta es opcional — toque Omitir para continuar sin responder.",
    },
    "field_select_min_one": {
        "en": "Please select at least one option before continuing.",
        "ar": "يرجى اختيار خيار واحد على الأقل قبل المتابعة.",
        "fr": "Veuillez sélectionner au moins une option avant de continuer.",
        "zh": "请在继续前至少选择一个选项。",
        "ru": "Пожалуйста, выберите хотя бы один вариант перед продолжением.",
        "es": "Por favor seleccione al menos una opción antes de continuar.",
    },
    "field_required": {
        "en": "This field is required — please make a selection.",
        "ar": "هذا الحقل مطلوب — يرجى تحديد خيار.",
        "fr": "Ce champ est obligatoire — veuillez faire un choix.",
        "zh": "此字段为必填项——请进行选择。",
        "ru": "Это поле обязательно — пожалуйста, сделайте выбор.",
        "es": "Este campo es obligatorio — por favor haga una selección.",
    },
    "field_invalid_number": {
        "en": "Please enter a valid number.",
        "ar": "يرجى إدخال رقم صحيح.",
        "fr": "Veuillez entrer un nombre valide.",
        "zh": "请输入有效数字。",
        "ru": "Пожалуйста, введите корректное число.",
        "es": "Por favor ingrese un número válido.",
    },
    "error_generic": {
        "en": "Something went wrong. Please try again with /start.",
        "ar": "حدث خطأ ما. يرجى المحاولة مجددًا باستخدام /start.",
        "fr": "Une erreur s'est produite. Veuillez réessayer avec /start.",
        "zh": "出现错误，请使用 /start 重试。",
        "ru": "Что-то пошло не так. Попробуйте ещё раз с /start.",
        "es": "Algo salió mal. Por favor intente de nuevo con /start.",
    },
    # UNDP Appendix 1 questions
    "electricity_question": {
        "en": "What is the current condition of electricity infrastructure in your community following the crisis?",
        "ar": "ما هي الحالة الراهنة للبنية التحتية للكهرباء في مجتمعك في أعقاب الأزمة؟",
        "fr": "Quel est l'état actuel des infrastructures électriques dans votre communauté suite à la crise ?",
        "zh": "危机发生后，您所在社区的电力基础设施目前状况如何？",
        "ru": "Каково текущее состояние электроснабжения в вашем сообществе после кризиса?",
        "es": "¿Cuál es el estado actual de la infraestructura eléctrica en su comunidad tras la crisis?",
    },
    "health_question": {
        "en": "How would you rate the overall functioning of health services in your community since the event?",
        "ar": "كيف تقيّم الأداء العام للخدمات الصحية في مجتمعك منذ وقوع الحدث؟",
        "fr": "Comment évalueriez-vous le fonctionnement global des services de santé dans votre communauté depuis l'événement ?",
        "zh": "自事件发生以来，您如何评价您所在社区卫生服务的总体运作情况？",
        "ru": "Как бы вы оценили общее функционирование медицинских услуг в вашем сообществе после события?",
        "es": "¿Cómo calificaría el funcionamiento general de los servicios de salud en su comunidad desde el evento?",
    },
    "pressing_needs_question": {
        "en": "What are the most pressing needs? (choose all that apply)",
        "ar": "ما هي الاحتياجات الأكثر إلحاحاً؟ (اختر كل ما ينطبق)",
        "fr": "Quels sont les besoins les plus pressants ? (choisissez tout ce qui s'applique)",
        "zh": "最迫切的需求是什么？（可多选）",
        "ru": "Каковы наиболее насущные потребности? (выберите все подходящие)",
        "es": "¿Cuáles son las necesidades más urgentes? (elija todas las que correspondan)",
    },
    # Electricity status options
    "elec_no_damage":  {"en": "No damage observed",                    "ar": "لا يوجد ضرر",           "fr": "Aucun dommage",                "zh": "无损坏",         "ru": "Повреждений нет",          "es": "Sin daños"},
    "elec_minor":      {"en": "Minor damage (quick repair)",            "ar": "ضرر طفيف (إصلاح سريع)", "fr": "Dommages mineurs (réparation rapide)", "zh": "轻微损坏（可快速修复）","ru": "Незначительный ущерб",   "es": "Daño menor (reparación rápida)"},
    "elec_moderate":   {"en": "Moderate damage (partial outages)",      "ar": "ضرر معتدل (انقطاعات جزئية)","fr": "Dommages modérés (pannes partielles)","zh": "中等损坏（部分停电）","ru": "Умеренный ущерб",       "es": "Daño moderado (cortes parciales)"},
    "elec_severe":     {"en": "Severe damage (prolonged outages)",      "ar": "ضرر شديد (انقطاعات مطوّلة)","fr": "Dommages graves (pannes prolongées)","zh": "严重损坏（长时间停电）","ru": "Серьёзный ущерб",     "es": "Daño grave (cortes prolongados)"},
    "elec_destroyed":  {"en": "Completely destroyed",                   "ar": "مدمّر كلياً",           "fr": "Complètement détruit",         "zh": "完全损毁",       "ru": "Полностью разрушено",       "es": "Completamente destruido"},
    "elec_unknown":    {"en": "Unknown/cannot be assessed",             "ar": "غير معروف / لا يمكن تقييمه","fr": "Inconnu / ne peut être évalué","zh": "未知/无法评估", "ru": "Неизвестно / не поддаётся оценке","es": "Desconocido/no evaluable"},
    # Health services options
    "health_fully":    {"en": "Fully functional",    "ar": "تعمل بالكامل",    "fr": "Pleinement opérationnel", "zh": "完全正常运作", "ru": "Полностью функционирует", "es": "Completamente funcional"},
    "health_partially":{"en": "Partially functional","ar": "تعمل جزئياً",     "fr": "Partiellement opérationnel","zh": "部分正常运作","ru": "Частично функционирует",  "es": "Parcialmente funcional"},
    "health_disrupted":{"en": "Largely disrupted",   "ar": "مضطربة إلى حد كبير","fr": "Largement perturbé",    "zh": "大部分中断",   "ru": "В значительной мере нарушено","es": "En gran parte interrumpido"},
    "health_none":     {"en": "Not functioning at all","ar": "لا تعمل إطلاقاً","fr": "Totalement à l'arrêt",  "zh": "完全无法运作", "ru": "Не функционирует совсем", "es": "No funciona en absoluto"},
    "health_unknown":  {"en": "Unknown",              "ar": "غير معروف",       "fr": "Inconnu",                "zh": "未知",         "ru": "Неизвестно",              "es": "Desconocido"},
    # Pressing needs options
    "needs_food_water":        {"en": "Food & safe drinking water",           "ar": "الغذاء والمياه الآمنة",        "fr": "Nourriture et eau potable",        "zh": "食物和饮用水",         "ru": "Питание и вода",               "es": "Alimentos y agua potable"},
    "needs_cash_financial":    {"en": "Cash or financial assistance",         "ar": "مساعدة نقدية أو مالية",        "fr": "Aide en espèces ou financière",    "zh": "现金或财务援助",       "ru": "Денежная помощь",              "es": "Asistencia económica"},
    "needs_healthcare":        {"en": "Healthcare & essential medicines",     "ar": "الرعاية الصحية والأدوية",       "fr": "Soins et médicaments essentiels",  "zh": "医疗保健和基本药物",   "ru": "Медицина и лекарства",         "es": "Salud y medicamentos"},
    "needs_shelter":           {"en": "Shelter, housing or accommodation",    "ar": "المأوى أو السكن المؤقت",        "fr": "Abri, logement ou hébergement",    "zh": "庇护所或住所",         "ru": "Жильё и временное размещение", "es": "Refugio o alojamiento"},
    "needs_livelihoods":       {"en": "Restoration of livelihoods",          "ar": "استعادة سبل العيش",             "fr": "Rétablissement des moyens de subsistance","zh": "恢复生计",     "ru": "Восстановление средств к жизни","es": "Restauración de medios de vida"},
    "needs_wash":              {"en": "Water, sanitation & hygiene",         "ar": "المياه والصرف الصحي",           "fr": "Eau, assainissement et hygiène",   "zh": "供水、卫生和洁净",     "ru": "Водоснабжение и санитария",    "es": "Agua, saneamiento e higiene"},
    "needs_basic_services":    {"en": "Basic services & infrastructure",     "ar": "الخدمات الأساسية والبنية التحتية","fr": "Services de base et infrastructures","zh": "基本服务和基础设施", "ru": "Базовые услуги и инфраструктура","es": "Servicios básicos e infraestructura"},
    "needs_protection":        {"en": "Protection & psychosocial support",   "ar": "الحماية والدعم النفسي",         "fr": "Protection et soutien psychosocial","zh": "保护和心理社会支持",   "ru": "Защита и психосоциальная помощь","es": "Protección y apoyo psicosocial"},
    "needs_community_support": {"en": "Support from local authorities",      "ar": "دعم السلطات المحلية",           "fr": "Soutien des autorités locales",    "zh": "当地当局支持",         "ru": "Поддержка местных властей",    "es": "Apoyo de autoridades locales"},
    "needs_other":             {"en": "Other, please specify",               "ar": "أخرى، يرجى التحديد",            "fr": "Autre, précisez",                  "zh": "其他，请说明",         "ru": "Другое (укажите)",             "es": "Otro, especifique"},
    # Damage level labels
    "damage_minimal": {
        "en": "Minimal",
        "ar": "أدنى",
        "fr": "Minimal",
        "zh": "轻微",
        "ru": "Минимальный",
        "es": "Mínimo",
    },
    "damage_partial": {
        "en": "Partial",
        "ar": "جزئي",
        "fr": "Partiel",
        "zh": "部分",
        "ru": "Частичный",
        "es": "Parcial",
    },
    "damage_complete": {
        "en": "Complete",
        "ar": "كامل",
        "fr": "Complet",
        "zh": "完全",
        "ru": "Полный",
        "es": "Completo",
    },
    # Infrastructure type labels
    "infra_residential":  {"en": "🏠 Residential", "ar": "🏠 سكني", "fr": "🏠 Résidentiel", "zh": "🏠 住宅", "ru": "🏠 Жилой", "es": "🏠 Residencial"},
    "infra_commercial":   {"en": "🏪 Commercial",  "ar": "🏪 تجاري", "fr": "🏪 Commercial",  "zh": "🏪 商业", "ru": "🏪 Коммерческий", "es": "🏪 Comercial"},
    "infra_government":   {"en": "🏛 Government",  "ar": "🏛 حكومي", "fr": "🏛 Gouvernement","zh": "🏛 政府", "ru": "🏛 Государственный", "es": "🏛 Gobierno"},
    "infra_utility":      {"en": "⚡ Utility",     "ar": "⚡ مرافق", "fr": "⚡ Services",    "zh": "⚡ 公用设施", "ru": "⚡ Коммунальный", "es": "⚡ Servicios"},
    "infra_transport":    {"en": "🛣 Transport",   "ar": "🛣 نقل",   "fr": "🛣 Transport",   "zh": "🛣 交通", "ru": "🛣 Транспорт", "es": "🛣 Transporte"},
    "infra_community":    {"en": "🏫 Community",   "ar": "🏫 مجتمعي","fr": "🏫 Communauté", "zh": "🏫 社区", "ru": "🏫 Общественный", "es": "🏫 Comunidad"},
    "infra_public_space": {"en": "🏟 Public space","ar": "🏟 فضاء عام","fr": "🏟 Espace public","zh": "🏟 公共空间","ru": "🏟 Общественное пространство","es": "🏟 Espacio público"},
    "infra_other":        {"en": "❓ Other",       "ar": "❓ أخرى",  "fr": "❓ Autre",       "zh": "❓ 其他", "ru": "❓ Другое", "es": "❓ Otro"},
    # Crisis nature labels
    "crisis_earthquake":  {"en": "🌍 Earthquake",  "ar": "🌍 زلزال",  "fr": "🌍 Séisme",      "zh": "🌍 地震",  "ru": "🌍 Землетрясение", "es": "🌍 Terremoto"},
    "crisis_flood":       {"en": "🌊 Flood",       "ar": "🌊 فيضان", "fr": "🌊 Inondation",  "zh": "🌊 洪水",  "ru": "🌊 Наводнение",    "es": "🌊 Inundación"},
    "crisis_tsunami":     {"en": "🌊 Tsunami",     "ar": "🌊 تسونامي","fr": "🌊 Tsunami",     "zh": "🌊 海啸",  "ru": "🌊 Цунами",        "es": "🌊 Tsunami"},
    "crisis_hurricane":   {"en": "🌀 Hurricane",   "ar": "🌀 إعصار", "fr": "🌀 Ouragan",     "zh": "🌀 飓风",  "ru": "🌀 Ураган",        "es": "🌀 Huracán"},
    "crisis_wildfire":    {"en": "🔥 Wildfire",    "ar": "🔥 حريق",  "fr": "🔥 Incendie",    "zh": "🔥 野火",  "ru": "🔥 Лесной пожар",  "es": "🔥 Incendio forestal"},
    "crisis_explosion":   {"en": "💥 Explosion",   "ar": "💥 انفجار","fr": "💥 Explosion",   "zh": "💥 爆炸",  "ru": "💥 Взрыв",         "es": "💥 Explosión"},
    "crisis_chemical":    {"en": "☣ Chemical",    "ar": "☣ كيميائي","fr": "☣ Chimique",    "zh": "☣ 化学",  "ru": "☣ Химическое",    "es": "☣ Químico"},
    "crisis_conflict":    {"en": "⚔ Conflict",    "ar": "⚔ نزاع",  "fr": "⚔ Conflit",     "zh": "⚔ 冲突",  "ru": "⚔ Конфликт",      "es": "⚔ Conflicto"},
    "crisis_civil_unrest":{"en": "🚨 Civil unrest","ar": "🚨 اضطرابات","fr": "🚨 Troubles civils","zh": "🚨 内乱","ru": "🚨 Гражданские волнения","es": "🚨 Disturbios civiles"},
}


def t(key: str, lang: str, **kwargs) -> str:
    """Return the string for key in lang, falling back to English."""
    text = STRINGS.get(key, {}).get(lang) or STRINGS.get(key, {}).get("en", key)
    return text.format(**kwargs) if kwargs else text
