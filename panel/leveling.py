from utils import send_amf_request, save_to_json, open_json_to_dict , flatten_json, get_data_by_id, StatManager, CUCSG
import struct
from typing import List
import config
import time
import keyboard

enemy_list = open_json_to_dict("data/enemy.json")
mission_list = open_json_to_dict("data/mission.json")
battle_hash = "eyJpdGVtcyI6eyJhY2Nlc3NvcnkiOiJhY2Nlc3NvcnlfMDEiLCJiYWNrX2l0ZW0iOiJiYWNrXzAxIiwid2VhcG9uIjoid3BuXzAxIiwic2V0Ijoic2V0XzAxXzAifSwic3RhdHVzIjp7ImVhcnRoIjowLCJmaXJlIjowLCJ3YXRlciI6MCwibGlnaHRuaW5nIjowLCJ3aW5kIjowfSwiYnl0ZXMiOnsiXyI6ODIyODQ0NywiX18iOjgyMjg0NDcsIl9fXyI6IjE3NjI3NDY2NTk0MDM2N2MzY2M5OTlhOWY5ZTk1MWExZDMzMjExNTQ1Yjg0YjJkNWE2MzkzM2IwMDIwNDMzMDAwYzNiYjQxMGZiMTc2Mjc0NjY1OTE3NjI3NDY2NTkxNzYyNzQ2NjU5MTc2Mjc0NjY1OSIsIl9fX19fIjo4MjI4NDQ3LCJfX19fX18iOjgyMjg0NDcsIl9fX18iOjE3NjI3NDY2NTl9LCJfX19fIjpbeyJfIjoic2tpbGxfMTMiLCJfXyI6MjkxMzR9XX0="

def get_levelling_mission(char_level):
    prohibited_grades = ["daily","tp","ss",""]
    if(char_level<=60):
        levelling_mission = [m for m in mission_list if m['level'] == char_level and m['grade'] not in prohibited_grades]
    else:
        levelling_mission = [m for m in mission_list if m['level'] == 60 and m['grade'] not in prohibited_grades]
    return levelling_mission[0]

def start_leveling():
    # char_data = open_json_to_dict("char_data.json")

    char_data = flatten_json(config.char_data)
    char_id = char_data["character_data_character_id"]
    char_level = char_data["character_data_character_level"]
    session_key = config.login_data["sessionkey"]

    while True:
        # Check if the user pressed 'q' to stop the function
        if keyboard.is_pressed('q'):  # 'q' will stop the running function
            print("Stopping the levelling...")
            break  # Exit the loop and stop the function

        mission_same_level = get_levelling_mission(char_level)
        if(mission_same_level is None and char_level > max(mission_list, key=lambda x: x['level'])['level']):
            print("Max level reached for available missions.")
            break
        mission_id = mission_same_level["id"]

        enemys = ""
        enemy_attrs = ""

        for enemy in mission_same_level['enemies']:
            enemy_attr = get_data_by_id(enemy, enemy_list)
            if enemys == "":
                enemys += enemy
                enemy_attrs += "id:" + enemy + "|hp:" + str(enemy_attr["hp"]) + "|agility:" + str(enemy_attr["agility"])
            else:
                enemys += ", " + enemy
                enemy_attrs += "#" + "id:" + enemy + "|hp:" + str(enemy_attr["hp"]) + "|agility:" + str(enemy_attr["agility"])
        agility = StatManager.calculate_stats_with_data("agility", char_data)

        hash_input = enemys + enemy_attrs + str(agility)
        mission_hash = CUCSG.hash(hash_input)


        parameters = [char_id, mission_id, enemys, enemy_attrs, agility, mission_hash, session_key]

        battle_id = send_amf_request("BattleSystem.startMission", parameters)

        time.sleep(1.5)

        #finish battle

        hash_input = str(mission_id) + str(char_id) + str(battle_id) + str(0)
        _loc2_ = CUCSG.hash(hash_input)

        parameters = [char_id, mission_id, battle_id, _loc2_, 0, session_key, battle_hash, 0]
        result = send_amf_request("BattleSystem.finishMission", parameters)

        if(result["status"] == 1):
            print("Mission completed successfully!","gained Gold:", result['result'][0],"Gained EXP:", result['result'][1],"Current Level:", result['level'])
            char_level = result['level']




