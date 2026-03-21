from vision_service import VisionService
from input_service import InputService
from context import Context
from state_machine import StateMachine
# from states import (
#     SomeState,
#     StartState
# )

vision = VisionService(threshold=0.80)
input_service = InputService()
context = Context(vision, input_service)

state_machine = StateMachine(context)

# state_machine.add_state(SomeState("SomeState"))
# state_machine.add_state(OpenInventory("StartState"))

# state_machine.set_start("StartState")
state_machine.run()