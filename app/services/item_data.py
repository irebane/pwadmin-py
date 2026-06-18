"""
Static item-builder data ported from pw_items_ext.php and config.php.
All lists use the same # delimited string format as PHP so ibuild.js
can consume them unchanged.
"""

ITEM_COLOR = ["#ffffff", "#ffffff", "#7777ff", "#00ff00", "#ffff00", "#ff0000"]
PWRACE_COLOR = ["", "#fddcbb", "#bbffbb", "#cacaff", "#aaaaff", "#fada77", "#dddddd"]

PW_CLASSES = ["Warrior", "Magician", "Werebeast", "Werefox", "Elf Archer", "Elf Priest",
               "Psychic", "Assassin", "Seeker", "Mystic", "Tideborn Rogue", "Tideborn Assassin"]

CLASS_MASKS = [1, 2, 16, 8, 128, 64, 4, 32, 256, 512, 1024, 2048]

PROC_TYPES = [
    "Cannot lose if die", "Cannot drop", "Cannot sell", "Fashion & Flyer",
    "Cannot trade", "Cannot refine", "Bind on gear", "? [128]",
    "Lose if leave area", "Use if pick up", "Drop if die", "Lose if log off",
    "Cannot repair", "Damaged, (fuel?)", "No account stash?", "Soulbound",
    "? [65536]", "? [131072]",
]

# ── Sub-menu structure: IBMenuSC[type][index] = "Name#minVer" ──────────────
IBMENU_SC = {
    1: [
        "Polehammer#0", "Poleaxe#0", "Dual Axe#0", "Dual Hammer#0",
        "Spear#0", "Polearm#0", "Staff#0", "Mace#0", "Blade#0", "Sword#0",
        "Dual Blade#0", "Dual Sword#0", "Fist#0", "Claw#0",
        "Bow#0", "Crossbow#0", "Slingshot#0", "Magic Sword#0",
        "Wand#0", "Magic Quoit#0", "Magic Staff#0",
        "Dagger#40", "Sphere#40", "Sabre#80", "Schythe#80",
    ],
    2: [
        "Heavy Plate#0", "Light Armor#0", "Magic Robe#0",
        "Heavy Leggings#0", "Light Leggings#0", "Magic Leggings#0",
        "Heavy Footwear#0", "Light Footwear#0", "Magic Footwear#0",
        "Heavy Wristguard#0", "Light Wristguard#0", "Magic Wristguard#0",
        "Heavy Helmet#0", "Magic Headgear#0", "Manteau/Cloack#0",
    ],
    3: [
        "Physical Necklance#0", "Dodge Necklance#0", "Magical Necklance#0",
        "Physical Waist Adorn#0", "Dodge Waist Adorn#0", "Magical Waist Adorn#0",
        "Physical Ring#0", "Magical Ring#0",
    ],
    4: [
        "Flyer#0", "Pet Egg#0", "Bless box#30", "Elf#38",
        "Hiero & Charm#0", "Ammo#0", "Potion#0", "Task Dice#0",
        "Pet Food#0", "Soul Stones#0", "Order#79", "Star Chart#79",
    ],
    5: [
        "Tome#0", "Boost#0", "Util#0", "Chat#0", "Pages#0", "Dye#0",
        "Firework#0", "Dragon Quest#0", "Pack Reward#0", "Pet Scroll#0",
        "Funny#0", "Fuel#0", "Wine, Blood#0", "Elf Gear#38",
        "Runes#50", "Mark of Might#69",
    ],
    6: ["Normal Mats#0", "Jade#0", "Herbs#0"],
    7: [
        "Top [Male]#0", "Top [Female]#0",
        "Pants [Male]#0", "Skirt [Female]#0",
        "Glove [Male]#0", "Sleeves [Female]#0",
        "Boots [Male]#0", "Shoes [Female]#0",
        "Hair Style [Male]#0", "Hair Style [Female]#0",
    ],
    8: [
        "Warrior#0", "Magician#0", "Werebeast#0", "Werefox#0",
        "Elf Archer#0", "Elf Priest#0",
    ],
}

