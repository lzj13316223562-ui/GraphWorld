from __future__ import annotations

from typing import Any


TASK_SKILLS: tuple[dict[str, Any], ...] = (
    {
        "name": "dispose_food",
        "trigger": "food is_rotten=true or is_burnt=true",
        "goal": "food is moved through trash_bin to garbage_station, food is restored, and trash_bin is returned home",
        "phases": [
            {
                "phase": "collect_food",
                "if": "bad food is not in trash_bin",
                "next": "pick food, place food in resolved trash_bin node id",
            },
            {
                "phase": "take_bin",
                "if": "bad food is already in trash_bin",
                "next": "pick trash_bin",
            },
            {
                "phase": "dump_bin",
                "if": "robot holds trash_bin",
                "next": "move to resolved garbage_station node id, dump trash_bin; food refreshes to fridge",
            },
            {
                "phase": "return_bin",
                "if": "trash_bin is not back at its resolved home node id",
                "next": "move back to trash_bin_home, place trash_bin there",
            },
        ],
    },
    {
        "name": "empty_cup",
        "trigger": "cup fill_level>0 or is_full=true",
        "goal": "cup fill_level=0 and is_full=false",
        "phases": [
            {
                "phase": "dump_cup",
                "if": "cup contains liquid",
                "next": "pick cup, move to resolved sink node id, dump cup into sink",
            },
        ],
    },
    {
        "name": "laundry_clothes",
        "trigger": "cloth is_dirty=true or is_wet=true or folded=false",
        "goal": "cloth is in wardrobe and is_dirty=false and is_wet=false and folded=true",
        "phases": [
            {
                "phase": "wash_load",
                "if": "cloth is_dirty=true and cloth is not in washer",
                "next": "pick cloth, open washer, place cloth in washer",
            },
            {
                "phase": "start_washer",
                "if": "cloth is_dirty=true and cloth is in washer and washer is not running",
                "next": "close washer, then press washer or washer_button",
            },
            {
                "phase": "dry",
                "if": "cloth is_wet=true",
                "next": "pick cloth from washer, place cloth on drying_rack, wait until dry",
            },
            {
                "phase": "fold",
                "if": "cloth is_dirty=false and is_wet=false and folded=false",
                "next": "fold cloth",
            },
            {
                "phase": "store",
                "if": "cloth is clean, dry, folded, and not in wardrobe",
                "next": "pick cloth, open wardrobe, place cloth in wardrobe, close wardrobe",
            },
        ],
    },
    {
        "name": "replenish_prescription_sheet",
        "trigger": "prescription_sheet is in prescription_return_lobby or otherwise not back at outpatient clinic desk/room",
        "goal": "blank prescription sheet is restored to its initial outpatient clinic location",
        "phases": [{"phase": "return_item", "next": "pick prescription_sheet from the return tray, move to outpatient clinic, place it at its initial parent"}],
    },
    {
        "name": "replenish_medicine_box",
        "trigger": "medicine_box is in supply_zone_lobby or otherwise not back in pharmacy",
        "goal": "medicine_box is restored to pharmacy so the next patient can get medicine",
        "phases": [{"phase": "return_item", "next": "pick medicine_box from the lobby supply zone, move to pharmacy, place it at its initial parent"}],
    },
    {
        "name": "return_refrigerated_medicine",
        "trigger": "refrigerated_medicine is in supply_zone_lobby or otherwise not back in medicine_fridge",
        "goal": "refrigerated medicine is restored to medicine_fridge",
        "phases": [{"phase": "return_item", "next": "pick refrigerated_medicine from the lobby supply zone, open medicine_fridge if needed, place it in medicine_fridge, close it"}],
    },
    {
        "name": "clean_medical_waste",
        "trigger": "medical_waste is outside medical_waste_bin",
        "goal": "medical waste is placed in medical_waste_bin",
        "phases": [{"phase": "return_item", "next": "pick medical_waste and place it in medical_waste_bin"}],
    },
    {
        "name": "collect_dirty_linen",
        "trigger": "dirty bed_sheet is outside linen_bin",
        "goal": "dirty bed sheet is placed in dirty_linen_bin",
        "phases": [{"phase": "return_item", "next": "pick dirty bed sheet and place it in dirty_linen_bin"}],
    },
    {
        "name": "restock_clean_sheet",
        "trigger": "clean bed_sheet is not in supply_cabinet",
        "goal": "clean bed sheet is restored to supply_cabinet for the next bed change",
        "phases": [{"phase": "return_item", "next": "pick clean bed sheet and place it in supply_cabinet"}],
    },
    {
        "name": "return_wheelchair",
        "trigger": "wheelchair is not at entrance",
        "goal": "wheelchair is restored to its initial entrance location",
        "phases": [{"phase": "return_item", "next": "pick or move wheelchair back to its initial parent"}],
    },
    {
        "name": "clean_waiting_area",
        "trigger": "waiting area seats are dirty",
        "goal": "waiting area seats are clean",
        "phases": [{"phase": "clean_surface", "next": "move to seats_waiting_area and brush it"}],
    },
    {
        "name": "clean_exam_bed",
        "trigger": "exam bed is dirty or needs_cleaning=true",
        "goal": "exam bed is clean and needs_cleaning=false",
        "phases": [{"phase": "clean_surface", "next": "move to exam_bed and brush it"}],
    },
)


