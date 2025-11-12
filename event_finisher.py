from event import fight_cd_event, fight_pumpkin_event, fight_yinyang_event, fight_gi_event, EventBattleSystem
from leveling import start_leveling
import time
from shadow_war import shadow_war_event

def event_finisher():
    system = EventBattleSystem()
    
    # Configure your targets here
    pumpkin_target = {
        "ene_2104": 50,
        "ene_2105": 25,
        "ene_2106": 25,
        "ene_2103": 50,
        "ene_2102": 50
    }
    
    yinyang_target = {
        "ene_2100": 100,  # Yin Tiger - 15 times
        "ene_2101": 100   # Yang Dragon - 10 times
    }
    
    independence_target = {
        "ene_2095": 40,  # Lembuswana - 20 times
        "ene_2096": 40,  # Lembuswana - 20 times
        "ene_2098": 40,
        "ene_2099": 40,
        "ene_2097": 40   # Leak - 15 times
    }
    
    cd_target = 200  # CD event - 30 times (only 1 enemy)
    
    # Create working copies of targets (so we can track progress)
    pumpkin_remaining = pumpkin_target.copy()
    yinyang_remaining = yinyang_target.copy()
    independence_remaining = independence_target.copy()
    cd_remaining = cd_target
    
    # Main event loop
    print("\n" + "="*50)
    print("Starting event battles...")
    print("="*50)
    
    while True:
        # Check if all targets are completed
        all_completed = (
            cd_remaining <= 0 and
            not pumpkin_remaining and 
            not yinyang_remaining and 
            not independence_remaining
        )
        
        if all_completed:
            print("\n✓ All configured enemies have been defeated!")
            break
        
        battles_performed = False
        
        # CD Event
        if cd_remaining > 0:
            energy = system.check_energy("cd")
            print(f"\nCD Event Energy: {energy}")
            while energy > 0 and cd_remaining > 0:
                print(f"Fighting CD boss ({cd_remaining} kills remaining)")
                fight_cd_event(num_loops=1)
                cd_remaining -= 1
                battles_performed = True
                if cd_remaining <= 0:
                    print("✓ CD event target completed!")
                    break
                # Re-check energy for next iteration
                energy = system.check_energy("cd")
            if energy <= 0 and cd_remaining > 0:
                print("⚠ No energy left for CD event")
        
        # Pumpkin Event
        if pumpkin_remaining:
            energy = system.check_energy("pumpkin")
            print(f"\nPumpkin Event Energy: {energy}")
            while energy > 0 and pumpkin_remaining:
                # Get first enemy from remaining targets
                enemy_id = next(iter(pumpkin_remaining))
                kills_left = pumpkin_remaining[enemy_id]
                print(f"Fighting Pumpkin enemy {enemy_id} ({kills_left} kills remaining)")
                fight_pumpkin_event(enemy_id=enemy_id, num_loops=1)
                pumpkin_remaining[enemy_id] -= 1
                battles_performed = True
                if pumpkin_remaining[enemy_id] <= 0:
                    del pumpkin_remaining[enemy_id]
                    print(f"✓ Enemy {enemy_id} target completed!")
                if not pumpkin_remaining:
                    print("✓ All Pumpkin targets completed!")
                    break
                # Re-check energy for next iteration
                energy = system.check_energy("pumpkin")
            if energy <= 0 and pumpkin_remaining:
                print("⚠ No energy left for Pumpkin event")
        
        # Yin-Yang Event
        if yinyang_remaining:
            energy = system.check_energy("yinyang")
            print(f"\nYin-Yang Event Energy: {energy}")
            while energy > 0 and yinyang_remaining:
                enemy_id = next(iter(yinyang_remaining))
                kills_left = yinyang_remaining[enemy_id]
                print(f"Fighting Yin-Yang enemy {enemy_id} ({kills_left} kills remaining)")
                fight_yinyang_event(enemy_id=enemy_id, num_loops=1)
                yinyang_remaining[enemy_id] -= 1
                battles_performed = True
                if yinyang_remaining[enemy_id] <= 0:
                    del yinyang_remaining[enemy_id]
                    print(f"✓ Enemy {enemy_id} target completed!")
                if not yinyang_remaining:
                    print("✓ All Yin-Yang targets completed!")
                    break
                # Re-check energy for next iteration
                energy = system.check_energy("yinyang")
            if energy <= 0 and yinyang_remaining:
                print("⚠ No energy left for Yin-Yang event")
        
        # Independence Event
        if independence_remaining:
            energy = system.check_energy("independence")
            print(f"\nIndependence Event Energy: {energy}")
            while energy > 0 and independence_remaining:
                enemy_id = next(iter(independence_remaining))
                kills_left = independence_remaining[enemy_id]
                print(f"Fighting Independence enemy {enemy_id} ({kills_left} kills remaining)")
                fight_gi_event(enemy_id=enemy_id, num_loops=1)
                independence_remaining[enemy_id] -= 1
                battles_performed = True
                if independence_remaining[enemy_id] <= 0:
                    del independence_remaining[enemy_id]
                    print(f"✓ Enemy {enemy_id} target completed!")
                if not independence_remaining:
                    print("✓ All Independence targets completed!")
                    break
                # Re-check energy for next iteration
                energy = system.check_energy("independence")
            if energy <= 0 and independence_remaining:
                print("⚠ No energy left for Independence event")
        
        # Check if all targets are completed before leveling
        all_completed_check = (
            cd_remaining <= 0 and
            not pumpkin_remaining and 
            not yinyang_remaining and 
            not independence_remaining
        )
        
        if not all_completed_check:
            print("\nStarting leveling session (waiting for 160 minutes)...")
            shadow_war_event()
            # start_leveling(1920)
            start_leveling(10)
        else:
            print("\nAll targets completed! Skipping leveling.")