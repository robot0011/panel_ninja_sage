from utils import send_amf_request, flatten_json, get_data_by_id, StatManager, CUCSG, open_json_to_dict, save_fight_data
import time
import keyboard
import config
import amf_req

mission_list = open_json_to_dict("data/mission.json")
enemy_list = open_json_to_dict("data/enemy.json")
battle_hash = "eyJpdGVtcyI6eyJhY2Nlc3NvcnkiOiJhY2Nlc3NvcnlfMDEiLCJiYWNrX2l0ZW0iOiJiYWNrXzAxIiwid2VhcG9uIjoid3BuXzAxIiwic2V0Ijoic2V0XzAxXzAifSwic3RhdHVzIjp7ImVhcnRoIjowLCJmaXJlIjowLCJ3YXRlciI6MCwibGlnaHRuaW5nIjowLCJ3aW5kIjowfSwiYnl0ZXMiOnsiXyI6ODIyODQ0NywiX18iOjgyMjg0NDcsIl9fXyI6IjE3NjI3NDY2NTk0MDM2N2MzY2M5OTlhOWY5ZTk1MWExZDMzMjExNTQ1Yjg0YjJkNWE2MzkzM2IwMDIwNDMzMDAwYzNiYjQxMGZiMTc2Mjc0NjY1OTE3NjI3NDY2NTkxNzYyNzQ2NjU5MTc2Mjc0NjY1OSIsIl9fX19fIjo4MjI4NDQ3LCJfX19fX18iOjgyMjg0NDcsIl9fX18iOjE3NjI3NDY2NTl9LCJfX19fIjpbeyJfIjoic2tpbGxfMTMiLCJfXyI6MjkxMzR9XX0="

# Global variable untuk tracking relogin attempts
relogin_attempts = 0
MAX_RELOGIN_ATTEMPTS = 3

def automatic_relogin():
    """Fungsi untuk melakukan login ulang otomatis ketika session expired"""
    global relogin_attempts
    
    print("Attempting automatic relogin...")
    
    try:
        # Load quick login data
        quick_login_data = open_json_to_dict("quick_login.json")
        if not quick_login_data:
            print("No quick login data found. Cannot auto relogin.")
            return False
        
        username = quick_login_data.get("username")
        password = quick_login_data.get("password")
        
        if not username or not password:
            print("Invalid quick login data.")
            return False
        
        config.game_data = amf_req.check_version()
        if config.game_data.get("status") != 1:
            print("Game version check failed during auto relogin.")
            return False
        
        # Perform login
        config.login_data = amf_req.login(
            username, 
            password, 
            config.game_data["__"], 
            str(int(config.game_data["_"]))
        )
        
        if config.login_data.get('status') != 1:
            print("Auto relogin failed. Invalid credentials.")
            relogin_attempts += 1
            return False
        
        # Get the same character data again
        if config.char_data and "character_data" in config.char_data:
            char_id = config.char_data["character_data"]["character_id"]
            config.char_data = amf_req.get_character_data(char_id)
            
            if config.char_data:
                print("Auto relogin successful! Session renewed.")
                relogin_attempts = 0  # Reset counter on success
                return True
        
        print("Failed to get character data after auto relogin.")
        relogin_attempts += 1
        return False
        
    except Exception as e:
        print(f"Error during auto relogin: {e}")
        relogin_attempts += 1
        return False

def get_levelling_mission(char_level):
    prohibited_grades = ["daily", "tp", "ss", ""]
    if char_level <= 60:
        levelling_mission = [m for m in mission_list if m['level'] == char_level and m['grade'] not in prohibited_grades]
    else:
        levelling_mission = [m for m in mission_list if m['level'] == 60 and m['grade'] not in prohibited_grades]
    return levelling_mission[0] if levelling_mission else None

def build_enemy_attributes(mission_same_level):
    enemies = []
    enemy_attrs = []
    for enemy in mission_same_level['enemies']:
        enemy_attr = get_data_by_id(enemy, enemy_list)
        enemies.append(enemy)
        enemy_attrs.append(f"id:{enemy}|hp:{enemy_attr['hp']}|agility:{enemy_attr['agility']}")
    return enemies, "#".join(enemy_attrs)

def start_battle(mission_same_level, char_id, char_level, session_key):
    enemies, enemy_attrs = build_enemy_attributes(mission_same_level)
    agility = StatManager.calculate_stats_with_data("agility", flatten_json(config.char_data))

    hash_input = ",".join(enemies) + enemy_attrs + str(agility)
    mission_hash = CUCSG.hash(hash_input)

    parameters = [char_id, mission_same_level["id"], ",".join(enemies), enemy_attrs, agility, mission_hash, session_key]
    battle_id = send_amf_request("BattleSystem.startMission", parameters)
    print("wait for 3 seconds")

    time.sleep(3)
    return battle_id