# ── Soul Stones: SoulStone[slot] list of "StoneId#Addon1#Addon2#...#Name#Grade#MinVer" ──
SOUL_STONES = {
    1: [
        "3646#577#577#4,5#4,5#Jargoon#1#20",
        "3647#578#578#4,10#4,10#Jargoon#2#20",
        "3648#579#579#4,15#4,15#Jargoon#3#20",
        "3649#580#580#4,20#4,20#Jargoon#4#20",
        "2012#497#497#4,25#4,25#Jargoon#5#20",
        "6384#1174#1174#4,32#4,32#Jargoon#6#20",
        "6385#1175#1175#4,40#4,40#Jargoon#7#20",
        "6386#1176#1176#4,50#4,50#Jargoon#8#20",
        "6387#1177#1177#4,62#4,62#Jargoon#9#20",
        "6388#1178#1178#4,75#4,75#Jargoon#10#20",
        "2013#498#498#4,100#4,100#Jargoon#11#20",
        "2014#499#499#4,130#4,130#Jargoon#12#20",
        "3650#581#581#13,5#13,5#Citrine#1#20",
        "3651#582#582#13,10#13,10#Citrine#2#20",
        "3652#583#583#13,15#13,15#Citrine#3#20",
        "3653#584#584#13,20#13,20#Citrine#4#20",
        "2015#500#500#13,25#13,25#Citrine#5#20",
        "6389#1179#1179#13,32#13,32#Citrine#6#20",
        "6390#1180#1180#13,40#13,40#Citrine#7#20",
        "6391#1181#1181#13,50#13,50#Citrine#8#20",
        "6392#1182#1182#13,62#13,62#Citrine#9#20",
        "6393#1183#1183#13,75#13,75#Citrine#10#20",
        "2016#501#501#13,100#13,100#Citrine#11#20",
        "2017#502#502#13,130#13,130#Citrine#12#20",
    ],
    2: [
        "5292#672#673#59,6#15,8#White Jade#1#20",
        "5293#674#675#59,12#15,16#White Jade#2#20",
        "5294#687#688#59,18#15,24#White Jade#3#20",
        "5295#689#690#59,24#15,32#White Jade#4#20",
        "5296#691#692#59,32#15,42#White Jade#5#20",
        "6394#1184#1185#59,40#15,52#White Jade#6#20",
        "6395#1186#1187#59,50#15,66#White Jade#7#20",
        "6396#1188#1189#59,64#15,84#White Jade#8#20",
        "6397#1190#1191#59,80#15,106#White Jade#9#20",
        "6398#1192#1193#59,100#15,140#White Jade#10#20",
        "5297#778#779#59,150#15,200#White Jade#11#20",
        "5298#776#777#59,200#15,270#White Jade#12#20",
        "5299#706#721#60,6#16,8#Beryl#1#20",
        "5300#740#745#60,12#16,16#Beryl#2#20",
        "5301#746#747#60,18#16,24#Beryl#3#20",
        "5302#748#749#60,24#16,32#Beryl#4#20",
        "5303#750#751#60,32#16,42#Beryl#5#20",
        "6399#1194#1195#60,40#16,52#Beryl#6#20",
        "6400#1996#1997#60,50#16,66#Beryl#7#20",
        "6401#1998#1999#60,64#16,84#Beryl#8#20",
        "6402#1200#1201#60,80#16,106#Beryl#9#20",
        "6403#1202#1203#60,100#16,140#Beryl#10#20",
        "5304#780#781#60,150#16,200#Beryl#11#20",
        "5305#782#783#60,200#16,270#Beryl#12#20",
        "5306#812#808#61,6#17,8#Jet#1#20",
        "5307#819#833#61,12#17,16#Jet#2#20",
        "5308#834#836#61,18#17,24#Jet#3#20",
        "5309#837#838#61,24#17,32#Jet#4#20",
        "5310#839#840#61,32#17,42#Jet#5#20",
        "6404#1204#1205#61,40#17,52#Jet#6#20",
        "6405#1206#1207#61,50#17,66#Jet#7#20",
        "6406#1208#1209#61,64#17,84#Jet#8#20",
        "6407#1210#1211#61,80#17,106#Jet#9#20",
        "6408#1212#1213#61,100#17,140#Jet#10#20",
        "5311#841#842#61,150#17,200#Jet#11#20",
        "5312#843#844#61,200#17,270#Jet#12#20",
        "5313#845#846#62,6#18,8#Balas#1#20",
        "5314#847#851#62,12#18,16#Balas#2#20",
        "5315#853#854#62,18#18,24#Balas#3#20",
        "5316#856#861#62,24#18,32#Balas#4#20",
        "5317#866#872#62,32#18,42#Balas#5#20",
        "6409#1214#1215#62,40#18,52#Balas#6#20",
        "6410#1216#1217#62,50#18,66#Balas#7#20",
        "6411#1218#1219#62,64#18,84#Balas#8#20",
        "6412#1220#1221#62,80#18,106#Balas#9#20",
        "6413#1222#1223#62,100#18,140#Balas#10#20",
        "5318#873#874#62,150#18,200#Balas#11#20",
        "5319#875#876#62,200#18,270#Balas#12#20",
        "5320#877#878#63,6#19,8#Topaz#1#20",
        "5321#879#880#63,12#19,16#Topaz#2#20",
        "5322#881#882#63,18#19,24#Topaz#3#20",
        "5323#883#884#63,24#19,32#Topaz#4#20",
        "5324#888#894#63,32#19,42#Topaz#5#20",
        "6414#1224#1225#63,40#19,52#Topaz#6#20",
        "6415#1226#1227#63,50#19,66#Topaz#7#20",
        "6416#1228#1229#63,64#19,84#Topaz#8#20",
        "6417#1230#1231#63,80#19,106#Topaz#9#20",
        "6418#1232#1233#63,100#19,140#Topaz#10#20",
        "5325#904#906#63,150#19,200#Topaz#11#20",
        "5326#907#908#63,200#19,270#Topaz#12#20",
    ],
    3: [
        "12637#2148#2146#29,3#3,10#Stone of Virgin Angel#12#30",
        "12638#2147#2146#14,1#3,10#Stone of Emperor#12#30",
        "12639#1513#1515#0,15#3,20#Stone of Zampel#13#30",
        "12640#1514#1515#1,15#3,20#Stone of Suntainer#13#30",
        "12641#1516#1515#2,15#3,20#Stone of Shen Nong#13#30",
        "21377#2142#2143#35,1#35,1#Diamond Stone#12#40",
        "21378#2144#2145#36,1#36,1#Vajra Stone#12#40",
        "38154#2977#2978#35,3#35,3#Devil stone#14#70",
        "38155#2979#2980#36,3#36,3#Serenity Stone#14#70",
        "38153#2975#2976#35,1#35,1#Deity Stone#13#70",
        "25154#2144#2145#36,2#36,2#Jade of Steady Defense#13#40",
    ],
}

