from __future__ import annotations
import argparse
import gzip
import random
from datetime import date, timedelta
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent

NEIGHBOURHOODS = [
    "Melbourne", "Port Phillip", "Yarra", "Stonnington", "Moreland", "Darebin",
    "Boroondara", "Maribyrnong", "Hobsons Bay", "Mornington Peninsula", "Glen Eira",
    "Bayside", "Monash", "Whitehorse", "Banyule", "Moonee Valley",
]
PROPERTY_TYPES = {
    "Entire home/apt": ["Entire rental unit", "Entire home", "Entire condo", "Entire townhouse", "Entire serviced apartment"],
    "Private room": ["Private room in rental unit", "Private room in home", "Private room in townhouse"],
    "Shared room": ["Shared room in rental unit"],
    "Hotel room": ["Room in hotel"],
}
HOST_NAMES = ["Sarah", "James", "Emily", "Liam", "Olivia", "Noah", "Chloe", "Jack", "Mia", "Lucas",
              "Amelia", "Ethan", "Grace", "Oliver", "Zoe", "Thomas", "Isla", "William", "Ruby", "Henry"]
AMENITIES = ["Wifi", "Kitchen", "Washer", "Air conditioning", "Heating", "TV", "Free parking on premises",
             "Dedicated workspace", "Pool", "Gym", "Elevator", "Dryer", "Iron", "Hair dryer", "Coffee maker"]

REVIEW_TEMPLATES = [
    ("positive", "en", ["location", "cleanliness"], [], "Great location, close to the tram and the apartment was spotless. Would stay again."),
    ("positive", "en", ["host", "amenities"], [], "The host was super responsive and the kitchen had everything we needed. Highly recommend."),
    ("positive", "en", ["value", "location"], [], "Excellent value for money and walking distance to Federation Square. Loved it!"),
    ("positive", "en", ["cleanliness", "host"], [], "Very clean, comfortable bed, and check-in was smooth. Thanks so much!"),
    ("negative", "en", [], ["noise", "cleanliness"], "Terrible night: construction noise from 6am and the bathroom was dirty. Not worth it."),
    ("negative", "en", [], ["host", "amenities"], "Host never answered our messages, the heater was broken and the wifi did not work."),
    ("negative", "en", [], ["value", "safety"], "Overpriced for what you get and the building entrance felt unsafe at night."),
    ("mixed", "en", ["location"], ["noise"], "Perfect spot near the CBD, but the street noise at night was really loud."),
    ("mixed", "en", ["cleanliness", "host"], ["value"], "Clean place and friendly host, although it is a bit expensive for the size."),
    ("mixed", "en", ["amenities"], ["cleanliness"], "Nice pool and gym, however the floors were sticky and the sheets smelled."),
    ("positive", "fr", ["location", "host"], [], "Emplacement parfait et hôte très accueillant. Appartement propre et calme."),
    ("negative", "fr", [], ["cleanliness", "noise"], "Appartement sale et très bruyant la nuit. Déçu de notre séjour."),
    ("positive", "zh", ["location", "cleanliness"], [], "位置很好，离市中心很近，房间非常干净，房东也很热情。"),
    ("mixed", "zh", ["location"], ["noise"], "位置不错，但是晚上很吵，睡得不好。"),
    ("positive", "vi", ["host", "value"], [], "Chủ nhà rất nhiệt tình, giá hợp lý, phòng sạch sẽ. Rất đáng tiền."),
    ("negative", "vi", [], ["cleanliness", "amenities"], "Phòng bẩn, máy lạnh hỏng, wifi chập chờn. Không nên ở."),
    ("positive", "es", ["location", "amenities"], [], "Ubicación excelente y el apartamento tenía todo lo necesario. Muy recomendable."),
    ("positive", "de", ["cleanliness", "host"], [], "Sehr sauber, freundlicher Gastgeber, alles hat gut funktioniert."),
    ("positive", "en", [], [], "Good."),
    ("positive", "en", ["location"], [], "Nice and central. 5 stars."),
]


def money(x: float | None) -> str:
    return "" if x is None else f"${x:,.2f}"