def finish_battle(mission_id, char_id, battle_id, session_key):
    hash_input = f"{mission_id}{char_id}{battle_id}0"
    _loc2_ = CUCSG.hash(hash_input)

    parameters = [char_id, mission_id, battle_id, _loc2_, 0, session_key, battle_hash, 0]
    result = send_amf_request("BattleSystem.finishMission", parameters)
    save_fight_data(result)

    return result

def process_mission(mission_same_level, char_level, char_id, session_key):
    global relogin_attempts
    
    mission_id = mission_same_level["id"]
    
    try:
        battle_id = start_battle(mission_same_level, char_id, char_level, session_key)
        result = finish_battle(mission_id, char_id, battle_id, session_key)

        if result["status"] == 1:
            print(f"Mission completed successfully! Gained Gold: {result['result'][0]} Gained EXP: {result['result'][1]} Current Level: {result['level']}")
            relogin_attempts = 0  # Reset on success
            return result['level']
        else:
            print("Mission failed or session expired. Waiting 20 seconds...")
            time.sleep(20)
            
            # Auto relogin setelah failure
            if relogin_attempts < MAX_RELOGIN_ATTEMPTS:
                if automatic_relogin():
                    # Update session key setelah relogin berhasil
                    new_session_key = config.login_data["sessionkey"]
                    new_char_id = config.char_data["character_data"]["character_id"]
                    print("Retrying mission after auto relogin...")
                    # Retry mission dengan session baru
                    return process_mission(mission_same_level, char_level, new_char_id, new_session_key)
                else:
                    relogin_attempts += 1
                    print(f"Auto relogin failed. Attempt {relogin_attempts}/{MAX_RELOGIN_ATTEMPTS}")
            else:
                print("Max auto relogin attempts reached. Stopping leveling.")
                
    except Exception as e:
        print(f"Error during mission: {e}")
        print("Waiting 20 seconds and attempting auto relogin...")
        time.sleep(20)
        
        if relogin_attempts < MAX_RELOGIN_ATTEMPTS:
            if automatic_relogin():
                new_session_key = config.login_data["sessionkey"]
                new_char_id = config.char_data["character_data"]["character_id"]
                print("Retrying mission after auto relogin...")
                return process_mission(mission_same_level, char_level, new_char_id, new_session_key)
            else:
                relogin_attempts += 1

    return char_level

def start_leveling(loop_times=None):
    global relogin_attempts
    
    # Reset relogin attempts ketika mulai leveling baru
    relogin_attempts = 0
    
    char_data = flatten_json(config.char_data)
    char_id = char_data["character_data_character_id"]
    char_level = char_data["character_data_character_level"]
    session_key = config.login_data["sessionkey"]

    if loop_times is None:
        iter_count = 0
        while True:
            if relogin_attempts >= MAX_RELOGIN_ATTEMPTS:
                print("Too many auto relogin failures. Stopping leveling.")
                break
                
            if iter_count == 15 and iter_count != 0:
                print("Rate limit reached. Waiting 30 seconds...")
                time.sleep(30)
                iter_count = 0

            if keyboard.is_pressed('q'):
                print("Stopping the levelling...")
                break

            mission_same_level = get_levelling_mission(char_level)
            if not mission_same_level:
                print(f"No suitable mission found for level {char_level}")
                break

            # Update data dari config setiap iterasi (untuk handle perubahan setelah relogin)
            char_data = flatten_json(config.char_data)
            char_id = char_data["character_data_character_id"]
            session_key = config.login_data["sessionkey"]
            
            new_level = process_mission(mission_same_level, char_level, char_id, session_key)
            
            # Only update level if mission was successful
            if new_level != char_level:
                char_level = new_level
                
            iter_count += 1
    else:
        for i in range(loop_times):
            if relogin_attempts >= MAX_RELOGIN_ATTEMPTS:
                print("Too many auto relogin failures. Stopping leveling.")
                break
                
            if i % 15 == 0 and i != 0:
                print("Rate limit reached. Waiting 30 seconds...")
                time.sleep(30)

            if keyboard.is_pressed('q'):
                print("Stopping the levelling...")
                break

            mission_same_level = get_levelling_mission(char_level)
            if not mission_same_level:
                print(f"No suitable mission found for level {char_level}")
                break

            # Update data dari config setiap iterasi
            print("battle :",i+1)
            char_data = flatten_json(config.char_data)
            char_id = char_data["character_data_character_id"]
            session_key = config.login_data["sessionkey"]
            
            new_level = process_mission(mission_same_level, char_level, char_id, session_key)
            
            if new_level != char_level:
                char_level = new_level