# ── Regular addons: "addonId#statId#type(H/F)#applicableItems#name#minVer" ──
ADDONS = [
    "1453#0#H#WAJBM#Strength#10",
    "1458#1#H#WAJBM#Agility#10",
    "1483#2#H#WAJBM#Intelligence#10",
    "1468#3#H#WAJBM#Constitution#10",
    "1384#4#H#WJM#Hit Point#10",
    "1364#5#H#WJM#Mana#10",
    "627#4#H#AB#Hit Point#10",
    "276#5#H#AB#Mana#10",
    "1008#6#H#WAJBM#Physical Attack#10",
    "1004#7#H#W#Max P.Attack#10",
    "1019#8#H#WAJBM#Magic Attack#10",
    "423#9#H#W#Max M.Attack#10",
    "1256#10#H#W#Physical defense#10",
    "219#10#H#AJBM#Physical Def.#10",
    "306#11#H#AJBM#Magic Def.#10",
    "2170#37#H#AJBM#PDefense %#10",
    "2302#38#H#AJBM#MDefense %#10",
    "2185#42#H#WAJBM#Metal Defense %#39",
    "2194#43#H#WAJBM#Wood Defense %#39",
    "2203#44#H#WAJBM#Water Defense %#39",
    "2176#45#H#WAJBM#Fire Defense %#39",
    "2212#46#H#WAJBM#Earth Defense %#39",
    "2487#50#H#WAJBM#Reduce Metal Dmg %#70",
    "2491#51#H#WAJBM#Reduce Wood Dmg %#70",
    "2495#52#H#WAJBM#Reduce Water Dmg %#70",
    "2483#53#H#WAJBM#Reduce Fire Dmg %#70",
    "2499#54#H#WAJBM#Reduce Earth Dmg %#70",
    "2503#49#H#WAJBM#Reduce Magic Dmg %#70",
    "311#23#H#WAJBM#Reduce P.Harm#10",
    "365#15#H#AJBM#Metal Def.#10",
    "368#16#H#AJBM#Wood Def.#10",
    "371#17#H#AJBM#Water Def.#10",
    "374#18#H#AJBM#Fire Def.#10",
    "377#19#H#AJBM#Earth Def.#10",
    "323#20#H#WAJBM#HP Recovery#10",
    "328#21#H#WAJBM#MP Recovery#10",
    "471#22#F#W#Range#10",
    "490#12#H#WAJBM#Accurancy#10",
    "670#13#H#WAJBM#Dodge#10",
    "390#24#H#WAJBM#Accurancy %#10",
    "393#25#H#WJM#Dodge %#10",
    "585#14#H#WAJBM#Crit %#10",
    "2079#35#H#WAJBM#Attack Level#38",
    "2056#36#H#WAJBM#Defence Level#38",
    "2843#47#H#WAJBM#Slaying Level#60",
    "2850#48#H#WAJBM#Warding Level#60",
    "3193#57#H#WAJBM#Physical Penetration#80",
    "3194#58#H#WAJBM#Magic Penetration#80",
    "2362#41#H#WAJBM#Soulforce#60",
    "3043#56#H#WAJBM#Spirit#80",
    "337#28#H#W#Interval -0.05#10",
    "331#28#H#AJBM#Interval -0.05#10",
    "595#29#H#WAJBM#Channeling %#10",
    "300#30#F#WAJB#Max. Duratibility#10",
    "406#31#H#WAJBM#Experience %#10",
    "387#32#H#WAJBM#Max HP %#10",
    "388#33#H#WAJBM#Max MP %#10",
    "286#27#H#WAJM#Mov. Speed %#10",
    "636#26#F#WAJM#Mov. Speed#10",
    "2311#55#H#WAJBM#Eye Observation#60",
    "2365#4#H#WAJB#Rune: HP#50",
    "2366#0#H#WAJB#Rune: Strength#50",
    "2367#1#H#WAJB#Rune: Dexterity#50",
    "2368#2#H#WAJB#Rune: Magic#50",
    "2363#6#H#WAJB#Rune: PAttack#50",
    "2364#8#H#WAJB#Rune: MAttack#50",
    "2370#7#H#WAJB#Rune: Max PAttack#50",
    "2372#9#H#WAJB#Rune: Max MAttack#50",
    "2382#10#H#WAJB#Rune: Phys. Defence#50",
    "2391#12#H#WAJB#Rune: Accurancy#50",
    "2402#14#H#WAJB#Rune: Critical Strike#50",
    "2403#35#H#WAJB#Rune: Attack Level#50",
    "2404#36#H#WAJB#Rune: Defence Level#50",
    "2414#29#H#WAJB#Rune: Channeling#50",
    "3133#64#F#WAJB#Rune: Ride Speed#70",
]