SKILLS_BY_NAME = {str(skill["name"]): skill for skill in TASK_SKILLS}


def relevant_skills_for_nodes(nodes: dict[str, dict[str, Any]], active_goal: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    if active_goal and active_goal.get("skill") in SKILLS_BY_NAME:
        return [SKILLS_BY_NAME[str(active_goal.get("skill"))]]
    relevant: list[dict[str, Any]] = []
    for item in nodes.values():
        semantic = str(item.get("semantic_type") or "")
        states = item.get("states") or {}
        if semantic == "food" and (states.get("is_rotten") is True or states.get("is_burnt") is True):
            relevant.append(SKILLS_BY_NAME["dispose_food"])
        if semantic == "cup" and (float(states.get("fill_level") or 0.0) > 0.0 or states.get("is_full") is True):
            relevant.append(SKILLS_BY_NAME["empty_cup"])
        if semantic in {"clothes", "towel", "blanket"} and (
            states.get("is_dirty") is True or states.get("is_wet") is True or states.get("folded") is False
        ):
            relevant.append(SKILLS_BY_NAME["laundry_clothes"])
        if semantic == "prescription_sheet":
            relevant.append(SKILLS_BY_NAME["replenish_prescription_sheet"])
        if semantic == "medicine_box":
            relevant.append(SKILLS_BY_NAME["replenish_medicine_box"])
        if semantic == "refrigerated_medicine":
            relevant.append(SKILLS_BY_NAME["return_refrigerated_medicine"])
        if semantic == "medical_waste":
            relevant.append(SKILLS_BY_NAME["clean_medical_waste"])
        if semantic == "bed_sheet":
            relevant.append(SKILLS_BY_NAME["collect_dirty_linen"])
            relevant.append(SKILLS_BY_NAME["restock_clean_sheet"])
        if semantic == "wheelchair":
            relevant.append(SKILLS_BY_NAME["return_wheelchair"])
        if str(item.get("id") or "") == "seats_waiting_area" and states.get("is_dirty") is True:
            relevant.append(SKILLS_BY_NAME["clean_waiting_area"])
        if semantic == "bed" and (states.get("is_dirty") is True or states.get("needs_cleaning") is True):
            relevant.append(SKILLS_BY_NAME["clean_exam_bed"])
    deduped = {str(skill["name"]): skill for skill in relevant}
    return list(deduped.values())


__all__ = ["TASK_SKILLS", "relevant_skills_for_nodes"]
