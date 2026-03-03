import time
from context import Context
from state_machine import State

# These states are written for converting supercompost to ultracompost

class CheckInventoryOpen(State):
    def execute(self, context):
        print("Checking inventory state ...")
        pos = context.vision.find_template("templates/opened_inventory.png")
        if pos:
            print("    Inventory is open. Checking Bank")
            return("CheckBanker")
        else:
            pos = context.vision.find_template("templates/inventory.png")
            if pos:
                print("    Inventory closed - Opening inventory ...")
                context.data["pos"] = pos
                return("OpenInventory")
        print("ERROR - Could not evaluate inventory state")

class OpenInventory(State):
    def execute(self, context):
        print("Open Inventory")
        context.input.click(context.data["pos"])
        return("CheckBanker")

class CheckBanker(State):
    def execute(self, context):
        banker_templates = ["banker", "banker2", "banker3", "banker4"]
        for banker in banker_templates:
            print(f"Checking for {banker} ...")
            pos = context.vision.find_template(f"templates/{banker}.png")
            if pos:
                print(f"    {banker} found - Banking Banker")
                context.data["pos"] = pos
                return("BankBanker")
        print("Failed to check for banker.")
        context.running = False

class BankBanker(State):
    def execute(self, context):
        print("Bank Banker")
        context.input.right_click(context.data["pos"])
        pos = context.vision.find_template("templates/bank_banker.png")
        if pos:
            print("    Banking ...")
            context.input.click(pos)
            return("CollectSuper")
        print("Failed to bank banker.")
        context.running = False

class CollectSuper(State):
    def execute(self, context):
        print("Acquiring supercompost ...")
        pos = context.vision.find_template("templates/banked_supercompost.png")
        if pos:
            context.input.right_click(pos)
            print("    Looking for withdraw ...")
            new_pos = context.vision.find_template("templates/withdraw_supercompost.png")
            if new_pos:
                print("    Withdrawing ...")
                context.input.click(new_pos)
                context.data["resources_ready"] = True
                return "CloseBank"
        print("Failed to withdraw supercompost.")
        context.running = False

class CloseBank(State):
    def execute(self, context):
        print("Closing bank ...")
        pos = context.vision.find_template("templates/close_bank.png")
        if pos:
            context.input.click(pos)
            return("ApplyResources")


class ApplyResources(State):
    def execute(self, context):
        if not context.data.get("resources_ready"):
            return "AcquireResources"

        print("Processing resources...")
        time.sleep(1)

        return "StoreResults"


class DepositResults(State):
    def execute(self, context):
        print("Storing results...")
        time.sleep(1)

        return "AcquireResources"

class ErrorState(State):
    def execute(self, context):
        print("Error state encountered - Stopping")
        context.running = False