# ── Special weapon addons: "skill_ids#desc#S#W#name#minVer" ──
ADDONS_S = [
    "450 140 1#Stun: Chance for 3 sec stun#S#W#Special: Stun#10",
    "453 141 1#Devour: Chance for reduce target pdef#S#W#Special: -Pdef#10",
    "451 142 1#Slow: Chance for slow target#S#W#Special: Slow#10",
    "452 143 1#Paralyze: Chance for paralyze your opponent#S#W#Special: Paralyze#10",
    "1276 196 1#Weaken: Chance for weaken target mdef#S#W#Special: -Mdef#10",
    "1277 197 1#Fright: Chance for reduce target pattack#S#W#Special: -Pattack#10",
    "1278 198 1#Muddle: Chance for reduce target mattack#S#W#Special: -Mattack#10",
    "1279 199 1#Atrophy: Chance for reduce target attack speed#S#W#Special: -AttSpd#10",
    "1280 200 1#Stupefy: Chance for increase target channeling#S#W#Special: +Channeling#10",
    "1281 201 1#Blind: Chance for reduce target accurancy#S#W#Special: -Acc#10",
    "1282 202 1#Daze: Chance for reduce target dodge rate#S#W#Special: -Dodge#10",
    "1283 203 1#Thoughen: Chance for increase your pdef#S#W#Special: +Pdef#10",
    "1284 204 1#Wisen: Chance for increase your mdef#S#W#Special: +Mdef#10",
    "1286 205 1#Sharpen: Chance for increase your pattack#S#W#Special: +Pattack#10",
    "1287 206 1#Quicken: Chance for increase your attack speed#S#W#Special: +AttSpd#10",
    "1288 207 1#Nimble: Chance for increase your accurancy#S#W#Special: +Acc#10",
    "1289 211 1#Regen: Chance for heal self by 5% HP#S#W#Special: +5% HP#10",
    "1290 212 1#Enlighten: Chance for recover by 5% MP#S#W#Special: +5% MP#10",
    "1291 219 1#Gloom1: Chance for greatly increase pattack but lose 5% MP#S#W#Special: +Patt -5% MP#10",
    "1292 220 1#Gloom2: Chance for greatly increase pattack but decrease self pdef#S#W#Special: +Patt -Pdef#10",
    "1293 225 1#Hatred: Chance for increase your agro level#S#W#Special: Hatred#10",
    "1296 144 1#Seal: Chance for seal target#S#W#Special: Seal#10",
    "1297 146 1#Berserk: Chance for double damage (5% hp cost)#S#W#Special: Berserk#10",
    "1298 208 1#Frenzy: Chance for increase attack spd, dmg but suffer more dmg#S#W#Special: +AttSpd,Patt +Dmg#10",
    "1299 213 1#Meditation: Chance for recover 5% HP & MP#S#W#Special: +5% HP & MP#10",
    "1300 214 1#Blood Defect: Chance for heal back 10% HP#S#W#Special: +10% HP#10",
    "1301 215 1#Spirit Defect: Chance for recover back 10% MP#S#W#Special: +10% MP#10",
    "1302 217 1#Revenge1: Chance for recover 5% HP and increase pattack#S#W#Special: +5%HP +Patt#10",
    "1303 218 1#Revenge2: Chance for recover 5% MP and increase pattac#S#W#Special: +5%MP +Patt#10",
    "1304 223 1#Spikes: Chance for increase pattack and reflect 25% melee dmg#S#W#Special: +Patt +25% Refl#10",
    "1305 224 1#Shield: Chance for cast shield around you, reduce dmg by 20%#S#W#Special: -20% Dmg#10",
    "1306 210 1#Bless: Chance for increase pattack and pdef#S#W#Special: +Patt +Pdef#10",
    "1307 221 1#Faith: Chance for recover 5% HP and increase pdef, mdef#S#W#Special: +5%HP+Pdef+Patt#10",
    "1308 209 1#Stop: Chance for stun target for 5sec and paralyze self for 10sec#S#W#Special: +5Stun -10Para#10",
    "1309 216 1#Holy: Chance for recover 5% HP and remove debuffs#S#W#Special: 5% HP +Purify#10",
    "1310 222 1#Darken: Chance for seal and paralyze your target#S#W#Special: Seal+Para#10",
    "445 809 1#Rip: Chance for deal 5000 bleed damage for 15 sec#S#W#Special: 5000 Bleed#10",
    "446 810 1#Infect: Chance for reduce target max HP#S#W#Special: -Max HP#10",
    "447 811 1#Knock: Chance for interrupt target channeling and knockback 10 m#S#W#Special: Knockback#10",
    "448 812 1#Concentrate: Chance for gain 20 vigor#S#W#Special: +20 Vigor#10",
    "449 813 1#Purge: Chance for dispel target positive buffs#S#W#Special: Purge#10",
    "2275 1168 1#Adv Berserk: Higher chance for deal double damage, cost 5% hp#S#W#Special: Adv Berserk#38",
    "2276 1169 1#Armor Crush: Higher chance for decrease target pdef#S#W#Special: Adv -Pdef#38",
    "2277 1170 1#Havoc: no info#S#W#Special: Havoc#38",
    "2278 1171 1#Determination: no info#S#W#Special: Determ.#38",
    "1279 1172 1#Interjection: no info#S#W#Special: Interj.#38",
    "2280 1173 1#Thunderbolt Shake: Higher chance or stun target for 3 sec#S#W#Special: Stun+#38",
    "2281 1174 1#ParaSeal: Higher chance or paralyze and seal the target#S#W#Special: ParaSeal#38",
    "2282 1175 1#Blood Feud: Higher chance for increase PAttack and recover 5% HP#S#W#Special: Blood Feud#38",
    "2283 1176 1#Frenzy: Higher chance for increase PAttack, AttSpd but get more dmg#S#W#Special: Frenzy#38",
    "2473 1569 1#Buddhas Strike#S#W#Special: Buddhas Strike#70",
    "2474 1570 1#Lord of War#S#W#Special: Lord of War#70",
    "2475 1571 1#Furious Dragon#S#W#Special: Furious Dragon#70",
    "2477 1573 1#Purify Spell#S#W#Special: Purify Spell#70",
    "2479 1575 1#Infinite#S#W#Special: Infinite#70",
    "2482 1742 1#Reflect#S#W#Special: Reflect#70",
]

