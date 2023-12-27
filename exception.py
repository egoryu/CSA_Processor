class UnexpectedDataValue(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"Unexpected data value: {self.value}"

class RepeatedVariableName(Exception):
    def __init__(self, variable_name):
        self.variable_name = variable_name

    def __str__(self):
        return f"Variable name repeated: {self.variable_name}"
