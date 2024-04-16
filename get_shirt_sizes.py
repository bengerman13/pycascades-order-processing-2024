#!/usr/bin/env python3
"""
Create CSVs for order fulfullment.

Important context:
- we changed how we collect shipping information halfway through
- we also need to ship some things we didn't get information for
- we are _not_ checking if someone changed their badge info or shirt size
- we are sending the full batch of things to be shipped to the swag team
  every time, and they are figuring out what is new and what is old
"""

import json
from datetime import datetime
import csv
import copy

import pretix as pretix

datestring = datetime.now().isoformat(timespec="minutes")
# item id for remote badge
badge_item_id = 462645
# category id for in-person tickets
in_person_category_id = 140850
# question id for shirt size
tshirt_question_id = 111318
# item id for in-person shirts
in_person_swag_item_id = 462644
# item id for remote swag
remote_swag_and_stickers_id = 462646
# question id for badge "extra line" question
badge_line_question_id = 111704
# question id for pronouns to be included on badge
badge_pronouns_question_id = 111703
# question id for organization/affiliation to include on badge
badge_affiliation_question_id = 111326
# item id for remote speaker ticket
remote_speaker_item_id = 462634
# question id for remote shipping address
shipping_address_question_id = 111320
# get this from Orders > export > Order data (JSON)
# this contains Orders, Positions, Questions, and Items 
source_file = "/path/to/pretix.json"
# get this from Orders > Export > Shipping: List of orders to be shipped
# this has shipping info for some remote shipped orders
shipping_list_file = "/path/to/shipping.csv"
# this is actually about badges, shirts, and speaker gifts
badge_out_file = f"./badges-{datestring}.csv"
# this is a summary of how many shirts of each size we need
shirt_count_file = f"./shirt_count-{datestring}.csv"
# this correlates shirt sizes to order IDs, and is pretty useless now that shirts are in the badge file
shirt_details_csv = f"./shirt_details-{datestring}.csv"
# get this file from orders > export > Invoice Data
# it's used for best-guess shipping where we didn't collect an address
invoices_csv = '/path/to/invoices.csv'

def main():

    with open(source_file) as f:
        d = json.load(f)
    shipping_rows = {}
    with open(shipping_list_file) as f:
        reader = csv.DictReader(f)
        for row in reader:
            shipping_rows[row["Order code"]] = row

    invoice_rows = {}
    with open(invoices_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            invoice_rows[row["Order code"]] = row

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
                    order_dict['badges'] = order_dict.get("badges", [])
                    order_dict['badges'].append(position)
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
        order_data = {"order_code": order_code, "has_remote_shirt": False, "has_badge": False, "has_remote_badge": False, "shipping_street": "", "shipping_city": "", "shipping_state": "", "shipping_zip": "", "shipping_country": "", "has_multiple_lines": False}
        order_data["timestamp"] = order["timestamp"]


        if badge_positions := order.get("badges"):
            if len(badge_positions) > 1:
                order_data["has_multiple_lines"] = True
            badge_line = order_data
            is_first_badge = True
            for badge_position in badge_positions:
                if not is_first_badge:
                    printable_orders.append(badge_line)
                if badge_position.item.id == badge_item_id:
                    badge_line["has_remote_badge"] = True
                badge_line["has_badge"] = True
                badge_line.update(badge_fields_for_position(badge_position))
                badge_line = copy.deepcopy(order_data)
                is_first_badge = False
                
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
        order_data["has_remote_speaker_gift"] = (order.get("speaker") is not None)
        printable_orders.append(order_data)

        for order_data in printable_orders:
            order_code = order_data["order_code"]
            if order_data["has_remote_badge"] or order_data["has_remote_shirt"]:
                if order_code in shipping_rows:
                    order_data["shipping_street"] = shipping_rows[order_code]["Invoice Address"]
                    order_data["shipping_city"] = shipping_rows[order_code]["Invoice City"]
                    order_data["shipping_state"] = shipping_rows[order_code]["Invoice State"]
                    order_data["shipping_zip"] = shipping_rows[order_code]["Invoice ZIP code"]
                    order_data["shipping_country"] = shipping_rows[order_code]["Invoice Country"]
                elif order_code in invoice_rows:
                    order_data["shipping_street"] = invoice_rows[order_code]["Address"]
                    order_data["shipping_city"] = invoice_rows[order_code]["City"]
                    order_data["shipping_state"] = invoice_rows[order_code]["State"]
                    order_data["shipping_zip"] = invoice_rows[order_code]["ZIP code"]
                    order_data["shipping_country"] = invoice_rows[order_code]["Country"]
    with open(badge_out_file, "w") as f:
        fieldnames = ["order_code","has_badge", "name", "affiliation", "extra_line", "pronouns", "shirt_size", "has_remote_speaker_gift", "has_remote_badge", "has_remote_shirt", "shipping_street", "shipping_city", "shipping_state", "shipping_zip", "shipping_country", "timestamp", "has_multiple_lines"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(printable_orders)
    
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