# ── Star chart addons: "itemId#starPositions#statId#name" ──
ADDON_STAR = [
    "3160#1,2,3,4,6,8,9,10,11,12#6#Physical Attack",
    "3161#5#6#Physical Attack",
    "3162#7#6#Physical Attack",
    "3163#*#8#Magic Attack",
    "3164#1,3,9#10#Physical Defence",
    "3165#5,7,11#10#Physical Defence",
    "3166#2,4,6,8,10,12#10#Physical Defence",
    "3167#1,3,9#11#Magic Defense",
    "3168#5,7,11#11#Magic Defense",
    "3169#2,4,6,8,10,12#11#Magic Defense",
    "3170#1,3,9#4#Hit Point",
    "3171#5,7,11#4#Hit Point",
    "3172#2,4,6,8,10,12#4#Hit Point",
    "3191#1,3,5,7,9,11#5#Mana Point",
    "3192#2,4,6,8,10,12#5#Mana Point",
    "3173#*#56#Spirit",
    "3174#1,3,9#15#Metal Defense",
    "3175#5,7,11#15#Metal Defense",
    "3176#2,4,6,8,10,12#15#Metal Defense",
    "3177#1,3,9#16#Wood Defense",
    "3178#5,7,11#16#Wood Defense",
    "3179#2,4,6,8,10,12#16#Wood Defense",
    "3180#1,3,9#17#Water Defense",
    "3181#5,7,11#17#Water Defense",
    "3182#2,4,6,8,10,12#17#Water Defense",
    "3183#1,3,9#18#Fire Defense",
    "3184#5,7,11#18#Fire Defense",
    "3185#2,4,6,8,10,12#18#Fire Defense",
    "3186#1,3,9#19#Earth Defense",
    "3187#5,7,11#19#Earth Defense",
    "3188#2,4,6,8,10,12#19#Earth Defense",
    "3189#1,3,9#1#Agility",
    "3190#5,7,11#1#Agility",
]