def generate(config: dict, out_root: Path, assigned_listings: pd.DataFrame, assigned_reviews: pd.DataFrame,
             areas: pd.DataFrame, n_extra_listings: int, seed: int) -> None:
    rng = random.Random(seed)
    snapshots = [str(s) for s in config["snapshots"]]
    quota = config["quota"]
    room_counts = quota["room_type_counts"]
    no_review_counts = quota["no_review_counts"]
    missing_price_last = int(quota["missing_price_counts"][snapshots[-1]])
    area_box = areas.set_index("analysis_area")

    ids = assigned_listings["listing_id"].tolist()
    area_of = dict(zip(assigned_listings["listing_id"], assigned_listings["analysis_area"]))
    room_plan: list[str] = []
    for rt, n in room_counts.items():
        room_plan += [rt] * int(n)
    assert len(room_plan) == len(ids), f"quota room_type ({len(room_plan)}) != số listing ({len(ids)})"
    rng.shuffle(room_plan)
    room_of = dict(zip(ids, room_plan))

    hosts = [rng.randrange(1_000_000, 99_999_999) for _ in range(int(len(ids) * 0.6) + 5)]
    host_of = {lid: rng.choice(hosts) for lid in ids}
    host_count: dict[int, int] = {}
    for h in host_of.values():
        host_count[h] = host_count.get(h, 0) + 1

    base_price = {lid: round(rng.lognormvariate(5.0, 0.5)) for lid in ids}
    min_nights = {lid: rng.choice([1, 1, 2, 2, 3, 5, 7, 14, 30, 90]) for lid in ids}
    extra_ids = [str(rng.randrange(10**11, 10**12)) for _ in range(n_extra_listings)]
    extra_rooms = ["Shared room", "Hotel room", "Entire home/apt", "Private room"]

    total_reviews = {lid: rng.choice([0, 3, 8, 15, 40, 90, 150]) for lid in ids}
    assigned_rev_by_listing = assigned_reviews.groupby("listing_id")["review_id"].apply(list).to_dict()

    for snap_i, snap in enumerate(snapshots):
        snap_date = date.fromisoformat(snap)
        out_dir = out_root / snap
        out_dir.mkdir(parents=True, exist_ok=True)
        is_last = snap_i == len(snapshots) - 1

        zero_n = int(no_review_counts[snap])
        zero_ids = set(rng.sample(ids, zero_n))
        missing_price_ids = set(rng.sample(ids, missing_price_last)) if is_last else set(rng.sample(ids, int(len(ids) * 0.3)))
        outlier_ids = set(rng.sample(ids, max(1, len(ids) // 100)))
        bad_minnights_ids = set(rng.sample(ids, max(1, len(ids) // 200)))
        missing_coord_ids = set(rng.sample(ids, max(1, len(ids) // 250)))
        drift_area_ids = set(rng.sample(ids, max(1, len(ids) // 100)))

        rows = []
        for lid in ids + extra_ids:
            assigned = lid in area_of
            rt = room_of[lid] if assigned else rng.choice(extra_rooms)
            if assigned:
                box = area_box.loc[area_of[lid]]
                lat = rng.uniform(box.lat_min, box.lat_max)
                lon = rng.uniform(box.lon_min, box.lon_max)
                if lid in drift_area_ids:
                    lat, lon = -37.0, 144.2
                if lid in missing_coord_ids:
                    lat, lon = None, None
            else:
                lat, lon = rng.uniform(-38.2, -37.5), rng.uniform(144.6, 145.6)
            n_rev = 0 if (assigned and lid in zero_ids) else (total_reviews.get(lid, rng.choice([0, 5, 20])) + snap_i * 3)
            if assigned and lid not in zero_ids and n_rev == 0:
                n_rev = 1
            price = None if (assigned and lid in missing_price_ids) else base_price.get(lid, 150) * (1 + 0.03 * snap_i)
            if price is not None and assigned and lid in outlier_ids and is_last:
                price = 15000.0
            mn = 1000 if (assigned and lid in bad_minnights_ids) else min_nights.get(lid, 2)
            avail365 = rng.randrange(0, 366)
            host = host_of.get(lid, rng.randrange(1_000_000, 99_999_999))
            rows.append({
                "id": lid,
                "listing_url": f"https://www.airbnb.com/rooms/{lid}",
                "scrape_id": int(snap_date.strftime("%Y%m%d")) * 1000000 + 123456,
                "last_scraped": snap,
                "source": rng.choice(["city scrape", "previous scrape"]),
                "name": f"{rng.choice(['Cozy', 'Sunny', 'Modern', 'Charming', 'Spacious'])} {rt.lower()} in {rng.choice(NEIGHBOURHOODS)}",
                "description": "Lorem ipsum dolor sit amet, a lovely place to stay in Melbourne.",
                "neighborhood_overview": "",
                "picture_url": "https://a0.muscache.com/pictures/example.jpg",
                "host_id": host,
                "host_url": f"https://www.airbnb.com/users/show/{host}",
                "host_name": rng.choice(HOST_NAMES),
                "host_since": "2015-06-01",
                "host_location": "Melbourne, Australia",
                "host_about": "",
                "host_response_time": rng.choice(["within an hour", "within a few hours", "within a day", ""]),
                "host_response_rate": rng.choice(["100%", "95%", "80%", ""]),
                "host_acceptance_rate": rng.choice(["100%", "90%", "70%", ""]),
                "host_is_superhost": rng.choice(["t", "f"]),
                "host_thumbnail_url": "", "host_picture_url": "",
                "host_neighbourhood": rng.choice(NEIGHBOURHOODS),
                "host_listings_count": host_count.get(host, 1),
                "host_total_listings_count": host_count.get(host, 1),
                "host_verifications": "['email', 'phone']",
                "host_has_profile_pic": "t", "host_identity_verified": rng.choice(["t", "f"]),
                "neighbourhood": "Melbourne, Victoria, Australia",
                "neighbourhood_cleansed": rng.choice(NEIGHBOURHOODS),
                "neighbourhood_group_cleansed": "",
                "latitude": lat, "longitude": lon,
                "property_type": rng.choice(PROPERTY_TYPES[rt]),
                "room_type": rt,
                "accommodates": rng.choice([1, 2, 2, 3, 4, 4, 6, 8, 20]),
                "bathrooms": rng.choice([1, 1.5, 2]), "bathrooms_text": rng.choice(["1 bath", "1.5 baths", "2 baths"]),
                "bedrooms": rng.choice([1, 1, 2, 3]), "beds": rng.choice([1, 2, 2, 3, 4]),
                "amenities": str(rng.sample(AMENITIES, 6)).replace("'", '"'),
                "price": money(price),
                "minimum_nights": mn, "maximum_nights": rng.choice([30, 90, 365, 1125]),
                "minimum_minimum_nights": mn, "maximum_minimum_nights": mn,
                "minimum_maximum_nights": 1125, "maximum_maximum_nights": 1125,
                "minimum_nights_avg_ntm": float(mn), "maximum_nights_avg_ntm": 1125.0,
                "calendar_updated": "", "has_availability": "t" if avail365 else "f",
                "availability_30": min(30, avail365), "availability_60": min(60, avail365),
                "availability_90": min(90, avail365), "availability_365": avail365,
                "calendar_last_scraped": snap,
                "number_of_reviews": n_rev,
                "number_of_reviews_ltm": min(n_rev, rng.randrange(0, 40)),
                "number_of_reviews_l30d": min(n_rev, rng.randrange(0, 4)),
                "availability_eoy": rng.randrange(0, 200), "number_of_reviews_ly": min(n_rev, rng.randrange(0, 40)),
                "estimated_occupancy_l365d": rng.randrange(0, 365),
                "estimated_revenue_l365d": rng.randrange(0, 90000),
                "first_review": "" if n_rev == 0 else "2019-03-10",
                "last_review": "" if n_rev == 0 else (snap_date - timedelta(days=rng.randrange(1, 400))).isoformat(),
                "review_scores_rating": "" if n_rev == 0 else round(rng.uniform(3.5, 5.0), 2),
                "review_scores_accuracy": "" if n_rev == 0 else round(rng.uniform(3.5, 5.0), 2),
                "review_scores_cleanliness": "" if n_rev == 0 else round(rng.uniform(3.5, 5.0), 2),
                "review_scores_checkin": "" if n_rev == 0 else round(rng.uniform(3.5, 5.0), 2),
                "review_scores_communication": "" if n_rev == 0 else round(rng.uniform(3.5, 5.0), 2),
                "review_scores_location": "" if n_rev == 0 else round(rng.uniform(3.5, 5.0), 2),
                "review_scores_value": "" if n_rev == 0 else round(rng.uniform(3.5, 5.0), 2),
                "license": rng.choice(["", "Exempt", "STRA-12345"]),
                "instant_bookable": rng.choice(["t", "f"]),
                "calculated_host_listings_count": host_count.get(host, 1),
                "calculated_host_listings_count_entire_homes": host_count.get(host, 1) if rt == "Entire home/apt" else 0,
                "calculated_host_listings_count_private_rooms": host_count.get(host, 1) if rt == "Private room" else 0,
                "calculated_host_listings_count_shared_rooms": 0,
                "reviews_per_month": "" if n_rev == 0 else round(n_rev / 36, 2),
            })
        listings = pd.DataFrame(rows)
        with gzip.open(out_dir / "listings.csv.gz", "wt", encoding="utf-8", newline="") as f:
            listings.to_csv(f, index=False)

        cal_rows = []
        for lid in ids + extra_ids[: max(1, len(extra_ids) // 5)]:
            busy_prob = rng.uniform(0.1, 0.9)
            p = base_price.get(lid, 150) * (1 + 0.03 * snap_i)
            for d in range(365):
                day = snap_date + timedelta(days=d)
                cal_rows.append({
                    "listing_id": lid, "date": day.isoformat(),
                    "available": "f" if rng.random() < busy_prob else "t",
                    "price": money(p * (1.2 if day.weekday() >= 5 else 1.0)),
                    "adjusted_price": "",
                    "minimum_nights": min_nights.get(lid, 2), "maximum_nights": 365,
                })
        with gzip.open(out_dir / "calendar.csv.gz", "wt", encoding="utf-8", newline="") as f:
            pd.DataFrame(cal_rows).to_csv(f, index=False)

        rev_rows = []
        for lid, rids in assigned_rev_by_listing.items():
            for rid in rids:
                t = REVIEW_TEMPLATES[int(rid) % len(REVIEW_TEMPLATES)]
                rev_rows.append({
                    "listing_id": lid, "id": rid,
                    "date": (date(2024, 1, 1) + timedelta(days=int(rid) % 600)).isoformat(),
                    "reviewer_id": int(rid) % 9_000_000 + 1000, "reviewer_name": rng.choice(HOST_NAMES),
                    "comments": t[4],
                })
            for k in range(rng.choice([0, 1, 2])):
                rid = str(rng.randrange(10**12, 10**13))
                t = rng.choice(REVIEW_TEMPLATES)
                rev_rows.append({"listing_id": lid, "id": rid, "date": "2025-05-05",
                                 "reviewer_id": rng.randrange(1000, 9_000_000), "reviewer_name": "Alex", "comments": t[4]})
        with gzip.open(out_dir / "reviews.csv.gz", "wt", encoding="utf-8", newline="") as f:
            pd.DataFrame(rev_rows).to_csv(f, index=False)
        print(f"[fixtures] {snap}: listings={len(listings)} calendar={len(cal_rows)} reviews={len(rev_rows)} -> {out_dir}")

    truth = []
    for rid in assigned_reviews["review_id"]:
        t = REVIEW_TEMPLATES[int(rid) % len(REVIEW_TEMPLATES)]
        truth.append({"review_id": rid, "sentiment": t[0], "language": t[1],
                      "aspects_positive": "|".join(t[2]), "aspects_negative": "|".join(t[3])})
    pd.DataFrame(truth).to_csv(out_root / "_fixture_truth_labels.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(ROOT / "configs" / "melbourne.yaml"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--small", action="store_true", help="fixture nhỏ cho smoke test (40 listing)")
    mode.add_argument("--full", action="store_true", help="cùng cỡ dữ liệu thật (1.000 listing)")
    parser.add_argument("--out", default=None, help="thư mục đích (mặc định: data/samples/fixtures hoặc data/raw_fake)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8-sig") as f:
        config = yaml.safe_load(f)
    al = pd.read_csv(ROOT / config["assignments"]["listings"], dtype=str)
    ar = pd.read_csv(ROOT / config["assignments"]["reviews"], dtype={"review_id": str, "listing_id": str})
    areas = pd.read_csv(ROOT / config["assignments"]["areas"])

    if args.full:
        out_root = Path(args.out or ROOT / "data" / "raw_fake")
        generate(config, out_root, al, ar, areas, n_extra_listings=300, seed=args.seed)
        return

    out_root = Path(args.out or ROOT / "data" / "samples" / "fixtures")
    small_l = al.groupby("analysis_area", group_keys=False).head(5).reset_index(drop=True)
    small_r = ar[ar["listing_id"].isin(small_l["listing_id"])]
    hand = small_r[small_r["hand_label"] == 1].head(10)
    llm_only = small_r[(small_r["llm_sample"] == 1) & (small_r["hand_label"] == 0)].head(30)
    rest = small_r[(small_r["llm_sample"] == 0)].head(200 - len(hand) - len(llm_only))
    small_r = pd.concat([hand, llm_only, rest]).sort_values("review_id").reset_index(drop=True)
    small_r["llm_sample"] = small_r["review_id"].isin(pd.concat([hand, llm_only])["review_id"]).astype(int)
    small_r["hand_label"] = small_r["review_id"].isin(hand["review_id"]).astype(int)

    small_cfg = dict(config)
    small_cfg["quota"] = dict(config["quota"])
    small_cfg["quota"]["room_type_counts"] = {"Entire home/apt": len(small_l) - 5, "Private room": 5}
    small_cfg["quota"]["no_review_counts"] = {s: n for s, n in zip([str(x) for x in config["snapshots"]], [2, 1, 1, 1])}
    small_cfg["quota"]["missing_price_counts"] = {str(config["snapshots"][-1]): 1}
    out_root.mkdir(parents=True, exist_ok=True)
    small_l.to_csv(out_root / "assigned_listings.csv", index=False)
    small_r.to_csv(out_root / "assigned_reviews.csv", index=False)
    areas.to_csv(out_root / "analysis_areas.csv", index=False)
    generate(small_cfg, out_root, small_l, small_r, areas, n_extra_listings=12, seed=args.seed)
    truth = pd.read_csv(out_root / "_fixture_truth_labels.csv", dtype=str).set_index("review_id")
    hand = hand.sort_values("review_id")
    pd.DataFrame({
        "review_id": hand["review_id"].values, "listing_id": hand["listing_id"].values,
        "comments": [REVIEW_TEMPLATES[int(r) % len(REVIEW_TEMPLATES)][4] for r in hand["review_id"]],
        "sentiment_hand": [truth.loc[r, "sentiment"] for r in hand["review_id"]],
        "aspects_positive_hand": [truth.loc[r, "aspects_positive"] if isinstance(truth.loc[r, "aspects_positive"], str) else "" for r in hand["review_id"]],
        "aspects_negative_hand": [truth.loc[r, "aspects_negative"] if isinstance(truth.loc[r, "aspects_negative"], str) else "" for r in hand["review_id"]],
        "language_hand": [truth.loc[r, "language"] for r in hand["review_id"]],
    }).to_csv(out_root / "hand_labeled_100.csv", index=False, encoding="utf-8-sig")
    print(f"[fixtures] quota thu nhỏ: listings={len(small_l)}, calendar={365 * len(small_l)}, reviews={len(small_r)}, "
          f"llm={int(small_r['llm_sample'].sum())}, hand={int(small_r['hand_label'].sum())}")


if __name__ == "__main__":
    main()
