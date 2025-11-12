import config
import time
from utils import flatten_json, send_amf_request, open_json_to_dict, CUCSG


class ShadowWarEvent:
    def __init__(self):
        self.char_data = open_json_to_dict("char_data.json")
        self.login_data = open_json_to_dict("login_data.json")
        self.char_id = self.char_data["character_data"]["character_id"]
        self.session_key = self.login_data['sessionkey']
        self.base_params = [self.char_id, self.session_key]

    def get_event_status(self):
        """Get current event status including energy."""
        return send_amf_request("ShadowWar.executeService", ["getStatus", self.base_params])

    def get_available_battles(self):
        """Calculate number of available battles based on energy."""
        event_status = self.get_event_status()
        energy = event_status.get('energy', 0)
        print(f"{energy} energies available")
        return energy // 10  # Use integer division

    def get_enemies(self):
        """Retrieve list of enemies."""
        return send_amf_request("ShadowWar.executeService", ["getEnemies", self.base_params])

    def start_battle(self, enemy_id):
        """Start a battle with specified enemy."""
        params = [self.char_id, self.session_key, enemy_id]
        return send_amf_request("ShadowWar.executeService", ["startBattle", params])

    def finish_battle(self, battle_id):
        """Finish the battle and get rewards."""
        mission_hash = CUCSG.hash(f"{self.char_id}{battle_id}0{config.BATTLE_HASH}")
        params = [self.char_id, self.session_key, battle_id, 0, config.BATTLE_HASH, mission_hash]
        return send_amf_request("ShadowWar.executeService", ["finishBattle", params])

    def process_battle(self):
        """Process a single battle sequence."""
        try:
            # Get enemy data
            enemies_data = self.get_enemies()
            if not enemies_data or 'enemies' not in enemies_data or not enemies_data['enemies']:
                print("No enemies available")
                return False

            enemy_id = enemies_data['enemies'][0]['id']
            print(f"Start fighting id: {enemy_id}")

            # Start battle
            battle_data = self.start_battle(enemy_id)
            if battle_data.get("status") != 1:
                print(f"Failed to start battle: {battle_data}")
                return False

            # Wait for battle to complete
            time.sleep(20)

            # Finish battle and get rewards
            battle_result = self.finish_battle(battle_data['id'])
            if battle_result.get("status") == 1:
                xp_gained = battle_result["result"][0]
                gold_gained = battle_result["result"][1]
                print(f"Gained XP: {xp_gained}, Gained Gold: {gold_gained}")
                return True
            else:
                print(f"Battle failed: {battle_result}")
                return False

        except Exception as e:
            print(f"Error processing battle: {e}")
            return False

    def run(self):
        """Main method to run the shadow war event."""
        available_battles = self.get_available_battles()
        
        if available_battles <= 0:
            print("No energy available for shadow war")
            return

        print(f"Starting {available_battles} battles...")
        
        successful_battles = 0
        for i in range(available_battles):
            print(f"Battle {i + 1}/{available_battles}")
            if self.process_battle():
                successful_battles += 1
            
            # Small delay between battles
            if i < available_battles - 1:
                time.sleep(30)
        
        print(f"Completed {successful_battles}/{available_battles} battles successfully")


def shadow_war_event():
    """Main function to execute shadow war event."""
    event = ShadowWarEvent()
    event.run()