import time
from context import Context
from state_machine import State

bait = ["roe", "caviar", "cuts"]
fish = ["salmon_inv", "sturgeoun_inv", "trout_inv"]
spots = ["fished_spot1", "unfished_spot1", "fished_spot2", "unfished_spot2", "fished_spot3", "unfished_spot3"]
dir = "templates/fishing"

class CheckInventory(State):
    def execute(self, context):
        print("Checking inventory ---")
        for bait_type in bait:
            pos = context.vision.find_template(f"{dir}/{bait_type}.png")
            if pos:
                print(f"--- Inventory has {bait_type}. Let's look for a fishing spot.")
                return("CheckSpot")
        print("    No bait. Checking for fish ...")
        for fish_type in fish:
            pos = context.vision.find_template(f"{dir}/{fish_type}.png")
            if pos:
                print(f"--- Inventory has {fish_type}. Let's make some bait.")
                context.data["pos"] = pos
                context.data["fish"] = fish_type
                return("MakeBait")
        print(">>> ERROR - No bait or fish found in inventory.")
        context.running = False

class MakeBait(State):
    def execute(self, context):
        print("Making bait ---")
        print("    Looking for knife ...")
        pos_knife = context.vision.find_template(f"{dir}/knife.png")
        if pos_knife:
            context.input.click(pos_knife)
        else:
            print(">>> ERROR - No knife found in inventory.")
            context.running = False
        print(f"    Cutting {context.data['fish']} until there are none left ...")
        context.input.click(context.data["pos"])
        pos = context.vision.find_template(f"{dir}/{context.data['fish']}.png")
        while pos:
            print("    Waiting ...")
            time.sleep(3)
            pos = context.vision.find_template(f"{dir}/{context.data['fish']}.png")
        print(f"--- No more {context.data['fish']} found. Let's check inventory for bait.")
        return("CheckInventory")

class CheckSpot(State):
    def execute(self, context):
        print("Checking for fishing spots ---")
        for spot in spots:
            pos = context.vision.find_template(f"{dir}/{spot}.png")
            if pos:
                print("--- Found a spot!")
                context.input.click(pos)
                context.data['fishing_pos'] = pos
                context.data['fishing_spot'] = spot
                return("Fish")
        print(">>> ERROR - No fishing spot found.")
        return("CheckSpot")

class Fish(State):
    def execute(self, context):
        print("Fishing ---")
        for bait_type in bait:
            pos = context.vision.find_template(f"{dir}/{bait_type}.png")
            while pos:
                print(f"    Found {bait_type} in inventory, waiting ...")
                time.sleep(3)
                pos = context.vision.find_template(f"{dir}/{bait_type}.png")
                if not context.vision.verify_template_at(f"{dir}/{context.data['fishing_spot']}.png", context.data['fishing_pos']):
                    print("--- Fishing spot moved. Checking spots.")
                    return("CheckSpot")
        print("--- Out of bait. Checking inventory.")
        return("CheckInventory")