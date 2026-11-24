"""Generate fake login logs for a 25-person company.

Run:  python generate_logs.py            (random attack details each time)
      python generate_logs.py --seed 7   (same data every time, for testing)

All data is invented. IP addresses come from ranges reserved for
documentation (RFC 5737), so they can never belong to a real machine.
"""

import argparse
import random
from datetime import datetime, timedelta

from server import store

# username: (display name, one line of what the account can access). All invented.
ACCOUNTS = {
    "ahmed.s":   ("أحمد السبيعي", "موظف عادي: يقرأ ملفات قسم المبيعات"),
    "fatima.k":  ("فاطمة القحطاني", "موظفة عادية: تقرأ ملفات الموارد البشرية وتعدّلها"),
    "khalid.m":  ("خالد المطيري", "مشرف مشاريع: يقرأ ملفات المشاريع ويرفع المخططات"),
    "noura.a":   ("نورة العنزي", "موظفة عادية: تقرأ ملفات قسم الحسابات"),
    "omar.h":    ("عمر الحربي", "مهندس موقع: يقرأ مخططات المشاريع"),
    "sara.y":    ("Sarah Young", "موظفة عادية: تقرأ ملفات قسم الحسابات وتعدّلها"),
    "faisal.r":  ("فيصل الرشيدي", "مهندس موقع: يقرأ مخططات المشاريع"),
    "huda.n":    ("هدى النعيمي", "موظفة عادية: تقرأ ملفات قسم المشتريات"),
    "yousef.b":  ("يوسف البقمي", "مدير مالي: يقرأ ويعدّل كل ملفات الحسابات ويوافق على الدفعات"),
    "lama.t":    ("لمى التميمي", "موظفة عادية: تقرأ ملفات التسويق"),
    "majed.f":   ("ماجد بن فهد بن عبدالرحمن العتيبي", "موظف عادي: يقرأ ملفات قسم المشتريات"),
    "reem.d":    ("ريم الدوسري", "موظفة عادية: تقرأ ملفات الموارد البشرية"),
    "turki.z":   ("تركي الزهراني", "مشرف مشاريع: يقرأ ملفات المشاريع ويرفع المخططات"),
    "maha.q":    ("مها القرني", "موظفة عادية: تقرأ ملفات قسم المبيعات"),
    "saad.w":    ("سعد الوادعي", "مهندس موقع: يقرأ مخططات المشاريع"),
    "abeer.l":   ("عبير اللحياني", "موظفة عادية: تقرأ ملفات العقود"),
    "nasser.j":  ("ناصر الجهني", "مدير المشتريات: يقرأ ويعدّل ملفات المشتريات ويوافق على الطلبات"),
    "dana.g":    ("دانة الغامدي", "موظفة عادية: تقرأ ملفات التسويق"),
    "bandar.o":  ("بندر العمري", "مهندس موقع: يقرأ مخططات المشاريع"),
    "hind.e":    ("هند العسيري", "موظفة عادية: تقرأ ملفات العقود"),
    "fahad.i":   ("فهد الإبراهيم", "المدير العام: يقرأ كل ملفات الشركة"),
    "ruba.c":    ("ربى الشمري", "موظفة عادية: تقرأ ملفات قسم المبيعات"),
    "sultan.v":  ("سلطان الحارثي", "مهندس موقع: يقرأ مخططات المشاريع"),
    "jawaher.p": ("الجوهرة البلوي", "موظفة عادية: تقرأ ملفات الموارد البشرية"),
    "it.admin":  ("أبو فهد", "مدير تقنية المعلومات: يصل إلى كل الأنظمة"),
}
EMPLOYEES = list(ACCOUNTS)

TARGET_LINES = 1500
DAY = datetime(2026, 11, 21)


def office_ip():
    return f"192.0.2.{random.randint(10, 60)}"         # inside the office


def home_ip():
    return f"198.51.100.{random.randint(1, 254)}"      # employees at home


def event(time, account, ip, success):
    # ISO 8601 with the Riyadh offset, e.g. 2026-11-21T23:41:07+03:00
    return (time.strftime("%Y-%m-%dT%H:%M:%S+03:00"), account, ip, 1 if success else 0)


def work_time():
    """A random moment during the working day (07:00 to 19:00)."""
    return DAY + timedelta(seconds=random.randint(7 * 3600, 19 * 3600))


def normal_login():
    ip = office_ip() if random.random() < 0.8 else home_ip()
    return [event(work_time(), random.choice(EMPLOYEES), ip, True)]


def evening_login():
    """Harmless: someone checks email from home between 19:00 and midnight."""
    t = DAY + timedelta(seconds=random.randint(19 * 3600, 24 * 3600 - 1))
    return [event(t, random.choice(EMPLOYEES), home_ip(), True)]


def typo_login():
    """Harmless: 1 or 2 wrong passwords, then success, within a minute."""
    t, who, ip = work_time(), random.choice(EMPLOYEES), office_ip()
    events = []
    for _ in range(random.randint(1, 2)):
        events.append(event(t, who, ip, False))
        t += timedelta(seconds=random.randint(5, 20))
    events.append(event(t, who, ip, True))
    return events


def near_miss(who):
    """4 failures then success: just BELOW the alert threshold of 5."""
    t, ip = DAY + timedelta(hours=9, minutes=15), home_ip()
    events = []
    for _ in range(4):
        events.append(event(t, who, ip, False))
        t += timedelta(seconds=random.randint(30, 90))
    events.append(event(t, who, ip, True))
    return events


def scripted_attack(target):
    """The one attack: many fast failures from one outside address, then success."""
    attacker_ip = f"203.0.113.{random.randint(1, 254)}"
    t = DAY + timedelta(hours=23, minutes=random.randint(5, 40))
    events = []
    for _ in range(random.randint(10, 15)):
        events.append(event(t, target, attacker_ip, False))
        t += timedelta(seconds=random.randint(8, 25))
    events.append(event(t, target, attacker_ip, True))
    return events, attacker_ip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, help="fix the randomness")
    seed = parser.parse_args().seed
    random.seed(seed)

    target = random.choice([e for e in EMPLOYEES if e != "it.admin"])
    near_miss_user = random.choice([e for e in EMPLOYEES if e != target])

    attack, attacker_ip = scripted_attack(target)
    events = attack + near_miss(near_miss_user)
    for _ in range(30):
        events += typo_login()
    for _ in range(40):
        events += evening_login()
    while len(events) < TARGET_LINES:
        events += normal_login()

    events.sort()  # by time, so log line IDs go up in time order

    # Start fresh every run: old incidents would point at log lines that no longer exist.
    store.reset_and_load(
        [(username, name, access) for username, (name, access) in ACCOUNTS.items()],
        events,
    )

    failed = sum(1 for e in events if e[3] == 0)
    print(f"Wrote {len(events)} log lines ({failed} failed logins).")
    print(f"Secret answer (for testing only): target={target}, attacker={attacker_ip}")
    print(f"Near miss (should NOT alert): {near_miss_user}")


if __name__ == "__main__":
    main()
