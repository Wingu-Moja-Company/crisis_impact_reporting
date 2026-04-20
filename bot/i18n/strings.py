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
        "en": "Share your location or type a what3words address (e.g. ///filled.count.soap).",
        "ar": "شارك موقعك أو اكتب عنوان what3words (مثال: ///filled.count.soap).",
        "fr": "Partagez votre position ou saisissez une adresse what3words (ex. ///filled.count.soap).",
        "zh": "分享您的位置，或输入 what3words 地址（例如：///filled.count.soap）。",
        "ru": "Поделитесь геолокацией или введите адрес what3words (например: ///filled.count.soap).",
        "es": "Comparta su ubicación o escriba una dirección what3words (p.ej. ///filled.count.soap).",
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
    "error_generic": {
        "en": "Something went wrong. Please try again with /start.",
        "ar": "حدث خطأ ما. يرجى المحاولة مجددًا باستخدام /start.",
        "fr": "Une erreur s'est produite. Veuillez réessayer avec /start.",
        "zh": "出现错误，请使用 /start 重试。",
        "ru": "Что-то пошло не так. Попробуйте ещё раз с /start.",
        "es": "Algo salió mal. Por favor intente de nuevo con /start.",
    },
    # Damage level labels
    "damage_minimal": {
        "en": "Minimal — cosmetic only, still functional",
        "ar": "طفيف — تجميلي فقط، لا يزال وظيفيًا",
        "fr": "Minimal — cosmétique uniquement, encore fonctionnel",
        "zh": "轻微 — 仅外观损坏，仍可使用",
        "ru": "Минимальный — косметический ущерб, здание функционирует",
        "es": "Mínimo — solo cosmético, aún funcional",
    },
    "damage_partial": {
        "en": "Partial — repairable, usable with caution",
        "ar": "جزئي — قابل للإصلاح، يمكن استخدامه بحذر",
        "fr": "Partiel — réparable, utilisable avec précaution",
        "zh": "部分 — 可修复，谨慎使用",
        "ru": "Частичный — поддаётся ремонту, можно использовать с осторожностью",
        "es": "Parcial — reparable, utilizable con precaución",
    },
    "damage_complete": {
        "en": "Complete — structurally unsafe or destroyed",
        "ar": "كامل — غير آمن هيكليًا أو مدمّر",
        "fr": "Complet — structurellement dangereux ou détruit",
        "zh": "完全 — 结构不安全或已损毁",
        "ru": "Полный — конструктивно опасен или разрушен",
        "es": "Completo — estructuralmente inseguro o destruido",
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
