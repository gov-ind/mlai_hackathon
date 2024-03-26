from policies.policy import Policy

class SimplePolicy(Policy):
    def __init__(self, quantity=10):
        self.quantity = quantity

    def act(self, external_state, internal_state):
        return self.quantity

    def load_historical(self, external_states):
        pass