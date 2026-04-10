def my_complex_function(x):
    """A function with some lint issues."""
    if x == 1:
        print("x is 1")
    elif x == 1:  # Duplicate condition (Ruff/Pylint should catch)
        print("x is still 1")
    
    y = 10
    # unused variable y (Vulture should catch)
    return x * 2

class MyTestClass:
    def method_with_issue(self):
        self.attr = 1
        return self.attr
        print("Unreachable")  # Unreachable code
