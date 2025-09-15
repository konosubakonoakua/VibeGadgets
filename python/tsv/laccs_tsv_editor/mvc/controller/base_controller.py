class BaseController:
    """Base class for all controllers"""

    def __init__(self, model=None, view=None):
        self.model = model
        self.view = view

    def set_model(self, model):
        """Set the model for the controller"""
        self.model = model

    def set_view(self, view):
        """Set the view for the controller"""
        self.view = view

    def initialize(self):
        """Initialize the controller, should be overridden by subclasses"""
        pass