# ── Elf skills: "skillId#maxLevel#talentFlags#name#description" ──
ELF_SKILLS = [
    "1000#0#00000#Venom Stinger#Starter Skill: Decrease target and increase your mov. speed a lil",
    "1024#0#00000#Eruption Fist#Starter Skill: Reduce target magic defence, 10% chance for purge the target",
    "1015#0#00000#Earthflame#Starter Skill: Reduce target attack, defense and target increase the mov. speed",
    "1014#0#00000#Wind Force#Starter Skill: Increase flying speed by 50% [AIR]",
    "968#1#10000#Adrenaline Surge#Sleep immunity",
    "975#1#01000#Qi Manipulation#Reduce target mana over 15 sec",
    "979#1#00001#Blinding Sand#Decrease target accurancy and channeling [GROUND]",
    "987#1#00100#Healing Ripple of Rebirth#Increase HP and MP regeneration in 15m area [WATER]",
    "994#1#00010#Explosion#Consume all vigor and deal fire damage based on consumed vigor",
    "958#1#00100#Cauterize#Chance for purify negative buffs",
    "960#1#10000#Blood Clot#Bleed damage immunity",
    "962#2#20000#Gale#AoE physical damage slow flying speed too [AIR]",
    "974#2#02000#Virulent Poison#Reduce target vigor and deal wood damage depend on drained vigor over 3 sec",
    "984#2#00002#Earthquake#10m AoE earth damage, knockback monsters [GROUND]",
    "991#2#00200#Aiding Ripple of Luck#Increase critical strike chance to you and allies in 15m [WATER]",
    "993#2#00020#Spark#Reduce target fire defense for 6 sec",
    "995#2#00020#Searing Heat#Deal fire damage and decrease target attack and channeling speed",
    "1001#2#01001#Solid Shield#Reduce incoming damage [Werebeast]",
    "1002#2#00101#Mud#AoE Pdef and mov. speed reduction",
    "1004#2#10010#Blade of Supreme Heat#Deal Fire and Physical damage to target",
]

