from vision_service import VisionService
from input_service import InputService
from context import Context
from state_machine import StateMachine
from states import (
    CheckInventoryOpen,
    OpenInventory,
    CheckBanker,
    BankBanker
)
from barbarian_fishing_states import (
    CheckInventory,
    MakeBait,
    CheckSpot,
    Fish
)

vision = VisionService(threshold=0.80)
input_service = InputService()
context = Context(vision, input_service)

state_machine = StateMachine(context)

# state_machine.add_state(CheckInventoryOpen("CheckInventoryOpen"))
# state_machine.add_state(OpenInventory("OpenInventory"))
# state_machine.add_state(CheckBanker("CheckBanker"))
# state_machine.add_state(BankBanker("BankBanker"))

state_machine.add_state(CheckInventory("CheckInventory"))
state_machine.add_state(MakeBait("MakeBait"))
state_machine.add_state(CheckSpot("CheckSpot"))
state_machine.add_state(Fish("Fish"))

state_machine.set_start("CheckInventory")
state_machine.run()