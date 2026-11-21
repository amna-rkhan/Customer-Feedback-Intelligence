import csv
import random
from datetime import date, timedelta

random.seed(11)
D = {
    "Laptop": {
        "pos": ["the screen is beautiful", "performance is fast", "the keyboard feels great", "it is light to carry", "the speakers are clear"],
        "neg": ["the battery drains quickly", "it gets very hot", "the fan is too loud", "it freezes during work", "the charger stopped working"],
        "neu": ["it has a 15 inch screen", "it came in a grey box", "it arrived on Tuesday"]},
    "Phone": {
        "pos": ["the camera is excellent", "setup was easy", "good value for money", "the battery lasts all day", "the display is sharp"],
        "neg": ["the screen cracked after a week", "it keeps crashing", "the battery dies by noon", "it overheats while charging", "the camera app freezes"],
        "neu": ["I ordered it in black", "the box has a charger and cable", "it has 128 GB storage"]},
    "Headphones": {
        "pos": ["the noise cancelling is great", "very comfortable to wear", "the sound is amazing", "the battery lasts long", "pairing was easy"],
        "neg": ["the left ear is crackling", "it stopped working after a month", "bluetooth keeps disconnecting", "the headband broke", "the microphone is poor"],
        "neu": ["they come in a white box", "the cable is one meter long", "sound is okay"]},
}
OPEN = {"pos": ["I love it,", "Very happy,", "Great buy,", "Works well,", "Impressed,"],
        "neg": ["Disappointed,", "Not happy,", "Terrible experience,", "Very frustrating,", "Would not recommend,"],
        "neu": ["It is okay,", "Average product,", "Just received it,", "Nothing special,"]}
TAIL = {"pos": [".", " and delivery was quick.", " and support was helpful."],
        "neg": [".", " and support was slow.", " and delivery was late.", " and the refund took weeks."],
        "neu": ["."]}

start = date(2026, 8, 31)
rows, cid = [], 3001
for week in range(12):
    for i in range(15):
        product = ["Laptop", "Phone", "Headphones"][i % 3]
        p_neg = 0.20 + 0.04 * week if product == "Phone" else (0.25 if product == "Headphones" else 0.20)
        r = random.random()
        kind = "neg" if r < p_neg else ("neu" if r < p_neg + 0.15 else "pos")
        text = random.choice(OPEN[kind]) + " " + random.choice(D[product][kind]) + random.choice(TAIL[kind])
        d = start + timedelta(days=week * 7 + random.randint(0, 6))
        rows.append([cid, product, text, d.isoformat()])
        cid += 1

with open("sample_data/reviews_big.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["customer_id", "product", "feedback", "date"])
    w.writerows(rows)
print("Wrote", len(rows), "synthetic reviews to sample_data/reviews_big.csv")
print("Unique texts:", len({r[2] for r in rows}))
