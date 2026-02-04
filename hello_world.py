print("Hello World")

def calculator():
    """
    A simple calculator function that performs basic mathematical operations.
    """
    print("Simple Calculator")
    print("Operations: + (addition), - (subtraction), * (multiplication), / (division)")
    print("Enter 'quit' to exit")
    
    while True:
        # Get user input
        expression = input("Enter calculation (e.g., 5 + 3): ").strip()
        
        # Exit condition
        if expression.lower() == 'quit':
            print("Exiting calculator...")
            break
            
        try:
            # Parse and evaluate the expression
            # Using eval for simplicity, but note: eval can be dangerous with untrusted input
            result = eval(expression)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}. Please enter a valid calculation.")

# Run the calculator
if __name__ == "__main__":
    calculator()