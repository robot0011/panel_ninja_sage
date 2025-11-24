from .utils import (
    send_amf_request,
    flatten_json,
    get_data_by_id,
    StatManager,
    CUCSG,
    open_json_to_dict,
    save_fight_data,
)
import time
from . import config

mission_list = open_json_to_dict("data/mission.json")
enemy_list = open_json_to_dict("data/enemy.json")
battle_hash = "eyJpdGVtcyI6eyJhY2Nlc3NvcnkiOiJhY2Nlc3NvcnlfMDEiLCJiYWNrX2l0ZW0iOiJiYWNrXzAxIiwid2VhcG9uIjoid3BuXzAxIiwic2V0Ijoic2V0XzAxXzAifSwic3RhdHVzIjp7ImVhcnRoIjowLCJmaXJlIjowLCJ3YXRlciI6MCwibGlnaHRuaW5nIjowLCJ3aW5kIjowfSwiYnl0ZXMiOnsiXyI6ODIyODQ0NywiX18iOjgyMjg0NDcsIl9fXyI6IjE3NjI3NDY2NTk0MDM2N2MzY2M5OTlhOWY5ZTk1MWExZDMzMjExNTQ1Yjg0YjJkNWE2MzkzM2IwMDIwNDMzMDAwYzNiYjQxMGZiMTc2Mjc0NjY1OTE3NjI3NDY2NTkxNzYyNzQ2NjU5MTc2Mjc0NjY1OSIsIl9fX19fIjo4MjI4NDQ3LCJfX19fX18iOjgyMjg0NDcsIl9fX18iOjE3NjI3NDY2NTl9LCJfX19fIjpbeyJfIjoic2tpbGxfMTMiLCJfXyI6MjkxMzR9XX0="


def check_stop_event():
    """Stop automation if a GUI request has been issued."""
    if hasattr(config, "stop_event") and config.stop_event.is_set():
        print("Automation stopped by user request")
        return True
    return False


def build_enemy_attributes(mission):
    """Return the enemy list and formatted attributes for the mission."""
    if check_stop_event():
        return [], ""

    enemies = []
    enemy_attrs = []
    for enemy_id in mission.get("enemies", []):
        enemy = get_data_by_id(enemy_id, enemy_list)
        if not enemy:
            print(f"Missing enemy definition for {enemy_id}")
            continue
        enemies.append(enemy_id)
        enemy_attrs.append(f"id:{enemy_id}|hp:{enemy['hp']}|agility:{enemy['agility']}")

    return enemies, "#".join(enemy_attrs)


def start_daily_battle(mission, char_flat, char_id, session_key):
    """Start a daily mission battle using the same protocol as leveling."""
    if check_stop_event():
        return None

    enemies, enemy_attrs = build_enemy_attributes(mission)
    if not enemies:
        print(f"Skipping {mission['id']} because enemy data could not be built")
        return None

    agility = StatManager.calculate_stats_with_data("agility", char_flat)
    hash_input = ",".join(enemies) + enemy_attrs + str(agility)
    mission_hash = CUCSG.hash(hash_input)

    parameters = [
        char_id,
        mission["id"],
        ",".join(enemies),
        enemy_attrs,
        agility,
        mission_hash,
        session_key,
    ]

    battle_id = send_amf_request("BattleSystem.startMission", parameters)
    print(f"Started daily mission {mission['id']} (battle id: {battle_id})")
    time.sleep(3)
    return battle_id


def finish_daily_battle(mission_id, char_id, battle_id, session_key):
    """Finish a mission after the battle ID was created."""
    if check_stop_event():
        return None

    hash_input = f"{mission_id}{char_id}{battle_id}0"
    _loc2_ = CUCSG.hash(hash_input)
    parameters = [char_id, mission_id, battle_id, _loc2_, 0, session_key, battle_hash, 0]

    result = send_amf_request("BattleSystem.finishMission", parameters)
    save_fight_data(result)
    return result


def daily():
    if check_stop_event():
        return

    try:
        char_data = config.char_data
    except Exception as exc:
        print(f"Failed to load character data: {exc}")
        return

    char_flat = flatten_json(char_data)
    char_id = char_flat.get("character_data_character_id")
    char_level = char_flat.get("character_data_character_level", "unknown")

    if not char_id:
        print("Character ID missing from saved data")
        return

    try:
        session_key = config.login_data["sessionkey"]
    except Exception as exc:
        print(f"Failed to load login session: {exc}")
        return

    try:
        available_mission = send_amf_request(
            "CharacterService.getMissionRoomData", [char_id, session_key]
        )
    except Exception as exc:
        print(f"Failed to retrieve daily missions: {exc}")
        return

    if available_mission.get("status") != 1:
        print("No available missions")
        return

    missions = available_mission.get("daily") or {}

    if not missions:
        print("No daily missions currently available")
        return

    if isinstance(missions, dict):
        mission_items = []
        for mission_id, available in missions.items():
            try:
                run_count = max(int(available or 0), 0)
            except (TypeError, ValueError):
                run_count = 0
            mission_items.append((mission_id, run_count))
    else:
        mission_items = [(mission_id, 1) for mission_id in missions]

    for mission_id, run_count in mission_items:
        if check_stop_event():
            break

        if not mission_id:
            continue

        if run_count <= 0:
            continue

        mission_data = get_data_by_id(mission_id, mission_list)
        if not mission_data:
            print(f"Unknown mission config for {mission_id}")
            continue

        print(f"Running daily mission {mission_id} ({mission_data.get('name')})")

        for attempt in range(run_count):
            if check_stop_event():
                break

            print(f"Attempt {attempt + 1}/{run_count} for {mission_id}")
            try:
                battle_id = start_daily_battle(
                    mission_data, char_flat, char_id, session_key
                )
                if not battle_id:
                    break
                result = finish_daily_battle(mission_id, char_id, battle_id, session_key)
            except Exception as exc:
                print(f"Failed to complete mission {mission_id}: {exc}")
                break

            if not result:
                break

            if result.get("status") == 1:
                rewards = result.get("result") or []
                gold = rewards[0] if len(rewards) > 0 else "n/a"
                exp = rewards[1] if len(rewards) > 1 else "n/a"
                level = result.get("level", char_level)
                print(
                    f"Mission {mission_id} complete: +{gold} Gold, +{exp} EXP (Level {level})"
                )
                char_level = level
            else:
                print(f"Mission {mission_id} returned unexpected payload: {result}")
                break
    print("Daily missions completed")