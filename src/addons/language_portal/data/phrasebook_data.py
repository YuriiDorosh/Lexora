"""Survival Phrasebook data — EN / UK / EL translations for 6 travel scenarios."""

SCENARIO_ORDER = ["airport", "hotel", "restaurant", "transport", "shopping", "emergency"]

PHRASEBOOK = {
    "airport": {
        "icon": "✈️",
        "label": "Airport & Flight",
        "phrases": [
            {
                "en": "Where is the check-in counter?",
                "uk": "Де знаходиться стійка реєстрації?",
                "el": "Πού είναι ο πάγκος check-in;",
                "tags": ["check-in", "directions"],
            },
            {
                "en": "I'd like a window seat, please.",
                "uk": "Мені, будь ласка, місце біля вікна.",
                "el": "Θα ήθελα μια θέση δίπλα στο παράθυρο, παρακαλώ.",
                "tags": ["check-in", "seat"],
            },
            {
                "en": "Is my flight on time?",
                "uk": "Мій рейс вчасно?",
                "el": "Είναι η πτήση μου στην ώρα της;",
                "tags": ["flight", "status"],
            },
            {
                "en": "My flight has been delayed.",
                "uk": "Мій рейс затримується.",
                "el": "Η πτήση μου έχει καθυστερήσει.",
                "tags": ["flight", "delay"],
            },
            {
                "en": "Where is gate number twelve?",
                "uk": "Де знаходиться виліт номер дванадцять?",
                "el": "Πού είναι η έξοδος αριθμός δώδεκα;",
                "tags": ["boarding", "gate"],
            },
            {
                "en": "I have nothing to declare.",
                "uk": "Мені нічого декларувати.",
                "el": "Δεν έχω τίποτα να δηλώσω.",
                "tags": ["customs", "declaration"],
            },
            {
                "en": "Where do I collect my luggage?",
                "uk": "Де я можу забрати свій багаж?",
                "el": "Πού παραλαμβάνω τις αποσκευές μου;",
                "tags": ["luggage", "arrival"],
            },
            {
                "en": "My bag is missing.",
                "uk": "Моя сумка зникла.",
                "el": "Η τσάντα μου λείπει.",
                "tags": ["luggage", "emergency"],
            },
            {
                "en": "Can I take this as carry-on?",
                "uk": "Чи можу я взяти це як ручний багаж?",
                "el": "Μπορώ να το πάρω αυτό ως χειραποσκευή;",
                "tags": ["check-in", "baggage"],
            },
            {
                "en": "Where is the security checkpoint?",
                "uk": "Де знаходиться контроль безпеки?",
                "el": "Πού είναι ο έλεγχος ασφαλείας;",
                "tags": ["security", "directions"],
            },
            {
                "en": "Please remove your shoes and belt.",
                "uk": "Будь ласка, зніміть взуття та пасок.",
                "el": "Παρακαλώ αφαιρέστε τα παπούτσια και τη ζώνη σας.",
                "tags": ["security"],
            },
            {
                "en": "Is there a bus to the city centre?",
                "uk": "Чи є автобус до центру міста?",
                "el": "Υπάρχει λεωφορείο για το κέντρο της πόλης;",
                "tags": ["transport", "arrival"],
            },
        ],
    },

    "hotel": {
        "icon": "🏨",
        "label": "Hotel & Stay",
        "phrases": [
            {
                "en": "I have a reservation under the name Smith.",
                "uk": "Я маю бронювання на ім'я Сміт.",
                "el": "Έχω κράτηση στο όνομα Σμιθ.",
                "tags": ["check-in"],
            },
            {
                "en": "Could I have an extra towel, please?",
                "uk": "Чи можу я отримати додатковий рушник, будь ласка?",
                "el": "Θα μπορούσα να έχω μια επιπλέον πετσέτα, παρακαλώ;",
                "tags": ["room", "request"],
            },
            {
                "en": "What is the Wi-Fi password?",
                "uk": "Який пароль від Wi-Fi?",
                "el": "Ποιος είναι ο κωδικός Wi-Fi;",
                "tags": ["wifi", "internet"],
            },
            {
                "en": "At what time is breakfast served?",
                "uk": "О котрій подається сніданок?",
                "el": "Τι ώρα σερβίρεται το πρωινό;",
                "tags": ["breakfast", "timing"],
            },
            {
                "en": "I'd like a wake-up call at seven.",
                "uk": "Мені потрібен дзвінок-будильник о сьомій.",
                "el": "Θα ήθελα κλήση αφύπνισης στις εφτά.",
                "tags": ["wake-up", "service"],
            },
            {
                "en": "The air conditioning is not working.",
                "uk": "Кондиціонер не працює.",
                "el": "Το κλιματιστικό δεν λειτουργεί.",
                "tags": ["room", "complaint"],
            },
            {
                "en": "I'd like to extend my stay by one night.",
                "uk": "Я хотів би продовжити своє перебування на одну ніч.",
                "el": "Θα ήθελα να παρατείνω την παραμονή μου κατά μία νύχτα.",
                "tags": ["checkout", "extension"],
            },
            {
                "en": "Can I store my luggage after checkout?",
                "uk": "Чи можу я залишити багаж після виселення?",
                "el": "Μπορώ να αποθηκεύσω τις αποσκευές μου μετά το check-out;",
                "tags": ["checkout", "luggage"],
            },
            {
                "en": "Is there a parking space available?",
                "uk": "Чи є вільне місце для паркування?",
                "el": "Υπάρχει διαθέσιμος χώρος στάθμευσης;",
                "tags": ["parking", "facilities"],
            },
            {
                "en": "Please do not disturb.",
                "uk": "Будь ласка, не турбуйте.",
                "el": "Παρακαλώ μη με ενοχλείτε.",
                "tags": ["room", "privacy"],
            },
            {
                "en": "What time is checkout?",
                "uk": "О котрій годині виселення?",
                "el": "Τι ώρα είναι το check-out;",
                "tags": ["checkout"],
            },
            {
                "en": "Could you recommend a nearby restaurant?",
                "uk": "Чи могли б ви порекомендувати найближчий ресторан?",
                "el": "Θα μπορούσατε να μου συστήσετε ένα κοντινό εστιατόριο;",
                "tags": ["recommendation", "dining"],
            },
        ],
    },

    "restaurant": {
        "icon": "🍽️",
        "label": "Restaurant & Café",
        "phrases": [
            {
                "en": "A table for two, please.",
                "uk": "Столик на двох, будь ласка.",
                "el": "Ένα τραπέζι για δύο, παρακαλώ.",
                "tags": ["seating"],
            },
            {
                "en": "Could I see the menu, please?",
                "uk": "Чи можу я побачити меню, будь ласка?",
                "el": "Μπορώ να δω το μενού, παρακαλώ;",
                "tags": ["ordering"],
            },
            {
                "en": "What do you recommend?",
                "uk": "Що ви рекомендуєте?",
                "el": "Τι συστήνετε;",
                "tags": ["ordering", "recommendation"],
            },
            {
                "en": "I am allergic to nuts.",
                "uk": "Я алергік на горіхи.",
                "el": "Είμαι αλλεργικός στους ξηρούς καρπούς.",
                "tags": ["allergies", "dietary"],
            },
            {
                "en": "Is this dish gluten-free?",
                "uk": "Чи є ця страва безглютеновою?",
                "el": "Είναι αυτό το πιάτο χωρίς γλουτένη;",
                "tags": ["dietary", "allergies"],
            },
            {
                "en": "I'd like my steak medium-rare.",
                "uk": "Я хочу свій стейк середнього ступеня прожарки.",
                "el": "Θέλω τη μπριζόλα μου μέτρια ψημένη.",
                "tags": ["ordering", "meat"],
            },
            {
                "en": "Could we have some more water?",
                "uk": "Чи можемо ми отримати ще трохи води?",
                "el": "Θα μπορούσαμε να έχουμε λίγο περισσότερο νερό;",
                "tags": ["drinks", "request"],
            },
            {
                "en": "The bill, please.",
                "uk": "Рахунок, будь ласка.",
                "el": "Τον λογαριασμό, παρακαλώ.",
                "tags": ["payment"],
            },
            {
                "en": "Can we split the bill?",
                "uk": "Ми можемо розділити рахунок?",
                "el": "Μπορούμε να χωρίσουμε τον λογαριασμό;",
                "tags": ["payment"],
            },
            {
                "en": "Is service included?",
                "uk": "Чи включено обслуговування?",
                "el": "Περιλαμβάνεται το σέρβις;",
                "tags": ["payment", "tip"],
            },
            {
                "en": "I did not order this.",
                "uk": "Я не замовляв це.",
                "el": "Δεν παρήγγειλα αυτό.",
                "tags": ["complaint", "ordering"],
            },
            {
                "en": "This is delicious, thank you.",
                "uk": "Це смачно, дякую.",
                "el": "Είναι πολύ νόστιμο, ευχαριστώ.",
                "tags": ["compliment"],
            },
        ],
    },

    "transport": {
        "icon": "🚕",
        "label": "Transport & Taxi",
        "phrases": [
            {
                "en": "Take me to this address, please.",
                "uk": "Відвезіть мене за цією адресою, будь ласка.",
                "el": "Πάρτε με σε αυτή τη διεύθυνση, παρακαλώ.",
                "tags": ["taxi", "destination"],
            },
            {
                "en": "How much will it cost to the city centre?",
                "uk": "Скільки буде коштувати до центру міста?",
                "el": "Πόσο θα κοστίσει μέχρι το κέντρο της πόλης;",
                "tags": ["taxi", "price"],
            },
            {
                "en": "Please stop here.",
                "uk": "Будь ласка, зупиніться тут.",
                "el": "Παρακαλώ σταματήστε εδώ.",
                "tags": ["taxi", "stop"],
            },
            {
                "en": "Do you accept credit cards?",
                "uk": "Ви приймаєте кредитні картки?",
                "el": "Δέχεστε πιστωτικές κάρτες;",
                "tags": ["payment", "taxi"],
            },
            {
                "en": "Where is the nearest metro station?",
                "uk": "Де знаходиться найближча станція метро?",
                "el": "Πού είναι ο πλησιέστερος σταθμός μετρό;",
                "tags": ["metro", "directions"],
            },
            {
                "en": "Which bus goes to the museum?",
                "uk": "Який автобус їде до музею?",
                "el": "Ποιο λεωφορείο πηγαίνει στο μουσείο;",
                "tags": ["bus", "directions"],
            },
            {
                "en": "A single ticket to downtown, please.",
                "uk": "Один квиток до центру міста, будь ласка.",
                "el": "Ένα απλό εισιτήριο για το κέντρο, παρακαλώ.",
                "tags": ["ticket", "bus"],
            },
            {
                "en": "Could you drive faster, please?",
                "uk": "Чи могли б ви їхати швидше, будь ласка?",
                "el": "Θα μπορούσατε να οδηγάτε πιο γρήγορα, παρακαλώ;",
                "tags": ["taxi", "speed"],
            },
            {
                "en": "I missed my train.",
                "uk": "Я пропустив свій потяг.",
                "el": "Έχασα το τρένο μου.",
                "tags": ["train", "problem"],
            },
            {
                "en": "When is the next train to the airport?",
                "uk": "Коли наступний потяг до аеропорту?",
                "el": "Πότε είναι το επόμενο τρένο για το αεροδρόμιο;",
                "tags": ["train", "timing"],
            },
            {
                "en": "Is this seat taken?",
                "uk": "Це місце зайняте?",
                "el": "Είναι αυτή η θέση πιασμένη;",
                "tags": ["seat", "public transport"],
            },
            {
                "en": "Could you call a taxi for me?",
                "uk": "Чи могли б ви викликати мені таксі?",
                "el": "Θα μπορούσατε να μου καλέσετε ένα ταξί;",
                "tags": ["taxi", "request"],
            },
        ],
    },

    "shopping": {
        "icon": "🛍️",
        "label": "Shopping",
        "phrases": [
            {
                "en": "How much does this cost?",
                "uk": "Скільки це коштує?",
                "el": "Πόσο κοστίζει αυτό;",
                "tags": ["price"],
            },
            {
                "en": "Do you have this in a larger size?",
                "uk": "Чи є у вас це у більшому розмірі?",
                "el": "Το έχετε σε μεγαλύτερο μέγεθος;",
                "tags": ["size", "clothing"],
            },
            {
                "en": "Can I try this on?",
                "uk": "Чи можу я це приміряти?",
                "el": "Μπορώ να το δοκιμάσω;",
                "tags": ["fitting", "clothing"],
            },
            {
                "en": "Is there a discount?",
                "uk": "Чи є знижка?",
                "el": "Υπάρχει κάποια έκπτωση;",
                "tags": ["discount", "price"],
            },
            {
                "en": "I'll take it.",
                "uk": "Я це візьму.",
                "el": "Θα το πάρω.",
                "tags": ["purchase"],
            },
            {
                "en": "Can I pay by card?",
                "uk": "Чи можу я заплатити карткою?",
                "el": "Μπορώ να πληρώσω με κάρτα;",
                "tags": ["payment"],
            },
            {
                "en": "Could I have a receipt, please?",
                "uk": "Чи можу я отримати чек, будь ласка?",
                "el": "Θα μπορούσα να έχω μια απόδειξη, παρακαλώ;",
                "tags": ["receipt", "payment"],
            },
            {
                "en": "I'd like to return this item.",
                "uk": "Я хочу повернути цей товар.",
                "el": "Θα ήθελα να επιστρέψω αυτό το προϊόν.",
                "tags": ["return", "refund"],
            },
            {
                "en": "Do you have a smaller size?",
                "uk": "Чи є у вас менший розмір?",
                "el": "Έχετε μικρότερο μέγεθος;",
                "tags": ["size", "clothing"],
            },
            {
                "en": "Where is the fitting room?",
                "uk": "Де знаходиться примірювальна?",
                "el": "Πού είναι ο χώρος δοκιμής;",
                "tags": ["fitting", "directions"],
            },
            {
                "en": "Is this on sale?",
                "uk": "Чи це на розпродажі?",
                "el": "Αυτό είναι σε έκπτωση;",
                "tags": ["sale", "price"],
            },
            {
                "en": "Do you have this in a different colour?",
                "uk": "Чи є це в іншому кольорі?",
                "el": "Το έχετε σε διαφορετικό χρώμα;",
                "tags": ["colour", "clothing"],
            },
        ],
    },

    "emergency": {
        "icon": "🆘",
        "label": "Emergency",
        "phrases": [
            {
                "en": "Help! Call an ambulance!",
                "uk": "Допоможіть! Викличте швидку!",
                "el": "Βοήθεια! Καλέστε ασθενοφόρο!",
                "tags": ["medical", "urgent"],
            },
            {
                "en": "Call the police!",
                "uk": "Викличте поліцію!",
                "el": "Καλέστε την αστυνομία!",
                "tags": ["police", "urgent"],
            },
            {
                "en": "I have been robbed.",
                "uk": "Мене пограбували.",
                "el": "Με λήστεψαν.",
                "tags": ["theft", "police"],
            },
            {
                "en": "I am lost.",
                "uk": "Я загубився.",
                "el": "Έχω χαθεί.",
                "tags": ["directions", "help"],
            },
            {
                "en": "I need a doctor.",
                "uk": "Мені потрібен лікар.",
                "el": "Χρειάζομαι γιατρό.",
                "tags": ["medical"],
            },
            {
                "en": "Where is the nearest hospital?",
                "uk": "Де знаходиться найближча лікарня?",
                "el": "Πού είναι το πλησιέστερο νοσοκομείο;",
                "tags": ["medical", "directions"],
            },
            {
                "en": "I am having an allergic reaction.",
                "uk": "У мене алергічна реакція.",
                "el": "Έχω αλλεργική αντίδραση.",
                "tags": ["medical", "allergies"],
            },
            {
                "en": "I lost my passport.",
                "uk": "Я загубив свій паспорт.",
                "el": "Έχασα το διαβατήριό μου.",
                "tags": ["documents", "help"],
            },
            {
                "en": "Please call the embassy.",
                "uk": "Будь ласка, зателефонуйте до посольства.",
                "el": "Παρακαλώ καλέστε την πρεσβεία.",
                "tags": ["embassy", "urgent"],
            },
            {
                "en": "I cannot breathe.",
                "uk": "Я не можу дихати.",
                "el": "Δεν μπορώ να αναπνεύσω.",
                "tags": ["medical", "urgent"],
            },
            {
                "en": "There is a fire!",
                "uk": "Пожежа!",
                "el": "Υπάρχει φωτιά!",
                "tags": ["fire", "urgent"],
            },
            {
                "en": "I need to contact my insurance company.",
                "uk": "Мені потрібно зв'язатися зі своєю страховою компанією.",
                "el": "Πρέπει να επικοινωνήσω με την ασφαλιστική μου εταιρεία.",
                "tags": ["insurance", "help"],
            },
        ],
    },
}
