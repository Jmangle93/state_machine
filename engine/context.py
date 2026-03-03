# context.py

class Context:
    def __init__(self, vision_service, input_service):
        self.vision = vision_service
        self.input = input_service
        self.data = {}
        self.running = True