# ── Pet skills: "skillId#name#maxLevel#colorType#description" ──
PET_SKILLS = [
    "687#Bashing#5#0#Single stronger physical attack",
    "747#Ripping Bite#5#0#Physical damage and extra bleed damage",
    "748#Flame Orb#5#0#Deal fire damage based on pet base damage",
    "749#Frost Sting#5#0#Deal water damage based on pet base damage",
    "750#Poison Mist#5#0#Deal wood damage based on pet base damage",
    "751#Summon Storm#5#0#Deal metal damage based on pet base damage",
    "752#Sand Raise#5#0#Deal earth damage based on pet base damage",
    "753#Bluster#5#0#Roar to attract enemies attacks",
    "754#Howling#5#0#Decrease enemy Mdef for 15 sec",
    "755#Armour Break#5#0#Decrease enemy Pdef for 15 sec",
    "756#Frighten#5#0#Decrease enemy Pattack for 15 sec",
    "757#ScreamShock#5#0#Chance for interrupt the opponent channeling",
    "758#Decelerate#5#0#Decrease enemy mov speed for 6 sec",
    "759#Crustaceous#5#0#Reduce damage take for 15 sec",
    "795#Blood Imbibe#3#0#Drain HP from enemy based on Pet Max HP",
    "796#Soul Imbibe#3#0#Drain MP from enemy based on Pet Max HP",
    "797#Life Seizure#1#2#Absorb enemy HP (half of missing HP), heal the Pet",
    "798#Spirit Seizure#1#2#Absorb enemy MP (half of missing HP), heal the Pet",
    "760#Embrave#3#2#Recover HP based on Max HP",
    "761#Doodoo#2#2#Chance for 3 sec Stun also increase self attack speed",
    "799#Sacrifice#1#2#Sacrifice 75% HP and deal 4x base damage",
    "800#Fordo Break#5#2#Deal physical damage, neglecting target defense",
    "801#Reversal Shock#5#2#Reflect melee damage for 1 hour",
    "802#Sharp Claw#5#3#Increase damage for 1 hour",
    "803#Exorcism#5#3#Increase Mdef for 1 hour",
    "804#Solidshell#5#3#Increase Pdef for 1 hour but reduce dodge to 0",
    "805#Bless#5#3#Increase Max HP for 1 hour",
]

# ── Fashion colors: "hexCode#colorName" ──
FASH_COLORS = [
    "ff7f#White", "0000#Black", "007c#Red", "1f00#Blue", "e07f#Yellow",
    "6055#Brown", "2003#Green", "137c#Pink", "3f7f#Perfect Pink",
    "0d7c#Violet Red", "1f30#Purple", "1f7c#Magenta", "1264#Fuchsia",
    "1f64#Violet", "9f49#Lavander", "3f1b#Light Blue", "ff03#Aquamarine",
    "7302#Aqua", "fa03#Turquise", "5f02#Saphire", "7f66#Plum",
    "f967#Jade", "b77f#Cream", "a07d#Copper", "607e#Orange",
    "e667#Lime", "f37f#Light Yellow", "f34f#Light Green", "e003#Bright Green",
    "007f#Mango", "ff67#Grey", "1f63#Smokey",
]


