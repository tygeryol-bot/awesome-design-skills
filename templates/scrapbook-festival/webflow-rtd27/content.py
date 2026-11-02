"""Content for the v2 tweaks, taken from the process document.
Artists: Rocking the Daisies 2025 (the last edition that went ahead; 2026 was cancelled).
Day/stage/time placements are proposals for 2027 and should be checked."""

DAYS = {
    "fri": {"name": "Friday", "short": "Fri", "line": "Come empty.",
            "text": "Arrive, set up camp and let the first night do its thing."},
    "sat": {"name": "Saturday", "short": "Sat", "line": "Hoard the feelings.",
            "text": "Big sets, long sunsets and songs you'll still be singing with your friends on the way home."},
    "sun": {"name": "Sunday", "short": "Sun", "line": "Take it home.",
            "text": "Slow mornings, last dances and one more photo before it's over."},
}

STAGES = {
    "main": {"name": "Main Stage", "icon": "sunflower", "text": "The big field. Headliners, sunsets and everyone singing."},
    "beach": {"name": "Beach Club", "icon": "sun-face", "text": "DJs from the afternoon until late."},
    "seeds": {"name": "Sowing the Seeds", "icon": "lily", "text": "New names to catch before everyone else does."},
}

# (slug, name, day, stage, time, one line about the set, headliner)
ACTS = [
    ("summer-walker", "Summer Walker", "fri", "main", "22:00", "The set you'll still be talking about on the drive home.", True),
    ("jessie-reyez", "Jessie Reyez", "fri", "main", "20:15", "Big voice, raw songs and a field singing every word back.", False),
    ("a-reece", "A-Reece", "fri", "main", "18:45", "South African hip-hop heavyweight. Learn the hooks before you get there.", False),
    ("elaine", "Elaine", "fri", "main", "17:15", "Soft late-afternoon R&B while the camp settles in.", False),
    ("focalistic", "Focalistic", "fri", "beach", "23:30", "Amapiano after dark. Nobody's heading back to the tent early.", False),
    ("dj-starrza", "DJ Starrza", "fri", "beach", "20:00", "The DJ set that kicks the first night into gear.", False),
    ("amy-mauritz", "Amy Mauritz", "fri", "beach", "18:00", "Warm-up selections as the first night gets going.", False),
    ("scoop-makhathini", "Scoop Makhathini", "fri", "seeds", "20:00", "Closing the first night on the small stage.", False),
    ("dphault", "D'Phault", "fri", "seeds", "18:30", "Worth the walk across the estate.", False),
    ("filah-lah-lah", "Filah Lah Lah", "fri", "seeds", "17:00", "Catch this one early and tell everyone you were there first.", False),
    ("marcus-harvey", "Marcus Harvey", "fri", "seeds", "15:30", "Golden light, early set, the first song of your weekend.", False),

    ("earl-sweatshirt", "Earl Sweatshirt", "sat", "main", "22:15", "Hypnotic, slow-burning rap from an artist with South African roots.", True),
    ("black-motion", "Black Motion", "sat", "main", "20:30", "Afro-house drums that carry across the whole estate.", False),
    ("mereba", "Mereba", "sat", "main", "19:00", "Warm songs for the long sunset.", False),
    ("sam-tompkins", "Sam Tompkins", "sat", "main", "17:30", "Phones up for one song, then put them away.", False),
    ("dj-zinhle", "DJ Zinhle", "sat", "beach", "23:30", "Saturday's last dance. Don't leave before this one.", False),
    ("kid-fonque", "Kid Fonque", "sat", "beach", "18:00", "Deep, easy selections as the sun drops.", False),
    ("atmos-blaq", "Atmos Blaq", "sat", "beach", "16:00", "Afternoon grooves for the people who found the shade.", False),
    ("sooks", "!Sooks", "sat", "seeds", "19:30", "New sounds before they blow up.", False),
    ("lelowhatsgood", "Lelowhatsgood", "sat", "seeds", "15:00", "Saturday warm-up for the early risers.", False),

    ("kabza-de-small", "Kabza De Small", "sun", "main", "21:30", "The last dance. Make it count, then take it home.", True),
    ("vigro-deep", "Vigro Deep", "sun", "main", "19:30", "Amapiano for the last sunset of the weekend.", False),
    ("djeff", "DJEFF", "sun", "beach", "17:00", "Afro-house to stretch the last afternoon out.", False),
    ("fka-mash", "FKA Mash", "sun", "beach", "14:00", "A slow Sunday start. Coffee in one hand.", False),
    ("black-villain", "Black Villain", "sun", "seeds", "15:30", "One more discovery before you pack up.", False),
]

PASSES = {
    "keepsake": {"name": "Keepsake", "long": "Keepsake – Weekend Pass", "price": 1690},
    "golden": {"name": "Golden Hour", "long": "Golden Hour – VIP Weekend Pass", "price": 3290},
}

# per = "person" or "tent"; sleeps = people per tent; passes_included for pre-pitched tents
STAYS = {
    "patch": {"name": "Your Own Patch", "price": 590, "per": "person", "type": "Bring your own tent",
              "text": "General camping for people bringing their own tent and gear.",
              "features": ["Camping pitch", "Showers + toilets", "Security"]},
    "slow": {"name": "Slow Mornings", "price": 890, "per": "person", "type": "Bring your own tent",
             "text": "A quieter camping area with lower noise, closer facilities and a morning coffee point.",
             "features": ["Quieter area", "Closer facilities", "Morning coffee point"]},
    "polaroid": {"name": "The Polaroid", "price": 7200, "per": "tent", "sleeps": 2, "type": "Pre-pitched · sleeps 2",
                 "text": "Come empty. A pre-pitched tent for two with beds and bedding, and both festival passes included.",
                 "features": ["Beds + bedding", "2 Keepsake passes included", "One purchase"]},
    "contact": {"name": "The Contact Sheet", "price": 14400, "per": "tent", "sleeps": 4, "type": "Pre-pitched · sleeps 4",
                "text": "The bigger frame. A pre-pitched tent for four with beds and bedding, and all four festival passes included.",
                "features": ["Beds + bedding", "4 Keepsake passes included", "One purchase"]},
}

EXTRAS = {
    "shuttle": {"name": "Cape Town Return Shuttle", "price": 380, "text": "Transport between Cape Town and the festival. Per person."},
    "locker": {"name": "Locker", "price": 150, "text": "Secure storage for your valuables all weekend."},
}

FAQ = [
    ("What's the difference between Keepsake and Golden Hour?",
     "Keepsake is your 3-day weekend pass (R1,690 Regular). Golden Hour is the VIP pass (R3,290 Regular), with fast-track entry, a raised viewing deck, a shaded lounge and a welcome drink every day."),
    ("How do I pay?",
     "You'll finish your booking on Computicket. We'll show you the full total before you check out, so you know exactly what you're paying."),
    ("Can I change the name on my ticket?",
     "Yes, once per ticket for R100, as long as it's at least 7 days before the festival."),
    ("What happens if the festival gets cancelled?",
     "You'll automatically get a full refund. No extra steps needed."),
    ("Is there a day pass?",
     "No. Darling is remote and the festival can finish around midnight, so getting home after a single day would be tricky. Every pass covers the whole weekend."),
    ("Do the pre-pitched tents include passes?",
     "Yes. The Polaroid includes 2 Keepsake passes and The Contact Sheet includes 4, so it's one purchase. Want Golden Hour instead? You only pay the difference."),
]
