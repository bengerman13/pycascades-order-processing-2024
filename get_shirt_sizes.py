#!/usr/bin/env python3

import json
from datetime import datetime
import csv

import pretix as pretix

datestring = datetime.now().isoformat(timespec="minutes")
badge_item_id = 462645
in_person_category_id = 140850
tshirt_question_id = 111318
in_person_swag_item_id = 462644
remote_swag_and_stickers_id = 462646
badge_line_question_id = 111704
badge_pronouns_question_id = 111703
badge_affiliation_question_id = 111326
remote_speaker_item_id = 462634
shipping_address_question_id = 111320
source_file = 
shipping_list_file = 
badge_out_file = f"./badges-{datestring}.csv"
shirt_count_file = f"./shirt_count-{datestring}.csv"
shirt_details_csv = f"./shirt_details-{datestring}.csv"

def main():

    with open(source_file) as f:
        d = json.load(f)
    shipping_rows = {}
    with open(shipping_list_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            shipping_rows[row["Order code"]] = row

    event = pretix.Event.from_dict(d["event"])
    interesting_orders = {}
    positions_with_badges = {}
    positions_with_shirts = {}
    remote_speakers = {}
    for order in event.orders:
        order_dict = {}
        if order.status == "p":
            for position in order.positions:
                if position.item.id == badge_item_id or position.item.category.id == in_person_category_id:
                    positions_with_badges[order.code] = position
                    order_dict["badge"] = position
                elif position.item.id == remote_swag_and_stickers_id:
                    positions_with_shirts[order.code] = position
                    order_dict["remote shirt"] = position
                elif position.item.id == in_person_swag_item_id:
                    positions_with_shirts[order.code] = position
                    order_dict["in-person shirt"] = position
                elif position.item.id == remote_speaker_item_id:
                    remote_speakers[order.code] = position
                    order_dict["speaker"] = position
        if order_dict:
            order_dict["timestamp"] = order.datetime
            interesting_orders[order.code] = order_dict

    printable_orders = []
    order_sizes = {}
    size_counts = {}
    for order_code, order in interesting_orders.items():
        order_data = {"order_code": order_code, "has_remote_shirt": False, "has_badge": False, "has_remote_badge": False, "shipping_street": "", "shipping_city": "", "shipping_state": "", "shipping_zip": "", "shipping_country": ""}
        order_data["timestamp"] = order["timestamp"]
        if badge_position := order.get("badge"):
            if badge_position.item.id == badge_item_id:
                order_data["has_remote_badge"] = True
            order_data["has_badge"] = True
            order_data.update(badge_fields_for_position(badge_position))
        if shirt_position := order.get("remote shirt"):
            has_size = False
            for answer in shirt_position.answers:
                if answer.question.id == tshirt_question_id:
                    has_size = True
                    size = answer.answer
                    order_sizes[order_code] = size
                    size_counts[size] = size_counts.get(size, 0) + 1
                    order_data["shirt_size"] = size
                order_data["has_remote_shirt"] = True
            if not has_size:
                print(f"order {order_code} position {position.id} is missing a shirt size!")
        if shirt_position := order.get("in-person shirt"):
            has_size = False
            for answer in shirt_position.answers:
                if answer.question.id == tshirt_question_id:
                    has_size = True
                    size = answer.answer
                    order_sizes[order_code] = size
                    size_counts[size] = size_counts.get(size, 0) + 1
                    order_data["shirt_size"] = size
            if not has_size:
                print(f"order {order_code} position {position.id} is missing a shirt size!")
        if order_data.get("has_remote_badge") or order_data.get("has_remote_shirt"):
            order_data["shipping_street"] = shipping_rows[order_code]["Invoice Address"]
            order_data["shipping_city"] = shipping_rows[order_code]["Invoice City"]
            order_data["shipping_state"] = shipping_rows[order_code]["Invoice State"]
            order_data["shipping_zip"] = shipping_rows[order_code]["Invoice ZIP code"]
            order_data["shipping_country"] = shipping_rows[order_code]["Invoice Country"]

        order_data["has_remote_speaker_gift"] = (order.get("speaker") is not None)
        printable_orders.append(order_data)

    with open(badge_out_file, "w") as f:
        fieldnames = ["order_code","has_badge", "name", "affiliation", "extra_line", "pronouns", "shirt_size", "has_remote_speaker_gift", "has_remote_badge", "has_remote_shirt", "shipping_street", "shipping_city", "shipping_state", "shipping_zip", "shipping_country", "timestamp"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(printable_orders)

            
    
    #badges = []
    #for order_code, position in positions_with_badges.items():
    #    badge = badge_fields_for_position(position)
    #    badge["order_code"] = order_code
    #    badges.append(badge)
    
    #for order_code, position in positions_with_shirts.items():
    #    has_size = False
    #    for answer in position.answers:
    #        if answer.question.id == tshirt_question_id:
    #            has_size = True
    #            size = answer.answer
    #            order_sizes[order_code] = size
    #            size_counts[size] = size_counts.get(size, 0) + 1
    #    if not has_size:
    #        print(f"order {order_code} position {position.id} is missing a shirt size!")
    with open(shirt_count_file, "w") as f:
        fieldnames = ["size", "count"]
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for size, count in size_counts.items():
            writer.writerow([size, count])
    with open(shirt_details_csv, "w") as f:
        fieldnames = ["order_code", "size"]
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        for order, size in order_sizes.items():
            writer.writerow([order, size])
    
        
def badge_fields_for_position(position, badge: dict = None):
    if badge is None:
        badge = {}
    has_name = False
    has_affiliation = False
    has_pronouns = False
    has_extra_line = False
    badge = {}
    for answer in position.answers:
        if answer.question.id == badge_affiliation_question_id:
            has_affiliation = True
            badge["affiliation"] = answer.answer
        elif answer.question.id == badge_pronouns_question_id:
            has_pronouns = True
            badge["pronouns"] = answer.answer
        elif answer.question.id == badge_line_question_id:
            has_extra_line = True
            badge["extra_line"] = answer.answer
    badge["name"] = position.attendee_name
    has_name = badge["name"] is not None
    if not all([has_name, has_affiliation, has_pronouns, has_extra_line]):
        if position.addon_to is not None:
            badge = badge_fields_for_position(position=position.addon_to, badge=badge)
    if badge["name"] is None:
        print(f"badge for position {position.id} doesn't have a name")
    return badge

            
if __name__ == "__main__":
    main()