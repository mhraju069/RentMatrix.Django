import re

TRANSLATIONS = {
    # Auth / User Management
    "User with this email already exists": {
        "en": "User with this email already exists",
        "ar": "المستخدم بهذا البريد الإلكتروني موجود بالفعل"
    },
    "User with this phone already exists": {
        "en": "User with this phone already exists",
        "ar": "المستخدم بهذا الهاتف موجود بالفعل"
    },
    "User created successfully": {
        "en": "User created successfully",
        "ar": "تم إنشاء المستخدم بنجاح"
    },
    "User not found": {
        "en": "User not found",
        "ar": "المستخدم غير موجود"
    },
    "Your account is inactive.": {
        "en": "Your account is inactive.",
        "ar": "حسابك غير نشط."
    },
    "Your account has been blocked.": {
        "en": "Your account has been blocked.",
        "ar": "تم حظر حسابك."
    },
    "Invalid credentials": {
        "en": "Invalid credentials",
        "ar": "بيانات الاعتماد غير صالحة"
    },
    "User logged in successfully": {
        "en": "User logged in successfully",
        "ar": "تم تسجيل دخول المستخدم بنجاح"
    },
    "User fetched successfully": {
        "en": "User fetched successfully",
        "ar": "تم جلب بيانات المستخدم بنجاح"
    },
    "Old and new password are required": {
        "en": "Old and new password are required",
        "ar": "كلمة المرور القديمة والجديدة مطلوبة"
    },
    "Invalid old password": {
        "en": "Invalid old password",
        "ar": "كلمة المرور القديمة غير صالحة"
    },
    "Uploaded file is not a valid image": {
        "en": "Uploaded file is not a valid image",
        "ar": "الملف الذي تم تحميله ليس صورة صالحة"
    },
    "User updated successfully": {
        "en": "User updated successfully",
        "ar": "تم تحديث المستخدم بنجاح"
    },
    "Otp sent successfully": {
        "en": "Otp sent successfully",
        "ar": "تم إرسال رمز التحقق بنجاح"
    },
    "Otp not sent": {
        "en": "Otp not sent",
        "ar": "لم يتم إرسال رمز التحقق"
    },
    "OTP not found": {
        "en": "OTP not found",
        "ar": "رمز التحقق غير موجود"
    },
    "Invalid OTP": {
        "en": "Invalid OTP",
        "ar": "رمز التحقق غير صالح"
    },
    "OTP expired": {
        "en": "OTP expired",
        "ar": "انتهت صلاحية رمز التحقق"
    },
    "Otp verified successfully": {
        "en": "Otp verified successfully",
        "ar": "تم التحقق من الرمز بنجاح"
    },
    "Password reset successfully": {
        "en": "Password reset successfully",
        "ar": "تم إعادة تعيين كلمة المرور بنجاح"
    },

    # Booking
    "property_id is required": {
        "en": "property_id is required",
        "ar": "معرف العقار مطلوب"
    },
    "Price calculated successfully": {
        "en": "Price calculated successfully",
        "ar": "تم حساب السعر بنجاح"
    },
    "Property not found": {
        "en": "Property not found",
        "ar": "العقار غير موجود"
    },
    "Booking created successfully": {
        "en": "Booking created successfully",
        "ar": "تم إنشاء الحجز بنجاح"
    },
    "Booking list fetched successfully": {
        "en": "Booking list fetched successfully",
        "ar": "تم جلب قائمة الحجوزات بنجاح"
    },
    "Booking not found": {
        "en": "Booking not found",
        "ar": "الحجز غير موجود"
    },
    "Booking details fetched successfully": {
        "en": "Booking details fetched successfully",
        "ar": "تم جلب تفاصيل الحجز بنجاح"
    },
    "Booking already cancelled": {
        "en": "Booking already cancelled",
        "ar": "الحجز ملغى بالفعل"
    },
    "Booking cancelled successfully": {
        "en": "Booking cancelled successfully",
        "ar": "تم إلغاء الحجز بنجاح"
    },
    "Booking already confirmed": {
        "en": "Booking already confirmed",
        "ar": "الحجز مؤكد بالفعل"
    },
    "Booking confirmed successfully, and guest documents auto-approved": {
        "en": "Booking confirmed successfully, and guest documents auto-approved",
        "ar": "تم تأكيد الحجز بنجاح، وتمت الموافقة التلقائية على مستندات الضيف"
    },

    # Notification
    "Device token already saved": {
        "en": "Device token already saved",
        "ar": "تم حفظ رمز الجهاز بالفعل"
    },
    "Device token saved successfully": {
        "en": "Device token saved successfully",
        "ar": "تم حفظ رمز الجهاز بنجاح"
    },
    "Notifications fetched successfully": {
        "en": "Notifications fetched successfully",
        "ar": "تم جلب الإشعارات بنجاح"
    },
    "Notification settings fetched successfully": {
        "en": "Notification settings fetched successfully",
        "ar": "تم جلب إعدادات الإشعارات بنجاح"
    },
    "Notification settings updated successfully": {
        "en": "Notification settings updated successfully",
        "ar": "تم تحديث إعدادات الإشعارات بنجاح"
    },
    "Successfully toggled booking": {
        "en": "Successfully toggled booking",
        "ar": "تم تبديل الحجز بنجاح"
    },
    "Successfully toggled checkin": {
        "en": "Successfully toggled checkin",
        "ar": "تم تبديل تسجيل الوصول بنجاح"
    },

    # Currency & Language
    "Languages fetched successfully": {
        "en": "Languages fetched successfully",
        "ar": "تم جلب اللغات بنجاح"
    },
    "Currencies fetched successfully": {
        "en": "Currencies fetched successfully",
        "ar": "تم جلب العملات بنجاح"
    },
    "User preferences fetched successfully": {
        "en": "User preferences fetched successfully",
        "ar": "تم جلب تفضيلات المستخدم بنجاح"
    },
    "Preferences updated successfully": {
        "en": "Preferences updated successfully",
        "ar": "تم تحديث التفضيلات بنجاح"
    },

    # Property
    "Properties fetched successfully": {
        "en": "Properties fetched successfully",
        "ar": "تم جلب العقارات بنجاح"
    },
    "Home sections fetched successfully": {
        "en": "Home sections fetched successfully",
        "ar": "تم جلب أقسام الصفحة الرئيسية بنجاح"
    },
    "Recommended properties fetched successfully": {
        "en": "Recommended properties fetched successfully",
        "ar": "تم جلب العقارات الموصى بها بنجاح"
    },
    "Popular nearby properties fetched successfully": {
        "en": "Popular nearby properties fetched successfully",
        "ar": "تم جلب العقارات الشهيرة المجاورة بنجاح"
    },
    "Property unfavourited successfully": {
        "en": "Property unfavourited successfully",
        "ar": "تم إزالة العقار من المفضلات بنجاح"
    },
    "Property favourited successfully": {
        "en": "Property favourited successfully",
        "ar": "تم إضافة العقار إلى المفضلات بنجاح"
    },
    "Favourite properties fetched successfully": {
        "en": "Favourite properties fetched successfully",
        "ar": "تم جلب العقارات المفضلة بنجاح"
    },
    "Property details fetched successfully": {
        "en": "Property details fetched successfully",
        "ar": "تم جلب تفاصيل العقار بنجاح"
    },
    "Property deleted successfully": {
        "en": "Property deleted successfully",
        "ar": "تم حذف العقار بنجاح"
    },
    "Property created successfully": {
        "en": "Property created successfully",
        "ar": "تم إنشاء العقار بنجاح"
    },
    "Invalid data": {
        "en": "Invalid data",
        "ar": "البيانات غير صالحة"
    },
    "Property not found or unauthorized": {
        "en": "Property not found or unauthorized",
        "ar": "العقار غير موجود أو غير مصرح به"
    },
    "Property updated successfully": {
        "en": "Property updated successfully",
        "ar": "تم تحديث العقار بنجاح"
    },
    "Gallery deleted successfully": {
        "en": "Gallery deleted successfully",
        "ar": "تم حذف المعرض بنجاح"
    },
    "Gallery updated successfully": {
        "en": "Gallery updated successfully",
        "ar": "تم تحديث المعرض بنجاح"
    },
    "Report submitted successfully": {
        "en": "Report submitted successfully",
        "ar": "تم تقديم البلاغ بنجاح"
    }
}

def translate_message(message: str, lang: str) -> str:
    if not message or not isinstance(message, str):
        return message
        
    lang = lang.lower()
    if lang not in ["en", "ar"]:
        lang = "en"
        
    # Check exact match
    if message in TRANSLATIONS:
        return TRANSLATIONS[message][lang]
        
    # Handle dynamic message patterns
    # Pattern 1: Successfully uploaded X document(s).
    upload_match = re.match(r"^Successfully uploaded (\d+) document\(s\)\.$", message)
    if upload_match:
        count = upload_match.group(1)
        if lang == "ar":
            return f"تم تحميل {count} من المستندات بنجاح."
        return f"Successfully uploaded {count} document(s)."
        
    # Pattern 2: Successfully toggled field_name
    toggle_match = re.match(r"^Successfully toggled (\w+)$", message)
    if toggle_match:
        field = toggle_match.group(1)
        field_ar = field
        if field == "booking":
            field_ar = "الحجز"
        elif field == "checkin":
            field_ar = "تسجيل الوصول"
            
        if lang == "ar":
            return f"تم تبديل {field_ar} بنجاح"
        return f"Successfully toggled {field}"

    return message
