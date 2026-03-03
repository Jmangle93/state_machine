import time
from engine.state_machine import Context, State


class CollectResources(State):
    def execute(self, context):
        print("Acquiring resources...")
        time.sleep(1)

        context.data["resources_ready"] = True
        return "ProcessResources"


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