def build_item_opts(items_data: dict, server_ver: int = 75) -> dict:
    """Convert raw items_data JSON into sorted, color-annotated option lists."""
    result: dict[int, dict[int, list[dict]]] = {}
    for type_str, subtypes in items_data.items():
        t = int(type_str)
        result[t] = {}
        for sub_str, entries in subtypes.items():
            s = int(sub_str)
            _vals = entries.values() if isinstance(entries, dict) else entries
            entry_list = sorted(_vals, key=lambda x: x.split("#")[0])
            opts = []
            first = True
            for entry in entry_list:
                parts = entry.split("#")
                if len(parts) < 4:
                    continue
                name = parts[0]
                item_id_str = parts[1]
                grade = parts[2] if len(parts) > 2 else ""
                col_idx = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
                color = ITEM_COLOR[col_idx] if col_idx < len(ITEM_COLOR) else "#ffffff"
                show_grade = t < 4 or (t == 4 and s == 7) or (t == 5 and s == 1)
                label = f" {name} [{grade}] " if show_grade and grade else f" {name} "
                show = True
                if t == 4 and s == 1 and len(parts) > 4:
                    extra = parts[4].split()
                    if len(extra) > 2:
                        race = int(extra[2])
                        color = PWRACE_COLOR[race] if race < len(PWRACE_COLOR) else "#ffffff"
                        label = f" {name} [{race}] "
                        if server_ver < 40 and race > 3:
                            show = False
                        elif server_ver < 50 and race > 4:
                            show = False
                        elif server_ver < 80 and race > 5:
                            show = False
                if show:
                    opts.append({"value": entry.replace("'", "’"), "label": label,
                                 "color": color, "selected": first})
                    first = False
            result[t][s] = opts
    return result


def get_template_data(server_ver: int = 75) -> dict:
    """Build the full context dict for the item builder template."""
    if server_ver >= 80:
        all_class, max_class = 4095, 12
    elif server_ver >= 50:
        all_class, max_class = 1023, 10
    elif server_ver >= 40:
        all_class, max_class = 255, 8
    else:
        all_class, max_class = 219, 6

    # Filter helper for server version
    def ver_ok(entry: str) -> bool:
        parts = entry.split("#")
        return int(parts[-1]) <= server_ver

    # Build filtered addon lists per item type
    def addons_for(type_char: str) -> list[str]:
        result = []
        for a in ADDONS:
            parts = a.split("#")
            if type_char in parts[3] and ver_ok(a):
                result.append(a)
        return result

    # Build star chart addon lists per star index (1-5)
    def star_addons(star_idx: int) -> list[tuple[str, bool]]:
        """Returns list of (entry, visible) for each addon star."""
        result = []
        for a in ADDON_STAR:
            parts = a.split("#")
            pos_str = parts[1]
            visible = False
            if pos_str == "*" or str(star_idx) == pos_str:
                visible = True
            elif "," in pos_str:
                visible = str(star_idx) in pos_str.split(",")
            result.append((a, visible))
        return result

    # Build IBMENU_SC filtered by server version, grouped by type
    menus = {}
    for t, entries in IBMENU_SC.items():
        menus[t] = [(i + 1, e.split("#")[0], int(e.split("#")[1]))
                    for i, e in enumerate(entries)
                    if int(e.split("#")[1]) <= server_ver]

    return {
        "server_ver": server_ver,
        "all_class": all_class,
        "max_class": max_class,
        "pw_classes": PW_CLASSES,
        "class_masks": CLASS_MASKS,
        "proc_types": PROC_TYPES,
        "item_colors": ITEM_COLOR,
        "pwrace_colors": PWRACE_COLOR,
        "fash_colors": FASH_COLORS,
        "menus": menus,
        "soul_stones": SOUL_STONES,
        "addons_w": addons_for("W"),
        "addons_a": addons_for("A"),
        "addons_j": addons_for("J"),
        "addons_b": addons_for("B"),
        "addons_m": addons_for("M"),
        "addons_s": [a for a in ADDONS_S if ver_ok(a)],
        "addon_star": ADDON_STAR,
        "addon_star_vis1": [
            bool(a.split("#")[1] == "*" or a.split("#")[1] == "1" or
                 ("," in a.split("#")[1] and "1" in a.split("#")[1].split(",")))
            for a in ADDON_STAR
        ],
        "elf_skills": ELF_SKILLS,
        "pet_skills": PET_SKILLS,
    }
