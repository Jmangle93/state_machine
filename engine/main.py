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

vision = VisionService(threshold=0.80)
input_service = InputService()
context = Context(vision, input_service)

state_machine = StateMachine(context)

state_machine.add_state(CheckInventoryOpen("CheckInventoryOpen"))
state_machine.add_state(OpenInventory("OpenInventory"))
state_machine.add_state(CheckBanker("CheckBanker"))
state_machine.add_state(BankBanker("BankBanker"))

state_machine.set_start("CheckInventoryOpen")
state_machine.run()