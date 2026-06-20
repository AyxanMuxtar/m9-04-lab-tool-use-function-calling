import json
import requests
import re
import sys

# Force UTF-8 output to avoid cp1252 encoding errors on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import re

def lookup_order(order_id):
    try:
        with open('orders.json', 'r') as f:
            orders = json.load(f)
        if order_id in orders:
            return json.dumps(orders[order_id])
        else:
            return json.dumps({"error": f"Order '{order_id}' not found."})
    except Exception as e:
        return json.dumps({"error": str(e)})

def calculate(expression):
    try:
        # Clean the expression for basic safety
        safe_expr = re.sub(r'[^0-9+\-*/(). ]', '', str(expression))
        if not safe_expr.strip():
            return json.dumps({"error": "Empty or invalid expression."})
        result = eval(safe_expr)
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})

def run_ollama_query(prompt):
    url = "http://localhost:11434/api/chat"
    
    tools = [
      {
        "type": "function",
        "function": {
          "name": "lookup_order",
          "description": "returns the order's item, price, purchase date, and warranty length from orders.json.",
          "parameters": {
            "type": "object",
            "properties": {
              "order_id": {
                "type": "string",
                "description": "The ID of the order to look up (e.g., A1001)."
              }
            },
            "required": ["order_id"]
          }
        }
      },
      {
        "type": "function",
        "function": {
          "name": "calculate",
          "description": "evaluates a simple arithmetic expression and returns the number.",
          "parameters": {
            "type": "object",
            "properties": {
              "expression": {
                "type": "string",
                "description": "The mathematical expression to calculate, e.g. '1200 * 3'."
              }
            },
            "required": ["expression"]
          }
        }
      }
    ]

    messages = [{"role": "user", "content": prompt}]
    
    print(f"--- QUERY: {prompt} ---")
    
    # Tool-use loop
    while True:
        payload = {
            "model": "minimax-m3:cloud",
            "messages": messages,
            "stream": False,
            "tools": tools
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
        except Exception as e:
            print("Error connecting to Ollama:", str(e))
            break
        
        if response.status_code != 200:
            print("Error from Ollama:", response.text)
            break
            
        data = response.json()
        message = data.get("message", {})
        messages.append(message)
        
        tool_calls = message.get("tool_calls", [])
        
        # If there are no tool calls, print the final answer and break
        if not tool_calls:
            print("FINAL ANSWER:", message.get("content"))
            break
            
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            name = func.get("name")
            args = func.get("arguments", {})
            
            print(f"-> TOOL CALL: {name}({args})")
            
            result = None
            if name == "lookup_order":
                result = lookup_order(args.get("order_id", ""))
            elif name == "calculate":
                result = calculate(args.get("expression", ""))
            else:
                result = json.dumps({"error": f"Unknown tool {name}"})
                
            print(f"<- TOOL RESULT: {result}")
            
            # The Ollama API documentation requires the tool response to be in messages
            # with role "tool" and optionally content as string.
            messages.append({
                "role": "tool",
                "content": result,
                "name": name
            })

if __name__ == "__main__":
    print("Starting Tool Use Agent with Ollama 'minimax-m3:cloud'...\n")
    
    # 1. Question needing 2 tools
    run_ollama_query("For order A1001, what would the total be if I bought three of them?")
    print("\n" + "="*50 + "\n")
    
    # 2. Question needing no tools
    run_ollama_query("What can you help me with?")
    print("\n" + "="*50 + "\n")
    
    # 3. Bad argument query (stretch goal)
    run_ollama_query("Look up order A9999 and tell me its price.")
    print("\n")
